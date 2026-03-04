"""Category 2: Mirror Sync — SHA-256 compare canonical vs template mirrors."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    _CLAUDE_COMMANDS_MIRROR,
    _COPILOT_AGENTS_MIRROR,
    _COPILOT_PROMPTS_MIRROR,
    _GOVERNANCE_MIRROR,
    CheckStatus,
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    _glob_files,
    _is_excluded,
    _is_source_repo,
    _sha256,
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
                status=CheckStatus.OK,
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
                status=CheckStatus.FAIL,
                message=f"Canonical root not found: {_GOVERNANCE_MIRROR[0]}",
            )
        )
        return

    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="mirror-root",
                status=CheckStatus.FAIL,
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
                    status=CheckStatus.FAIL,
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
                status=CheckStatus.FAIL,
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
                status=CheckStatus.WARN,
                message=f"Mirror file has no canonical source: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    # Claude commands mirror
    _check_claude_commands_mirror(target, report, _sha)

    # Copilot prompts and agents mirrors
    _check_copilot_prompts_mirror(target, report, _sha)
    _check_copilot_agents_mirror(target, report, _sha)

    if mismatches == 0 and not (canonical_relatives - mirror_relatives):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="governance-mirrors",
                status=CheckStatus.OK,
                message=f"All {checked} mirror pairs in sync",
            )
        )


def _check_claude_commands_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: object = _sha256,
) -> None:
    """Check .claude/commands/ mirror sync."""
    _sha = sha_fn  # type: ignore[assignment]
    canonical_root = target / _CLAUDE_COMMANDS_MIRROR[0]
    mirror_root = target / _CLAUDE_COMMANDS_MIRROR[1]

    if not canonical_root.is_dir():
        return  # .claude/commands/ is optional
    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="claude-commands-mirror-root",
                status=CheckStatus.FAIL,
                message="Claude commands mirror directory not found",
            )
        )
        return

    canonical_files = {
        f.relative_to(canonical_root) for f in sorted(canonical_root.rglob("*.md")) if f.is_file()
    }
    mirror_files = {
        f.relative_to(mirror_root) for f in sorted(mirror_root.rglob("*.md")) if f.is_file()
    }

    mismatches = 0
    for rel in sorted(canonical_files & mirror_files):
        if _sha(canonical_root / rel) != _sha(mirror_root / rel):
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"claude-cmd-desync-{rel.as_posix()}",
                    status=CheckStatus.FAIL,
                    message=f"Claude command mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    for rel in sorted(canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"claude-cmd-missing-{rel.as_posix()}",
                status=CheckStatus.FAIL,
                message=f"Claude command has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    if mismatches == 0 and not (canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="claude-commands-mirrors",
                status=CheckStatus.OK,
                message=f"All {len(canonical_files & mirror_files)} Claude command mirrors in sync",
            )
        )


def _check_copilot_prompts_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: object = _sha256,
) -> None:
    """Check .github/prompts/ mirror sync with templates."""
    _sha = sha_fn  # type: ignore[assignment]
    canonical_root = target / _COPILOT_PROMPTS_MIRROR[0]
    mirror_root = target / _COPILOT_PROMPTS_MIRROR[1]

    if not canonical_root.is_dir():
        return  # .github/prompts/ is optional
    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="copilot-prompts-mirror-root",
                status=CheckStatus.FAIL,
                message="Copilot prompts mirror directory not found",
            )
        )
        return

    canonical_files = {
        f.relative_to(canonical_root)
        for f in sorted(canonical_root.rglob("*.prompt.md"))
        if f.is_file()
    }
    mirror_files = {
        f.relative_to(mirror_root) for f in sorted(mirror_root.rglob("*.prompt.md")) if f.is_file()
    }

    mismatches = 0
    for rel in sorted(canonical_files & mirror_files):
        if _sha(canonical_root / rel) != _sha(mirror_root / rel):
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"copilot-prompt-desync-{rel.as_posix()}",
                    status=CheckStatus.FAIL,
                    message=f"Copilot prompt mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    for rel in sorted(canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"copilot-prompt-missing-{rel.as_posix()}",
                status=CheckStatus.FAIL,
                message=f"Copilot prompt has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    if mismatches == 0 and not (canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="copilot-prompts-mirrors",
                status=CheckStatus.OK,
                message=f"All {len(canonical_files & mirror_files)} Copilot prompt mirrors in sync",
            )
        )


def _check_copilot_agents_mirror(
    target: Path,
    report: IntegrityReport,
    sha_fn: object = _sha256,
) -> None:
    """Check .github/agents/ mirror sync with templates."""
    _sha = sha_fn  # type: ignore[assignment]
    canonical_root = target / _COPILOT_AGENTS_MIRROR[0]
    mirror_root = target / _COPILOT_AGENTS_MIRROR[1]

    if not canonical_root.is_dir():
        return  # .github/agents/ is optional
    if not mirror_root.is_dir():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="copilot-agents-mirror-root",
                status=CheckStatus.FAIL,
                message="Copilot agents mirror directory not found",
            )
        )
        return

    canonical_files = {
        f.relative_to(canonical_root)
        for f in sorted(canonical_root.rglob("*.agent.md"))
        if f.is_file()
    }
    mirror_files = {
        f.relative_to(mirror_root) for f in sorted(mirror_root.rglob("*.agent.md")) if f.is_file()
    }

    mismatches = 0
    for rel in sorted(canonical_files & mirror_files):
        if _sha(canonical_root / rel) != _sha(mirror_root / rel):
            mismatches += 1
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name=f"copilot-agent-desync-{rel.as_posix()}",
                    status=CheckStatus.FAIL,
                    message=f"Copilot agent mirror desync: {rel.as_posix()}",
                    file_path=rel.as_posix(),
                )
            )

    for rel in sorted(canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name=f"copilot-agent-missing-{rel.as_posix()}",
                status=CheckStatus.FAIL,
                message=f"Copilot agent has no mirror: {rel.as_posix()}",
                file_path=rel.as_posix(),
            )
        )

    if mismatches == 0 and not (canonical_files - mirror_files):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="copilot-agents-mirrors",
                status=CheckStatus.OK,
                message=f"All {len(canonical_files & mirror_files)} Copilot agent mirrors in sync",
            )
        )
