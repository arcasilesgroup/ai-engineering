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
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from ai_engineering.git.context import get_git_context
from ai_engineering.installer.templates import (
    get_ai_engineering_template_root,
    get_project_template_root,
    resolve_template_maps,
)
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import append_ndjson, read_json_model, write_json_model
from ai_engineering.state.models import (
    AuditEntry,
    InstallState,
    OwnershipEntry,
    OwnershipMap,
)
from ai_engineering.state.service import load_install_state, save_install_state
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
    reason_code: str = "unspecified"
    explanation: str = ""
    recommended_action: str | None = None

    def outcome(self, *, dry_run: bool) -> str:
        """Return a user-facing outcome label for the change."""
        if self.action in ("create", "update"):
            return "available" if dry_run else "applied"
        if self.action == "skip-denied":
            return "protected"
        if self.action == "skip-unchanged":
            return "unchanged"
        return "failed"

    def to_dict(self, *, dry_run: bool) -> dict[str, str | None]:
        """Return a structured JSON-safe representation of the change."""
        return {
            "path": str(self.path),
            "action": self.action,
            "outcome": self.outcome(dry_run=dry_run),
            "reason_code": self.reason_code,
            "explanation": self.explanation,
            "recommended_action": self.recommended_action,
            "diff": self.diff,
        }


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

    @property
    def unchanged_count(self) -> int:
        """Number of files that already match the bundled templates."""
        return sum(1 for c in self.changes if c.action == "skip-unchanged")

    @property
    def available_count(self) -> int:
        """Number of files that are available to create or update."""
        return sum(1 for c in self.changes if c.action in ("create", "update"))

    @property
    def protected_count(self) -> int:
        """Number of files intentionally protected by ownership rules."""
        return self.denied_count

    def to_dict(self) -> dict[str, object]:
        """Return a structured summary for JSON output."""
        return {
            "mode": "APPLIED" if not self.dry_run else "PREVIEW",
            "applied": self.applied_count,
            "denied": self.denied_count,
            "grouped_counts": {
                "applied": self.applied_count if not self.dry_run else 0,
                "available": self.available_count if self.dry_run else 0,
                "protected": self.protected_count,
                "unchanged": self.unchanged_count,
                "failed": 0,
            },
            "changes": [change.to_dict(dry_run=self.dry_run) for change in self.changes],
        }


def _initialize_update_context(
    target: Path,
    *,
    dry_run: bool,
) -> tuple[Path, Path, OwnershipMap, bool, str | None]:
    """Load ownership and update state before evaluating changes."""
    ai_eng_dir = target / ".ai-engineering"
    state_dir = ai_eng_dir / "state"

    ownership_path = state_dir / "ownership-map.json"
    if ownership_path.exists():
        ownership = read_json_model(ownership_path, OwnershipMap)
    else:
        ownership = OwnershipMap()

    rules_added = _merge_missing_ownership_rules(ownership)

    if not dry_run:
        _migrate_install_manifest(ai_eng_dir)
        _migrate_tools_json(ai_eng_dir)

    _migrate_hooks_dir(target)

    if not dry_run:
        _cleanup_legacy_prompts(target)

    install_state = load_install_state(state_dir)
    return ai_eng_dir, ownership_path, ownership, rules_added, install_state.vcs_provider


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
    ai_eng_dir, ownership_path, ownership, rules_added, vcs_provider = _initialize_update_context(
        target,
        dry_run=dry_run,
    )

    # --- Phase 1: evaluate all changes (pure, no disk writes) ---
    changes: list[FileChange] = []
    changes.extend(_evaluate_governance_files(ai_eng_dir, ownership))
    changes.extend(_evaluate_project_files(target, ownership, vcs_provider=vcs_provider))

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

    # --- Phase 3: persist merged ownership rules ---
    if rules_added:
        write_json_model(ownership_path, ownership)

    # --- Phase 4: migrate legacy agents/skills directories ---
    _migrate_legacy_dirs(target, ai_eng_dir)

    # --- Phase 5: audit log ---
    _log_update_event(ai_eng_dir, result)

    return result


# ---------------------------------------------------------------------------
# Ownership auto-merge
# ---------------------------------------------------------------------------


def _merge_missing_ownership_rules(ownership: OwnershipMap) -> bool:
    """Add missing default ownership rules to an existing map.

    Inserts new rules at the START of the list so that specific patterns
    (e.g., ``.claude/settings.json`` deny) match before broad globs
    (e.g., ``.claude/**`` allow).  Existing rules are never modified
    or removed.

    Args:
        ownership: The ownership map to merge into (mutated in place).

    Returns:
        True if any rules were added, False if already up-to-date.
    """
    existing_patterns = {entry.pattern for entry in ownership.paths}
    defaults = default_ownership_map()
    to_add = [entry for entry in defaults.paths if entry.pattern not in existing_patterns]

    if not to_add:
        return False

    # Insert at position 0 so new specific rules match before old broad ones
    ownership.paths = to_add + ownership.paths
    return True


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
    *,
    vcs_provider: str | None = None,
) -> list[FileChange]:
    """Evaluate changes for project-level template files."""
    project_root = get_project_template_root()
    resolved = resolve_template_maps(None, vcs_provider=vcs_provider)
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
    ownership_entry = _match_ownership_entry(ownership, ownership_path)

    if not dest.exists():
        # Block creation if there is an explicit deny rule
        if ownership.has_deny_rule(ownership_path):
            return FileChange(
                path=dest,
                action="skip-denied",
                src=src,
                reason_code=_protected_reason_code(ownership_entry, is_create=True),
                explanation=_protected_explanation(ownership_entry, is_create=True),
            )
        return FileChange(
            path=dest,
            action="create",
            src=src,
            reason_code="missing-framework-file",
            explanation=(
                "A framework-managed file is missing and can be created from the bundled template."
            ),
            recommended_action="Apply the update to create this file.",
        )

    # Check ownership (only ALLOW permits full replacement)
    if not ownership.is_update_allowed(ownership_path):
        return FileChange(
            path=dest,
            action="skip-denied",
            src=src,
            reason_code=_protected_reason_code(ownership_entry, is_create=False),
            explanation=_protected_explanation(ownership_entry, is_create=False),
        )

    # Compare content
    src_content = src.read_bytes()
    dest_content = dest.read_bytes()

    if src_content == dest_content:
        return FileChange(
            path=dest,
            action="skip-unchanged",
            src=src,
            reason_code="already-current",
            explanation="This file already matches the bundled framework template.",
        )

    diff = _generate_diff(src_content, dest_content, ownership_path)
    return FileChange(
        path=dest,
        action="update",
        src=src,
        diff=diff,
        reason_code="template-drift",
        explanation=("This installed file differs from the current bundled framework template."),
        recommended_action=(
            "Apply the update to replace it with the latest framework-managed version."
        ),
    )


def _match_ownership_entry(ownership: OwnershipMap, path: str) -> OwnershipEntry | None:
    """Return the first ownership entry matching a path, if any."""
    for entry in ownership.paths:
        if fnmatch(path, entry.pattern):
            return entry
    return None


def _protected_reason_code(entry: OwnershipEntry | None, *, is_create: bool) -> str:
    """Return a stable reason code for protected paths."""
    suffix = "create" if is_create else "update"
    if entry is None:
        return f"protected-{suffix}"
    if entry.owner.value == "team-managed":
        return f"team-managed-{suffix}-protected"
    if entry.framework_update.value == "append-only":
        return f"append-only-{suffix}-protected"
    if entry.framework_update.value == "deny":
        return f"ownership-deny-{suffix}-protected"
    return f"protected-{suffix}"


def _protected_explanation(entry: OwnershipEntry | None, *, is_create: bool) -> str:
    """Return a user-facing explanation for protected paths."""
    operation = "created" if is_create else "replaced"
    if entry is None:
        return (
            "This path is protected by ownership rules, so ai-eng update will not "
            f"have it {operation}. No action is required unless you intend to "
            "manage it manually."
        )
    if entry.owner.value == "team-managed":
        return (
            "This is a team-managed path, so ai-eng update intentionally leaves "
            f"it unchanged and will not have it {operation}. No action is "
            "required."
        )
    if entry.framework_update.value == "append-only":
        return (
            "This path is append-only in the ownership map, so ai-eng update "
            "will not fully replace it. No action is required unless you intend "
            "to update it manually."
        )
    if entry.framework_update.value == "deny":
        return (
            "An explicit ownership rule protects this path, so ai-eng update will "
            f"not have it {operation}. No action is required unless you intend to "
            "override the policy manually."
        )
    return (
        "This path is protected by ownership rules, so ai-eng update will not "
        f"have it {operation}. No action is required."
    )


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
# State-file migration (spec-068)
# ---------------------------------------------------------------------------


def _migrate_install_manifest(ai_eng_dir: Path) -> bool:
    """Migrate legacy ``install-manifest.json`` to ``install-state.json``.

    If both old and new files exist, the old file takes precedence
    (re-migrate). After successful conversion the old file is deleted.

    Args:
        ai_eng_dir: The ``.ai-engineering/`` directory.

    Returns:
        True if a migration was performed, False otherwise.
    """
    state_dir = ai_eng_dir / "state"
    old_path = state_dir / "install-manifest.json"

    if not old_path.exists():
        return False

    logger.info("Migrating install-manifest.json -> install-state.json")

    data = json.loads(old_path.read_text(encoding="utf-8"))
    state = InstallState.from_legacy_dict(data)

    save_install_state(state_dir, state)
    old_path.unlink()
    return True


def _migrate_tools_json(ai_eng_dir: Path) -> bool:
    """Merge legacy ``tools.json`` platform data into ``install-state.json``.

    Loads (or creates) the current ``install-state.json``, then merges
    platform entries extracted from ``tools.json``. After merge, the old
    file is deleted.

    Args:
        ai_eng_dir: The ``.ai-engineering/`` directory.

    Returns:
        True if a migration was performed, False otherwise.
    """
    state_dir = ai_eng_dir / "state"
    tools_path = state_dir / "tools.json"

    if not tools_path.exists():
        return False

    logger.info("Migrating tools.json -> install-state.json (platforms)")

    tools_data = json.loads(tools_path.read_text(encoding="utf-8"))

    # Load existing install-state (or defaults if it doesn't exist yet)
    install_state = load_install_state(state_dir)

    # Extract platforms from tools.json via the dict-based helper
    from ai_engineering.state.models import _extract_platforms_from_dict

    merged_platforms = _extract_platforms_from_dict(tools_data)

    # Merge: tools.json platforms overwrite matching keys
    install_state.platforms.update(merged_platforms)

    save_install_state(state_dir, install_state)
    tools_path.unlink()
    return True


# ---------------------------------------------------------------------------
# Legacy migration
# ---------------------------------------------------------------------------


def _cleanup_legacy_prompts(target: Path) -> None:
    """Remove legacy ``.github/prompts/`` when ``.github/skills/`` exists.

    The framework migrated from flat prompt files to directory-based Agent
    Skills in spec-077.  Projects that upgrade retain orphaned prompt files
    that may confuse Copilot if both directories are present.
    """
    legacy = target / ".github" / "prompts"
    new = target / ".github" / "skills"
    if not legacy.is_dir() or not new.is_dir():
        return
    for f in sorted(legacy.rglob("*"), reverse=True):
        if f.is_file():
            logger.info("Removing legacy prompt: %s", f.relative_to(target))
            f.unlink()
    # Remove empty directories bottom-up
    for d in sorted(legacy.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    if legacy.is_dir() and not any(legacy.iterdir()):
        legacy.rmdir()
        logger.info("Removed legacy directory: .github/prompts/")


def _migrate_hooks_dir(target: Path) -> None:
    """Migrate hooks from legacy ``scripts/hooks/`` to ``.ai-engineering/scripts/hooks/``.

    Idempotent: if the new path already exists, skip silently.
    """
    old_hooks = target / "scripts" / "hooks"
    new_hooks = target / ".ai-engineering" / "scripts" / "hooks"

    if not old_hooks.is_dir():
        return
    if new_hooks.is_dir():
        logger.debug("Hooks already at new path, skipping migration")
        return

    logger.info("Migrating hooks from scripts/hooks/ to .ai-engineering/scripts/hooks/")
    new_hooks.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(old_hooks, new_hooks)
    shutil.rmtree(old_hooks)

    # Remove empty scripts/ directory if nothing else is in it
    scripts_dir = target / "scripts"
    if scripts_dir.is_dir() and not any(scripts_dir.iterdir()):
        scripts_dir.rmdir()


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
