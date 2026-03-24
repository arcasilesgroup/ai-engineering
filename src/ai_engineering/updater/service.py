"""Ownership-safe framework update service.

Updates framework-managed and system-managed files from bundled templates
while strictly respecting ownership boundaries.  Team-managed and
project-managed paths are never modified.

Modes:
- **Dry-run** (default): reports what would change without writing.
- **Apply**: writes changes to disk, with audit logging.  Uses a
  temporary backup so that a partial failure can be rolled back.
"""

from __future__ import annotations

import difflib
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.git.context import get_git_context
from ai_engineering.installer.templates import (
    get_ai_engineering_template_root,
    get_project_template_root,
    resolve_template_maps,
)
from ai_engineering.state.io import append_ndjson, read_json_model
from ai_engineering.state.models import (
    AuditEntry,
    OwnershipMap,
)
from ai_engineering.vcs.repo_context import get_repo_context

logger = logging.getLogger(__name__)

_DIFF_MAX_LINES = 50
"""Maximum number of diff lines shown in CLI output."""

_GOVERNANCE_EXCLUDE_PREFIXES = ("agents/", "skills/")
"""Path prefixes to skip when evaluating governance templates.

Agents and skills are delivered through IDE-specific project templates
(e.g., ``.claude/``, ``.github/agents/``), not under ``.ai-engineering/``.
This mirrors the installer exclude in ``copy_template_tree``."""


@dataclass
class FileChange:
    """Describes a potential or applied file change."""

    path: Path
    action: str  # "create", "update", "skip-denied", "skip-unchanged"
    src: Path | None = None
    diff: str | None = None


@dataclass
class UpdateResult:
    """Summary of an update operation."""

    dry_run: bool
    changes: list[FileChange] = field(default_factory=list)

    @property
    def applied_count(self) -> int:
        """Number of files created or updated."""
        return sum(1 for c in self.changes if c.action in ("create", "update"))

    @property
    def denied_count(self) -> int:
        """Number of files skipped due to ownership denial."""
        return sum(1 for c in self.changes if c.action == "skip-denied")


def update(
    target: Path,
    *,
    dry_run: bool = True,
) -> UpdateResult:
    """Update framework-managed files from bundled templates.

    Respects the ownership map: only framework-managed (allow) and
    system-managed (allow) paths are touched.  Team-managed, project-managed,
    and append-only paths are never modified.

    On apply the service creates a temporary backup of every file that will
    be overwritten.  If any write fails the backup is restored and the error
    is re-raised.

    Args:
        target: Root directory of the target project.
        dry_run: If True (default), only report what would change.

    Returns:
        UpdateResult with details of all changes.
    """
    ai_eng_dir = target / ".ai-engineering"

    # Load ownership map
    ownership_path = ai_eng_dir / "state" / "ownership-map.json"
    if ownership_path.exists():
        ownership = read_json_model(ownership_path, OwnershipMap)
    else:
        ownership = OwnershipMap()

    # --- Phase 1: evaluate all changes (pure, no disk writes) ---
    changes: list[FileChange] = []
    changes.extend(_evaluate_governance_files(ai_eng_dir, ownership))
    changes.extend(_evaluate_project_files(target, ownership))

    result = UpdateResult(dry_run=dry_run, changes=changes)

    if dry_run:
        return result

    # --- Phase 2: apply with backup/rollback ---
    actionable = [c for c in changes if c.action in ("create", "update")]

    if not actionable:
        return result

    backup_dir = _backup_targets(actionable, target)
    try:
        for change in actionable:
            if change.src is None:
                continue
            change.path.parent.mkdir(parents=True, exist_ok=True)
            change.path.write_bytes(change.src.read_bytes())
    except Exception:
        if backup_dir is not None:
            _restore_backup(backup_dir, target)
        raise
    else:
        if backup_dir is not None:
            shutil.rmtree(backup_dir, ignore_errors=True)

    # --- Phase 3: migrate legacy agents/skills directories ---
    _migrate_legacy_dirs(target, ai_eng_dir)

    # --- Phase 4: audit log ---
    _log_update_event(ai_eng_dir, result)

    return result


# ---------------------------------------------------------------------------
# Evaluation (pure - no disk writes)
# ---------------------------------------------------------------------------


def _evaluate_governance_files(
    ai_eng_dir: Path,
    ownership: OwnershipMap,
) -> list[FileChange]:
    """Evaluate changes for files under ``.ai-engineering/`` from templates."""
    template_root = get_ai_engineering_template_root()
    changes: list[FileChange] = []

    for src_file in sorted(template_root.rglob("*")):
        if not src_file.is_file():
            continue

        relative = src_file.relative_to(template_root)
        relative_posix = relative.as_posix()

        # Skip agents/ and skills/ — delivered via IDE project templates
        if any(relative_posix.startswith(p) for p in _GOVERNANCE_EXCLUDE_PREFIXES):
            continue

        ownership_path = f".ai-engineering/{relative_posix}"
        dest = ai_eng_dir / relative

        change = _evaluate_file_change(src_file, dest, ownership_path, ownership)
        changes.append(change)

    return changes


def _evaluate_project_files(
    target: Path,
    ownership: OwnershipMap,
) -> list[FileChange]:
    """Evaluate changes for project-level template files."""
    project_root = get_project_template_root()
    resolved = resolve_template_maps(None)
    changes: list[FileChange] = []

    # 1. Individual file mappings (provider + common)
    all_file_maps = {**resolved.file_map, **resolved.common_file_map}
    for src_relative, dest_relative in sorted(all_file_maps.items()):
        src_file = project_root / src_relative
        if not src_file.is_file():
            continue

        dest = target / dest_relative
        ownership_path = dest_relative

        change = _evaluate_file_change(src_file, dest, ownership_path, ownership)
        changes.append(change)

    # 2. Directory tree mappings (provider + common + VCS)
    all_trees = resolved.tree_list + resolved.common_tree_list + resolved.vcs_tree_list
    for src_tree, dest_tree in all_trees:
        src_dir = project_root / src_tree
        if not src_dir.is_dir():
            continue

        for src_file in sorted(src_dir.rglob("*")):
            if not src_file.is_file():
                continue
            relative_in_tree = src_file.relative_to(src_dir)
            dest = target / dest_tree / relative_in_tree
            ownership_path = f"{dest_tree}/{relative_in_tree.as_posix()}"

            change = _evaluate_file_change(src_file, dest, ownership_path, ownership)
            changes.append(change)

    return changes


def _evaluate_file_change(
    src: Path,
    dest: Path,
    ownership_path: str,
    ownership: OwnershipMap,
) -> FileChange:
    """Evaluate what action should be taken for a single file.

    Args:
        src: Source template file.
        dest: Destination file in the target project.
        ownership_path: Relative path for ownership lookup.
        ownership: The ownership map to consult.

    Returns:
        FileChange describing the evaluated action.
    """
    if not dest.exists():
        # Block creation if there is an explicit deny rule
        if ownership.has_deny_rule(ownership_path):
            return FileChange(path=dest, action="skip-denied", src=src)
        return FileChange(path=dest, action="create", src=src)

    # Check ownership (only ALLOW permits full replacement)
    if not ownership.is_update_allowed(ownership_path):
        return FileChange(path=dest, action="skip-denied", src=src)

    # Compare content
    src_content = src.read_bytes()
    dest_content = dest.read_bytes()

    if src_content == dest_content:
        return FileChange(path=dest, action="skip-unchanged", src=src)

    diff = _generate_diff(src_content, dest_content, ownership_path)
    return FileChange(path=dest, action="update", src=src, diff=diff)


# ---------------------------------------------------------------------------
# Diff generation
# ---------------------------------------------------------------------------


def _generate_diff(
    src_content: bytes,
    dest_content: bytes,
    label: str,
) -> str | None:
    """Generate a unified diff between destination (old) and source (new).

    Args:
        src_content: New content from the template.
        dest_content: Current content on disk.
        label: Path label for the diff header.

    Returns:
        Unified diff string, or ``"[binary file]"`` if the content
        cannot be decoded as UTF-8.
    """
    try:
        old_lines = dest_content.decode("utf-8").splitlines(keepends=True)
        new_lines = src_content.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return "[binary file]"

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
        )
    )
    if not diff_lines:
        return None
    return "".join(diff_lines)


# ---------------------------------------------------------------------------
# Backup / restore
# ---------------------------------------------------------------------------


def _backup_targets(changes: list[FileChange], target: Path) -> Path | None:
    """Create a temporary backup of files that will be overwritten.

    Only backs up files with action ``update`` (existing files being replaced).
    New files (``create``) need no backup.

    Args:
        changes: List of actionable file changes.
        target: Project root used to compute relative paths.

    Returns:
        Path to the backup directory, or None if nothing was backed up.
    """
    to_backup = [c for c in changes if c.action == "update" and c.path.exists()]
    if not to_backup:
        return None

    backup_dir = Path(tempfile.mkdtemp(prefix="ai-eng-backup-"))
    for change in to_backup:
        try:
            relative = change.path.relative_to(target)
        except ValueError:
            continue
        backup_file = backup_dir / relative
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(change.path, backup_file)

    return backup_dir


def _restore_backup(backup_dir: Path, target: Path) -> None:
    """Restore files from a backup directory.

    Args:
        backup_dir: Temporary directory containing backed-up files.
        target: Project root — files are restored relative to this path.
    """
    for backup_file in backup_dir.rglob("*"):
        if not backup_file.is_file():
            continue
        relative = backup_file.relative_to(backup_dir)
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, dest)


# ---------------------------------------------------------------------------
# Legacy migration
# ---------------------------------------------------------------------------


_LEGACY_DIRS = ("agents", "skills")
"""Directory names under ``.ai-engineering/`` that are considered legacy."""


def _migrate_legacy_dirs(target: Path, ai_eng_dir: Path) -> list[str]:
    """Remove legacy agents/ and skills/ directories from .ai-engineering/.

    The migration is safe: a legacy directory is only removed when at least
    one IDE-specific directory already contains files (confirming the normal
    project template update flow has populated them).

    Args:
        target: Project root directory.
        ai_eng_dir: The ``.ai-engineering/`` directory within the project.

    Returns:
        List of legacy directory names that were removed.
    """
    legacy_dirs = [ai_eng_dir / d for d in _LEGACY_DIRS if (ai_eng_dir / d).is_dir()]
    if not legacy_dirs:
        return []

    # Safety check: confirm at least one IDE directory has content.
    # IDE directories live at the project root (e.g., .claude/, .github/agents/,
    # .agents/).
    ide_candidates = [
        target / ".claude",
        target / ".github" / "agents",
        target / ".agents",
    ]
    ide_has_content = any(d.is_dir() and any(d.rglob("*")) for d in ide_candidates)
    if not ide_has_content:
        logger.debug("Skipping legacy migration: no IDE directory with content found")
        return []

    logger.info("Migrating legacy agents/skills to IDE directories...")

    removed: list[str] = []
    for legacy_dir in legacy_dirs:
        name = legacy_dir.name
        shutil.rmtree(legacy_dir)
        removed.append(name)
        logger.info("Removed legacy directory: .ai-engineering/%s", name)

    _log_migration_event(ai_eng_dir, removed)
    return removed


def _log_migration_event(ai_eng_dir: Path, removed: list[str]) -> None:
    """Append an audit-log entry for legacy directory migration."""
    audit_path = ai_eng_dir / "state" / "audit-log.ndjson"
    if not audit_path.parent.exists():
        return
    project_root = ai_eng_dir.parent
    repo_ctx = get_repo_context(project_root)
    git_ctx = get_git_context(project_root)
    entry = AuditEntry(
        event="migrate-legacy-dirs",
        actor="ai-engineering-cli",
        detail={"removed": list(removed)},
        vcs_provider=repo_ctx.provider if repo_ctx else None,
        vcs_organization=repo_ctx.organization if repo_ctx else None,
        vcs_project=repo_ctx.project if repo_ctx else None,
        vcs_repository=repo_ctx.repository if repo_ctx else None,
        branch=git_ctx.branch if git_ctx else None,
        commit_sha=git_ctx.commit_sha if git_ctx else None,
    )
    append_ndjson(audit_path, entry)


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def _log_update_event(ai_eng_dir: Path, result: UpdateResult) -> None:
    """Append an audit-log entry for the update operation."""
    audit_path = ai_eng_dir / "state" / "audit-log.ndjson"
    project_root = ai_eng_dir.parent
    repo_ctx = get_repo_context(project_root)
    git_ctx = get_git_context(project_root)
    entry = AuditEntry(
        event="update",
        actor="ai-engineering-cli",
        detail={"applied": result.applied_count, "denied": result.denied_count},
        vcs_provider=repo_ctx.provider if repo_ctx else None,
        vcs_organization=repo_ctx.organization if repo_ctx else None,
        vcs_project=repo_ctx.project if repo_ctx else None,
        vcs_repository=repo_ctx.repository if repo_ctx else None,
        branch=git_ctx.branch if git_ctx else None,
        commit_sha=git_ctx.commit_sha if git_ctx else None,
    )
    append_ndjson(audit_path, entry)
