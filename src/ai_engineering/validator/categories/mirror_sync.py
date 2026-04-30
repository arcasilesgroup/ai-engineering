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
    _resolve_instruction_files,
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

_ROOT_PARITY_SOURCE_FALLBACKS: dict[str, str] = {
    "CLAUDE.md": "CLAUDE.md",
    "AGENTS.md": "CLAUDE.md",
    "GEMINI.md": "AGENTS.md",
    ".github/copilot-instructions.md": "CLAUDE.md",
}


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


def _check_instruction_parity(  # audit:exempt:pre-existing-debt-out-of-spec-114-G7-scope
    target: Path,
    report: IntegrityReport,
) -> None:
    """Verify enabled root instruction surfaces have parity coverage.

    Also checks that skill/agent counts in section headers match manifest.
    This is section-level parity (not byte-level, since path translations differ).

    Only checks files for providers listed in ``ai_providers.enabled``.
    Missing enabled-provider root surfaces are reported explicitly instead of
    being skipped behind the CLAUDE.md -> AGENTS.md path.
    """
    from ai_engineering.config.loader import load_manifest_config

    cfg = load_manifest_config(target)
    enabled = set(cfg.ai_providers.enabled)

    enabled_root_surfaces = [
        file_rel
        for file_rel in _resolve_instruction_files(target)
        if file_rel in _ROOT_PARITY_SOURCE_FALLBACKS
    ]

    if not enabled_root_surfaces:
        return

    for surface_rel in enabled_root_surfaces:
        surface_path = target / surface_rel
        if not surface_path.is_file():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=(
                        "instruction-missing-root-surface-"
                        f"{surface_rel.lower().replace('/', '-').replace('.', '-')}"
                    ),
                    status=IntegrityStatus.FAIL,
                    message=f"Enabled provider root instruction surface missing: {surface_rel}",
                    file_path=surface_rel,
                )
            )
            continue

        source_rel = _ROOT_PARITY_SOURCE_FALLBACKS[surface_rel]
        source_path = target / source_rel
        if not source_path.is_file():
            if source_rel != surface_rel:
                source_rel = surface_rel
                source_path = surface_path
            else:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=(
                            "instruction-missing-parity-source-"
                            f"{surface_rel.lower().replace('/', '-').replace('.', '-')}"
                        ),
                        status=IntegrityStatus.WARN,
                        message=(
                            f"Cannot validate {surface_rel} parity because canonical "
                            f"source {source_rel} is missing"
                        ),
                        file_path=surface_rel,
                    )
                )
                continue

        source_content = source_path.read_text(encoding="utf-8")
        surface_content = surface_path.read_text(encoding="utf-8")

        required_sections = [
            section
            for section in _REQUIRED_AGENTS_SECTIONS
            if _extract_section(source_content, section).strip()
        ]

        if not required_sections:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=(
                        "instruction-root-surface-missing-parity-sections-"
                        f"{surface_rel.lower().replace('/', '-').replace('.', '-')}"
                    ),
                    status=IntegrityStatus.WARN,
                    message=(
                        f"{surface_rel} is an enabled root instruction surface but "
                        "contains none of the required parity sections"
                    ),
                    file_path=surface_rel,
                )
            )
            continue

        missing_sections = [
            section
            for section in required_sections
            if not _extract_section(surface_content, section).strip()
        ]

        if missing_sections:
            for section in missing_sections:
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=(
                            "instruction-missing-section-"
                            f"{surface_rel.lower().replace('/', '-').replace('.', '-')}"
                            f"-{section.lower().replace(' ', '-')}"
                        ),
                        status=IntegrityStatus.FAIL,
                        message=f"{surface_rel} missing section: {section}",
                        file_path=surface_rel,
                    )
                )
        elif source_rel != surface_rel:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=(
                        "instruction-section-parity-"
                        f"{surface_rel.lower().replace('/', '-').replace('.', '-')}"
                    ),
                    status=IntegrityStatus.OK,
                    message=(
                        f"{surface_rel} contains all {len(required_sections)}"
                        f" required sections from {source_rel}"
                    ),
                )
            )

    # Determine which instruction files to check for parity
    has_claude = "claude_code" in enabled
    # Providers that use AGENTS.md: github_copilot, gemini, codex
    has_agents_provider = bool(enabled & {"github_copilot", "gemini", "codex"})

    claude_md = target / "CLAUDE.md"
    agents_md = target / "AGENTS.md"

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
