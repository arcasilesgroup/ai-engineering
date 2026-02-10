"""Ownership-safe framework update service.

Updates framework-managed and system-managed files from bundled templates
while strictly respecting ownership boundaries.  Team-managed and
project-managed paths are never modified.

Modes:
- **Dry-run** (default): reports what would change without writing.
- **Apply**: writes changes to disk, with audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.installer.templates import (
    _PROJECT_TEMPLATE_MAP,
    get_ai_engineering_template_root,
    get_project_template_root,
)
from ai_engineering.state.io import append_ndjson, read_json_model
from ai_engineering.state.models import (
    AuditEntry,
    FrameworkUpdatePolicy,
    OwnershipMap,
)


@dataclass
class FileChange:
    """Describes a potential or applied file change."""

    path: Path
    action: str  # "create", "update", "skip-denied", "skip-unchanged"


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
    system-managed (allow/append-only) paths are touched.  Team-managed
    and project-managed paths are never modified.

    Args:
        target: Root directory of the target project.
        dry_run: If True (default), only report what would change.

    Returns:
        UpdateResult with details of all changes.
    """
    result = UpdateResult(dry_run=dry_run)
    ai_eng_dir = target / ".ai-engineering"

    # Load ownership map
    ownership_path = ai_eng_dir / "state" / "ownership-map.json"
    if ownership_path.exists():
        ownership = read_json_model(ownership_path, OwnershipMap)
    else:
        ownership = OwnershipMap()

    # 1. Update .ai-engineering/ governance files
    _update_governance_files(target, ai_eng_dir, ownership, result, dry_run=dry_run)

    # 2. Update project-level files (CLAUDE.md, .github/copilot/, etc.)
    _update_project_files(target, ownership, result, dry_run=dry_run)

    # 3. Audit log (only on apply)
    if not dry_run and result.applied_count > 0:
        _log_update_event(ai_eng_dir, result)

    return result


def _update_governance_files(
    target: Path,
    ai_eng_dir: Path,
    ownership: OwnershipMap,
    result: UpdateResult,
    *,
    dry_run: bool,
) -> None:
    """Update files under .ai-engineering/ from templates."""
    template_root = get_ai_engineering_template_root()

    for src_file in sorted(template_root.rglob("*")):
        if not src_file.is_file():
            continue

        relative = src_file.relative_to(template_root)
        ownership_path = f".ai-engineering/{relative.as_posix()}"
        dest = ai_eng_dir / relative

        change = _evaluate_file_change(
            src_file,
            dest,
            ownership_path,
            ownership,
        )
        result.changes.append(change)

        if not dry_run and change.action in ("create", "update"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src_file.read_bytes())


def _update_project_files(
    target: Path,
    ownership: OwnershipMap,
    result: UpdateResult,
    *,
    dry_run: bool,
) -> None:
    """Update project-level template files (CLAUDE.md, copilot/, etc.)."""
    project_root = get_project_template_root()

    for src_relative, dest_relative in sorted(_PROJECT_TEMPLATE_MAP.items()):
        src_file = project_root / src_relative
        if not src_file.is_file():
            continue

        dest = target / dest_relative
        # Project templates are external_framework_managed
        ownership_path = dest_relative

        change = _evaluate_file_change(
            src_file,
            dest,
            ownership_path,
            ownership,
        )
        result.changes.append(change)

        if not dry_run and change.action in ("create", "update"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src_file.read_bytes())


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
        return FileChange(path=dest, action="create")

    # Check ownership
    if not _is_update_allowed(ownership_path, ownership):
        return FileChange(path=dest, action="skip-denied")

    # Compare content
    src_content = src.read_bytes()
    dest_content = dest.read_bytes()

    if src_content == dest_content:
        return FileChange(path=dest, action="skip-unchanged")

    return FileChange(path=dest, action="update")


def _is_update_allowed(path: str, ownership: OwnershipMap) -> bool:
    """Check if a path can be updated by the framework.

    Respects ownership rules:
    - framework-managed + allow → True
    - system-managed + allow → True
    - team-managed + deny → False
    - project-managed + deny → False
    - append-only → False (updater does not append)
    - No rule → False (conservative default)

    Args:
        path: Relative path to check.
        ownership: Ownership map to consult.

    Returns:
        True if update is allowed.
    """
    from fnmatch import fnmatch

    for entry in ownership.paths:
        if fnmatch(path, entry.pattern):
            return entry.framework_update == FrameworkUpdatePolicy.ALLOW
    # No matching rule → deny by default
    return False


def _log_update_event(ai_eng_dir: Path, result: UpdateResult) -> None:
    """Append an audit-log entry for the update operation."""
    audit_path = ai_eng_dir / "state" / "audit-log.ndjson"
    entry = AuditEntry(
        event="update",
        actor="ai-engineering-cli",
        detail=(f"applied={result.applied_count} denied={result.denied_count}"),
    )
    append_ndjson(audit_path, entry)
