"""Category 2: Mirror Sync -- SHA-256 compare canonical vs template mirrors."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from ai_engineering.config.mirror_inventory import (
    get_generated_provenance_fields,
    get_internal_specialist_agent_targets,
    get_mirror_families,
)
from ai_engineering.validator._shared import (
    _CLAUDE_AGENTS_MIRROR,
    _CLAUDE_COMMANDS_MIRROR,
    _CLAUDE_SKILLS_MIRROR,
    _CODEX_AGENTS_MIRROR,
    _CODEX_SKILLS_MIRROR,
    _COPILOT_AGENTS_MIRROR,
    _COPILOT_GENERATED_INSTRUCTIONS_MIRROR,
    _COPILOT_SKILLS_MIRROR,
    _GEMINI_AGENTS_MIRROR,
    _GEMINI_SKILLS_MIRROR,
    _GOVERNANCE_MIRROR,
    _MANUAL_INSTRUCTION_FILES,
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

_SPECIALIST_AGENT_PREFIXES = ("reviewer-", "verifier-", "review-", "verify-")
_FRONTMATTER_BLOCK_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_PROVENANCE_GLOB_BY_FAMILY: dict[str, str] = {
    "codex-skills": "SKILL.md",
    "codex-agents": "ai-*.md",
    "gemini-skills": "SKILL.md",
    "gemini-agents": "ai-*.md",
    "copilot-skills": "SKILL.md",
    "copilot-agents": "*.agent.md",
}
# Spec-119 introduced specialist review/verifier agents that mirror from
# `.claude/agents/` to public surfaces. They're governed by the canonical
# Claude mirror, so extend allowed patterns rather than relocating them
# under `internal/` (which would break the parity contract).
_PUBLIC_AGENT_ROOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        _CODEX_AGENTS_MIRROR[0],
        ("ai-*.md", "review-*.md", "reviewer-*.md", "verifier-*.md", "verify-*.md"),
    ),
    (
        _CODEX_AGENTS_MIRROR[1],
        ("ai-*.md", "review-*.md", "reviewer-*.md", "verifier-*.md", "verify-*.md"),
    ),
    (
        _GEMINI_AGENTS_MIRROR[0],
        ("ai-*.md", "review-*.md", "reviewer-*.md", "verifier-*.md", "verify-*.md"),
    ),
    (
        _GEMINI_AGENTS_MIRROR[1],
        ("ai-*.md", "review-*.md", "reviewer-*.md", "verifier-*.md", "verify-*.md"),
    ),
    (
        _COPILOT_AGENTS_MIRROR[0],
        ("*.agent.md", "review-*.md", "reviewer-*.md", "verifier-*.md", "verify-*.md"),
    ),
    (
        _COPILOT_AGENTS_MIRROR[1],
        ("*.agent.md", "review-*.md", "reviewer-*.md", "verifier-*.md", "verify-*.md"),
    ),
)
_PUBLIC_SKILL_ROOTS: tuple[str, ...] = (
    _CODEX_SKILLS_MIRROR[0],
    _CODEX_SKILLS_MIRROR[1],
    _GEMINI_SKILLS_MIRROR[0],
    _GEMINI_SKILLS_MIRROR[1],
    _COPILOT_SKILLS_MIRROR[0],
    _COPILOT_SKILLS_MIRROR[1],
)
_PUBLIC_SKILL_ROOT_PREFIXES = ("ai-", "_shared")
_NON_CLAUDE_LOCAL_REFERENCE_ROOTS: tuple[str, ...] = (
    _CODEX_SKILLS_MIRROR[0],
    _CODEX_SKILLS_MIRROR[1],
    _CODEX_AGENTS_MIRROR[0],
    _CODEX_AGENTS_MIRROR[1],
    _GEMINI_SKILLS_MIRROR[0],
    _GEMINI_SKILLS_MIRROR[1],
    _GEMINI_AGENTS_MIRROR[0],
    _GEMINI_AGENTS_MIRROR[1],
    _COPILOT_SKILLS_MIRROR[0],
    _COPILOT_SKILLS_MIRROR[1],
    _COPILOT_AGENTS_MIRROR[0],
    _COPILOT_AGENTS_MIRROR[1],
)
_STRAY_CLAUDE_LOCAL_REF_RE = re.compile(r"\.claude/(skills|agents)/")
_CANONICAL_SOURCE_LINE_RE = re.compile(
    r"^canonical_source:\s+\.claude/(skills|agents)/.*$", re.MULTILINE
)


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
    _check_claude_specialist_agents_mirror(target, report)

    # Codex skills/agents mirrors
    _check_codex_skills_mirror(target, report, _sha)
    _check_codex_agents_mirror(target, report, _sha)

    # Gemini skills/agents mirrors
    _check_gemini_skills_mirror(target, report, _sha)
    _check_gemini_agents_mirror(target, report, _sha)

    # Copilot skills and agents mirrors
    _check_copilot_skills_mirror(target, report, _sha)
    _check_copilot_agents_mirror(target, report, _sha)
    _check_generated_instructions_mirror(target, report, _sha)
    _check_generated_mirror_provenance(target, report)
    _check_non_claude_local_reference_leaks(target, report)
    _check_public_skill_root_contract(target, report)
    _check_public_agent_root_contract(target, report)

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
    exclude_relatives: frozenset[str] = frozenset(),
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
        if f.is_file() and f.relative_to(canonical_root).as_posix() not in exclude_relatives
    }
    mirror_files = {
        f.relative_to(mirror_root)
        for f in sorted(mirror_root.rglob(glob_pattern))
        if f.is_file() and f.relative_to(mirror_root).as_posix() not in exclude_relatives
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
        "ai-*.md",
        "claude-agent",
        "Claude agent",
        sha_fn=sha_fn,
    )


def _check_claude_specialist_agents_mirror(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Check generated Claude specialist agent wrappers against canonical input."""
    canonical_root = target / _CLAUDE_AGENTS_MIRROR[0]
    mirror_root = target / _CLAUDE_AGENTS_MIRROR[1]

    if not canonical_root.is_dir():
        return
    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="claude-specialist-agent-mirror-root",
                status=IntegrityStatus.FAIL,
                message="Claude specialist agent mirror directory not found",
            )
        )
        return

    specialist_files = [
        agent_path
        for agent_path in sorted(canonical_root.glob("*.md"))
        if any(agent_path.stem.startswith(prefix) for prefix in _SPECIALIST_AGENT_PREFIXES)
    ]

    mismatches = 0
    missing = 0
    for canonical_path in specialist_files:
        mirror_path = mirror_root / canonical_path.name
        if not mirror_path.is_file():
            missing += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"claude-specialist-agent-missing-{canonical_path.name}",
                    status=IntegrityStatus.FAIL,
                    message=f"Claude specialist agent has no mirror: {canonical_path.name}",
                    file_path=canonical_path.name,
                )
            )
            continue

        canonical_frontmatter, canonical_body = _split_frontmatter(
            canonical_path.read_text(encoding="utf-8")
        )
        mirror_frontmatter, mirror_body = _split_frontmatter(
            mirror_path.read_text(encoding="utf-8")
        )
        expected_frontmatter = {
            **canonical_frontmatter,
            **get_generated_provenance_fields(
                "specialist-agents",
                canonical_source=f".claude/agents/{canonical_path.name}",
            ),
        }
        if mirror_frontmatter != expected_frontmatter or mirror_body.lstrip(
            "\n"
        ) != canonical_body.lstrip("\n"):
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"claude-specialist-agent-desync-{canonical_path.name}",
                    status=IntegrityStatus.FAIL,
                    message=f"Claude specialist agent mirror desync: {canonical_path.name}",
                    file_path=canonical_path.name,
                )
            )

    if mismatches == 0 and missing == 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="claude-specialist-agents-mirrors",
                status=IntegrityStatus.OK,
                message=(
                    f"All {len(specialist_files)} Claude specialist agent mirrors "
                    "match the generated contract"
                ),
            )
        )


def _check_generated_mirror_provenance(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Validate provenance frontmatter on generated mirror surfaces.

    Pair parity alone cannot catch regressions when both repo and template
    surfaces drift in the same way. Generated mirrors that carry frontmatter
    must retain their governed provenance markers.
    """
    checked = 0
    failures = 0

    surfaces = list(_generated_provenance_surfaces())
    for repo_rel, template_rel in get_internal_specialist_agent_targets().values():
        surfaces.append(("specialist-agents", repo_rel, "*.md"))
        surfaces.append(("specialist-agents", template_rel, "*.md"))

    for family_id, root_rel, glob_pattern in surfaces:
        root = target / root_rel
        if not root.is_dir():
            continue

        for path in sorted(root.rglob(glob_pattern)):
            if not path.is_file():
                continue

            checked += 1
            relative = path.relative_to(root)
            frontmatter, _body = _split_frontmatter(path.read_text(encoding="utf-8"))
            expected = get_generated_provenance_fields(
                family_id,
                _expected_generated_canonical_source(family_id, relative),
            )
            mismatched_keys = [
                key
                for key, expected_value in expected.items()
                if frontmatter.get(key) != expected_value
            ]
            if mismatched_keys:
                failures += 1
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=(
                            f"generated-provenance-{family_id}-"
                            f"{path.relative_to(target).as_posix().replace('/', '-')}"
                        ),
                        status=IntegrityStatus.FAIL,
                        message=(
                            "Generated mirror provenance mismatch: "
                            f"{path.relative_to(target).as_posix()} "
                            f"(expected {', '.join(mismatched_keys)})"
                        ),
                        file_path=path.relative_to(target).as_posix(),
                    )
                )

    if failures == 0 and checked > 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="generated-mirror-provenance",
                status=IntegrityStatus.OK,
                message=f"Validated provenance in {checked} generated mirror files",
            )
        )


def _generated_provenance_surfaces() -> tuple[tuple[str, str, str], ...]:
    surfaces: list[tuple[str, str, str]] = []
    for family in get_mirror_families():
        glob_pattern = _PROVENANCE_GLOB_BY_FAMILY.get(family.family_id)
        if glob_pattern is None:
            continue
        for root_rel in (family.repo_surface_rel, family.template_surface_rel):
            if root_rel:
                surfaces.append((family.family_id, root_rel, glob_pattern))
    return tuple(surfaces)


def _check_public_skill_root_contract(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Reject ungoverned entries in public provider skill roots."""
    checked_roots = 0
    failures = 0

    for root_rel in _PUBLIC_SKILL_ROOTS:
        root = target / root_rel
        if not root.is_dir():
            continue
        checked_roots += 1

        for child in sorted(root.iterdir()):
            if child.name.startswith("."):
                continue
            if child.is_dir() and any(
                child.name.startswith(prefix) for prefix in _PUBLIC_SKILL_ROOT_PREFIXES
            ):
                continue

            failures += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=(
                        "ungoverned-public-skill-entry-"
                        f"{child.relative_to(target).as_posix().replace('/', '-')}"
                    ),
                    status=IntegrityStatus.FAIL,
                    message=(
                        f"Ungoverned public skill entry: {child.relative_to(target).as_posix()}"
                    ),
                    file_path=child.relative_to(target).as_posix(),
                )
            )

    if failures == 0 and checked_roots > 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="public-skill-root-contract",
                status=IntegrityStatus.OK,
                message=f"Validated governed public skill roots in {checked_roots} surfaces",
            )
        )


def _check_public_agent_root_contract(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Reject ungoverned entries in public provider agent roots.

    Public agent roots may contain only governed public agent files and the
    provider-local `internal/` specialist namespace.
    """
    checked_roots = 0
    failures = 0

    for root_rel, allowed_glob in _PUBLIC_AGENT_ROOTS:
        root = target / root_rel
        if not root.is_dir():
            continue
        checked_roots += 1

        for child in sorted(root.iterdir()):
            if child.name.startswith("."):
                continue

            if child.is_dir():
                if child.name != "internal":
                    failures += 1
                    report.checks.append(
                        IntegrityCheckResult(
                            category=IntegrityCategory.MIRROR_SYNC,
                            name=(
                                "ungoverned-public-agent-entry-"
                                f"{child.relative_to(target).as_posix().replace('/', '-')}"
                            ),
                            status=IntegrityStatus.FAIL,
                            message=(
                                "Ungoverned public agent directory: "
                                f"{child.relative_to(target).as_posix()}"
                            ),
                            file_path=child.relative_to(target).as_posix(),
                        )
                    )
                continue

            # Accept iff:
            #   (a) name matches an allowed glob pattern, AND
            #   (b) for non-`*.agent.md` patterns (specialist names like
            #       reviewer-architecture.md), a same-named canonical
            #       counterpart exists under .claude/agents/ — so a stray
            #       reviewer-bad.md without a canonical pair gets flagged
            #       even though it matches the glob.
            matched_glob = any(child.match(pat) for pat in allowed_glob)
            governed = matched_glob
            if matched_glob and not child.match("*.agent.md"):
                canonical_peer = target / ".claude" / "agents" / child.name
                if not canonical_peer.is_file():
                    governed = False
            if not governed:
                failures += 1
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=(
                            "ungoverned-public-agent-entry-"
                            f"{child.relative_to(target).as_posix().replace('/', '-')}"
                        ),
                        status=IntegrityStatus.FAIL,
                        message=(
                            f"Ungoverned public agent file: {child.relative_to(target).as_posix()}"
                        ),
                        file_path=child.relative_to(target).as_posix(),
                    )
                )

    if failures == 0 and checked_roots > 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="public-agent-root-contract",
                status=IntegrityStatus.OK,
                message=f"Validated governed public agent roots in {checked_roots} surfaces",
            )
        )


def _check_non_claude_local_reference_leaks(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Reject leaked `.claude/skills|agents` references in non-Claude mirrors.

    Generated non-Claude mirrors may keep `.claude/...` only in the provenance
    `canonical_source` field. Any other `.claude/skills/` or `.claude/agents/`
    occurrence means the generator failed to localize a provider-facing path.
    """
    checked = 0
    failures = 0

    for root_rel in _NON_CLAUDE_LOCAL_REFERENCE_ROOTS:
        root = target / root_rel
        if not root.is_dir():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            # Specialist agents under `internal/` may legitimately reference
            # `.claude/...` paths in prose (governance docs describing
            # canonical layout). Scripts under `scripts/` should localize
            # paths to their own IDE root and ARE checked here.
            rel_parts = path.relative_to(root).parts
            if "internal" in rel_parts:
                continue

            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            searchable = _CANONICAL_SOURCE_LINE_RE.sub("", text)
            if _STRAY_CLAUDE_LOCAL_REF_RE.search(searchable):
                failures += 1
                report.checks.append(
                    IntegrityCheckResult(
                        category=IntegrityCategory.MIRROR_SYNC,
                        name=(
                            "non-claude-local-reference-leak-"
                            f"{path.relative_to(target).as_posix().replace('/', '-')}"
                        ),
                        status=IntegrityStatus.FAIL,
                        message=(
                            "Stray .claude local reference leak in non-Claude mirror: "
                            f"{path.relative_to(target).as_posix()}"
                        ),
                        file_path=path.relative_to(target).as_posix(),
                    )
                )

    if failures == 0 and checked > 0:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="non-claude-local-reference-contract",
                status=IntegrityStatus.OK,
                message=f"Validated non-Claude local references in {checked} generated files",
            )
        )


def _expected_generated_canonical_source(family_id: str, relative: Path) -> str:
    """Return the canonical source path encoded into generated provenance."""
    rel = relative.as_posix()
    if family_id in {"codex-skills", "gemini-skills", "copilot-skills"}:
        return f".claude/skills/{rel}"
    if family_id in {"codex-agents", "gemini-agents"}:
        return f".claude/agents/{rel}"
    if family_id == "copilot-agents":
        agent_name = relative.name.removesuffix(".agent.md")
        canonical_name = agent_name if agent_name.startswith("ai-") else f"ai-{agent_name}"
        return f".claude/agents/{canonical_name}.md"
    if family_id == "specialist-agents":
        return f".claude/agents/{relative.name}"
    raise ValueError(f"Unsupported generated provenance family: {family_id}")


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Return parsed frontmatter and body from a markdown document."""
    match = _FRONTMATTER_BLOCK_RE.match(text)
    if not match:
        return {}, text

    import yaml

    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, text[match.end() :]


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


def _check_generated_instructions_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: Callable[[Path], str] = _sha256,
) -> None:
    """Check generated Copilot instruction files for repo/template parity."""
    _check_pair_mirror(
        target,
        report,
        *_COPILOT_GENERATED_INSTRUCTIONS_MIRROR,
        "*.instructions.md",
        "copilot-generated-instruction",
        "Generated instruction",
        sha_fn=sha_fn,
        exclude_relatives=_MANUAL_INSTRUCTION_FILES,
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
    has_claude = "claude-code" in enabled
    # Providers that use AGENTS.md: github-copilot, gemini-cli, codex
    has_agents_provider = bool(enabled & {"github-copilot", "gemini-cli", "codex"})

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
