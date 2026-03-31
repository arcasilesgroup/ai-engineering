"""Category 2: Mirror Sync -- SHA-256 compare canonical vs template mirrors."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from ai_engineering.validator._shared import (
    _CLAUDE_AGENTS_MIRROR,
    _CLAUDE_COMMANDS_MIRROR,
    _CLAUDE_SKILLS_MIRROR,
    _CODEX_AGENTS_MIRROR,
    _CODEX_SKILLS_MIRROR,
    _COPILOT_AGENTS_MIRROR,
    _COPILOT_SKILLS_MIRROR,
    _GEMINI_AGENTS_MIRROR,
    _GEMINI_SKILLS_MIRROR,
    _GOVERNANCE_MIRROR,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _extract_section,
    _glob_files,
    _is_excluded,
    _is_source_repo,
    _sha256,
)

# Sections in CLAUDE.md that must also appear in AGENTS.md.
# Excludes Claude-specific items that are intentionally stripped.
_REQUIRED_AGENTS_SECTIONS: list[str] = [
    "Workflow Orchestration",
    "Task Management",
    "Core Principles",
    "Agent Selection",
    "Skills",
    "Effort Levels",
    "Quality Gates",
    "Observability",
    "Don't",
    "Source of Truth",
]

# Pattern to extract skill/agent count from section header like "## Skills (40)"
_SECTION_COUNT_RE = re.compile(r"\((\d+)\)")


def _check_mirror_sync(
    target: Path, report: IntegrityReport, *, cache: FileCache | None = None
) -> None:
    """SHA-256 compare canonical governance files vs template mirrors."""
    if not _is_source_repo(target):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="mirror-sync-skipped",
                status=IntegrityStatus.OK,
                message="Mirror sync checks skipped (not source repo)",
            )
        )
        return

    _sha = cache.sha256 if cache else _sha256
    _gf = cache.glob_files if cache else _glob_files

    canonical_root = target / _GOVERNANCE_MIRROR[0]
    mirror_root = target / _GOVERNANCE_MIRROR[1]
    patterns = _GOVERNANCE_MIRROR[2]
    exclusions = _GOVERNANCE_MIRROR[3]

    if not canonical_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="canonical-root",
                status=IntegrityStatus.FAIL,
                message=f"Canonical root not found: {_GOVERNANCE_MIRROR[0]}",
            )
        )
        return

    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="mirror-root",
                status=IntegrityStatus.FAIL,
                message=f"Mirror root not found: {_GOVERNANCE_MIRROR[1]}",
            )
        )
        return

    # Collect canonical files
    canonical_files = _gf(canonical_root, patterns)
    canonical_relatives = {
        f.relative_to(canonical_root)
        for f in canonical_files
        if not _is_excluded(f.relative_to(canonical_root), exclusions)
    }

    # Collect mirror files
    mirror_files = _gf(mirror_root, patterns)
    mirror_relatives = {
        f.relative_to(mirror_root)
        for f in mirror_files
        if not _is_excluded(f.relative_to(mirror_root), exclusions)
    }

    # Check pairs
    mismatches = 0
    checked = 0
    for rel in sorted(canonical_relatives & mirror_relatives):
        checked += 1
        canonical_hash = _sha(canonical_root / rel)
        mirror_hash = _sha(mirror_root / rel)
        if canonical_hash != mirror_hash:
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"desync-{rel.as_posix()}",
                    status=IntegrityStatus.FAIL,
                    message=f"Mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    # Missing mirrors
    for rel in sorted(canonical_relatives - mirror_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"missing-mirror-{rel.as_posix()}",
                status=IntegrityStatus.FAIL,
                message=f"Canonical file has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    # Orphaned mirrors
    for rel in sorted(mirror_relatives - canonical_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"orphan-mirror-{rel.as_posix()}",
                status=IntegrityStatus.WARN,
                message=f"Mirror file has no canonical source: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    # Claude commands mirror
    _check_claude_commands_mirror(target, report, _sha)

    # Claude skills/agents mirrors
    _check_claude_skills_mirror(target, report, _sha)
    _check_claude_agents_mirror(target, report, _sha)

    # Codex skills/agents mirrors
    _check_codex_skills_mirror(target, report, _sha)
    _check_codex_agents_mirror(target, report, _sha)

    # Gemini skills/agents mirrors
    _check_gemini_skills_mirror(target, report, _sha)
    _check_gemini_agents_mirror(target, report, _sha)

    # Copilot skills and agents mirrors
    _check_copilot_skills_mirror(target, report, _sha)
    _check_copilot_agents_mirror(target, report, _sha)

    # Instruction file parity (CLAUDE.md <-> AGENTS.md section content)
    _check_instruction_parity(target, report)

    if mismatches == 0 and not (canonical_relatives - mirror_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="governance-mirrors",
                status=IntegrityStatus.OK,
                message=f"All {checked} mirror pairs in sync",
            )
        )


def _check_pair_mirror(
    target: Path,
    report: IntegrityReport,
    canonical_rel: str,
    mirror_rel: str,
    glob_pattern: str,
    label: str,
    description: str,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check a canonical/mirror directory pair for SHA-256 parity."""
    canonical_root = target / canonical_rel
    mirror_root = target / mirror_rel

    if not canonical_root.is_dir():
        return
    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"{label}-mirror-root",
                status=IntegrityStatus.FAIL,
                message=f"{description} mirror directory not found",
            )
        )
        return

    canonical_files = {
        f.relative_to(canonical_root)
        for f in sorted(canonical_root.rglob(glob_pattern))
        if f.is_file()
    }
    mirror_files = {
        f.relative_to(mirror_root) for f in sorted(mirror_root.rglob(glob_pattern)) if f.is_file()
    }

    mismatches = 0
    for rel in sorted(canonical_files & mirror_files):
        if sha_fn(canonical_root / rel) != sha_fn(mirror_root / rel):
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"{label}-desync-{rel.as_posix()}",
                    status=IntegrityStatus.FAIL,
                    message=f"{description} mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    for rel in sorted(canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"{label}-missing-{rel.as_posix()}",
                status=IntegrityStatus.FAIL,
                message=f"{description} has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    if mismatches == 0 and not (canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"{label}s-mirrors",
                status=IntegrityStatus.OK,
                message=f"All {len(canonical_files & mirror_files)} {description} mirrors in sync",
            )
        )


def _check_claude_commands_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .claude/commands/ mirror sync."""
    _check_pair_mirror(
        target,
        report,
        *_CLAUDE_COMMANDS_MIRROR,
        "*.md",
        "claude-cmd",
        "Claude command",
        sha_fn=sha_fn,
    )


def _check_copilot_skills_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .github/skills/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_COPILOT_SKILLS_MIRROR,
        "*.md",
        "copilot-skill",
        "Copilot skill",
        sha_fn=sha_fn,
    )


def _check_claude_skills_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .claude/skills/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_CLAUDE_SKILLS_MIRROR,
        "*.md",
        "claude-skill",
        "Claude skill",
        sha_fn=sha_fn,
    )


def _check_claude_agents_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .claude/agents/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_CLAUDE_AGENTS_MIRROR,
        "*.md",
        "claude-agent",
        "Claude agent",
        sha_fn=sha_fn,
    )


def _check_codex_skills_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .codex/skills/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_CODEX_SKILLS_MIRROR,
        "*.md",
        "codex-skill",
        "Codex skill",
        sha_fn=sha_fn,
    )


def _check_codex_agents_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .codex/agents/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_CODEX_AGENTS_MIRROR,
        "*.md",
        "codex-agent",
        "Codex agent",
        sha_fn=sha_fn,
    )


def _check_gemini_skills_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .gemini/skills/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_GEMINI_SKILLS_MIRROR,
        "*.md",
        "gemini-skill",
        "Gemini skill",
        sha_fn=sha_fn,
    )


def _check_gemini_agents_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .gemini/agents/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_GEMINI_AGENTS_MIRROR,
        "*.md",
        "gemini-agent",
        "Gemini agent",
        sha_fn=sha_fn,
    )


def _check_copilot_agents_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check .github/agents/ mirror sync with templates."""
    _check_pair_mirror(
        target,
        report,
        *_COPILOT_AGENTS_MIRROR,
        "*.agent.md",
        "copilot-agent",
        "Copilot agent",
        sha_fn=sha_fn,
    )


def _check_instruction_parity(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Verify AGENTS.md contains all required sections from CLAUDE.md.

    Also checks that skill/agent counts in section headers match manifest.
    This is section-level parity (not byte-level, since path translations differ).

    Only checks files for providers listed in ``ai_providers.enabled``.
    When both ``claude_code`` and a provider using ``AGENTS.md`` are enabled,
    performs section-level parity between the two files.
    """
    from ai_engineering.config.loader import load_manifest_config

    cfg = load_manifest_config(target)
    enabled = set(cfg.ai_providers.enabled)

    # Determine which instruction files to check for parity
    has_claude = "claude_code" in enabled
    # Providers that use AGENTS.md: github_copilot, gemini, codex
    has_agents_provider = bool(enabled & {"github_copilot", "gemini", "codex"})

    claude_md = target / "CLAUDE.md"
    agents_md = target / "AGENTS.md"

    # Only check parity when both claude_code and an agents-provider are enabled
    if has_claude and has_agents_provider:
        if not claude_md.is_file() or not agents_md.is_file():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="instruction-parity-skipped",
                    status=IntegrityStatus.WARN,
                    message="CLAUDE.md or AGENTS.md not found, skipping parity check",
                )
            )
            return
    elif has_claude:
        # Only claude_code enabled; no agents-provider, so no parity to check
        if not claude_md.is_file():
            return
        # Nothing to compare against — skip silently
        return
    elif has_agents_provider:
        # Only agents-provider(s); no CLAUDE.md to compare against
        return
    else:
        # No relevant providers enabled
        return

    claude_content = claude_md.read_text(encoding="utf-8")
    agents_content = agents_md.read_text(encoding="utf-8")

    # Only check sections that actually exist in CLAUDE.md
    # (test environments may use minimal instruction files)
    present_in_claude = [
        section
        for section in _REQUIRED_AGENTS_SECTIONS
        if _extract_section(claude_content, section).strip()
    ]

    if not present_in_claude:
        # CLAUDE.md has none of the expected sections -- skip parity check
        return

    # Check required sections exist in AGENTS.md
    missing_sections: list[str] = []
    for section in present_in_claude:
        extracted = _extract_section(agents_content, section)
        if not extracted.strip():
            missing_sections.append(section)

    if missing_sections:
        for section in missing_sections:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"instruction-missing-section-{section.lower().replace(' ', '-')}",
                    status=IntegrityStatus.FAIL,
                    message=f"AGENTS.md missing section: {section}",
                    file_path="AGENTS.md",
                )
            )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="instruction-section-parity",
                status=IntegrityStatus.OK,
                message=(
                    f"AGENTS.md contains all {len(present_in_claude)}"
                    " required sections from CLAUDE.md"
                ),
            )
        )

    # Check skill/agent counts match manifest using load_manifest_config
    expected_skills = cfg.skills.total
    expected_agents = cfg.agents.total

    if expected_skills == 0 and expected_agents == 0:
        return

    # Check counts in instruction files for enabled providers
    files_to_check: list[tuple[Path, str]] = []
    if has_claude and claude_md.is_file():
        files_to_check.append((claude_md, "CLAUDE.md"))
    if has_agents_provider and agents_md.is_file():
        files_to_check.append((agents_md, "AGENTS.md"))

    for file_path, label in files_to_check:
        content = file_path.read_text(encoding="utf-8")

        # Extract skill count from "## Skills (N)" header
        skills_section_header = ""
        for line in content.splitlines():
            if line.strip().lower().startswith("## skills"):
                skills_section_header = line
                break

        if skills_section_header and expected_skills > 0:
            count_match = _SECTION_COUNT_RE.search(skills_section_header)
            if count_match:
                found_count = int(count_match.group(1))
                if found_count != expected_skills:
                    report.checks.append(
                        IntegrityCheckResult(
                            category=IntegrityCategory.MIRROR_SYNC,
                            name=f"instruction-skill-count-{label.lower().replace('.', '-')}",
                            status=IntegrityStatus.FAIL,
                            message=(
                                f"{label} skill count ({found_count})"
                                f" != manifest ({expected_skills})"
                            ),
                            file_path=label,
                        )
                    )

        # Check Source of Truth section for skill/agent counts
        sot_section = _extract_section(content, "Source of Truth")
        if sot_section:
            skills_sot = re.search(r"Skills\s*\((\d+)\)", sot_section)
            agents_sot = re.search(r"Agents\s*\((\d+)\)", sot_section)
            if skills_sot and expected_skills > 0 and int(skills_sot.group(1)) != expected_skills:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=f"instruction-sot-skills-{label.lower().replace('.', '-')}",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"{label} Source of Truth skill count"
                            f" ({skills_sot.group(1)}) != manifest ({expected_skills})"
                        ),
                        file_path=label,
                    )
                )
            if agents_sot and expected_agents > 0 and int(agents_sot.group(1)) != expected_agents:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=f"instruction-sot-agents-{label.lower().replace('.', '-')}",
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"{label} Source of Truth agent count"
                            f" ({agents_sot.group(1)}) != manifest ({expected_agents})"
                        ),
                        file_path=label,
                    )
                )
