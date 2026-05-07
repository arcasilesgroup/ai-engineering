"""Ownership-safe framework update service.

Updates framework-managed and system-managed files from bundled templates
while strictly respecting ownership boundaries.  Team-managed and
project-managed paths are never modified.

Modes:
- **Dry-run** (default): reports what would change without writing.
- **Apply**: writes changes to disk, with canonical framework events. Uses a
  temporary backup so that a partial failure can be rolled back.
"""

from __future__ import annotations

import difflib
import json
import logging
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config, load_manifest_root_entry_points
from ai_engineering.config.manifest import RootEntryPointConfig
from ai_engineering.installer.templates import (
    _PROVIDER_FILE_MAPS,
    _PROVIDER_TREE_MAPS,
    get_ai_engineering_template_root,
    get_project_template_root,
    resolve_template_maps,
)
from ai_engineering.reconciler import (
    ReconcileAction,
    ReconcileApplyResult,
    ReconcileInspection,
    ReconcilePlan,
    ReconcileVerification,
    ResourceReconciler,
)
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import (
    InstallState,
    OwnershipEntry,
    OwnershipMap,
)
from ai_engineering.state.observability import emit_framework_operation
from ai_engineering.state.service import (
    load_install_state,
    remove_legacy_audit_log,
    save_install_state,
)

logger = logging.getLogger(__name__)

_DIFF_MAX_LINES = 50
"""Maximum number of diff lines shown in CLI output."""

_GOVERNANCE_EXCLUDE_PREFIXES = ("agents/", "skills/")
"""Path prefixes to skip when evaluating governance templates.

Agents and skills are delivered through IDE-specific project templates
(e.g., ``.claude/``, ``.github/agents/``), not under ``.ai-engineering/``.
This mirrors the installer exclude in ``copy_template_tree``."""

_SKIP_DIR_NAMES: frozenset[str] = frozenset({"__pycache__"})
"""Directory names excluded from all template walks.

Python bytecode caches are machine-specific and auto-generated;
they must never be compared or synced between template and target."""

_AI_ENGINEERING_DIR = ".ai-engineering"
_GITHUB_DIR = ".github"


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
        if self.action == "orphan":
            return "orphan" if dry_run else "removed"
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
    def orphan_count(self) -> int:
        """Number of files detected as orphans from disabled providers."""
        return sum(1 for c in self.changes if c.action == "orphan")

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
                "orphan": self.orphan_count,
                "failed": 0,
            },
            "changes": [change.to_dict(dry_run=self.dry_run) for change in self.changes],
        }


@dataclass(frozen=True)
class _UpdateSnapshot:
    ai_eng_dir: Path
    ownership_path: Path
    ownership: OwnershipMap
    rules_added: bool
    vcs_provider: str | None
    providers: list[str] | None


@dataclass(frozen=True)
class _UpdatePlanPayload:
    result: UpdateResult
    actionable: list[FileChange]
    orphan_changes: list[FileChange]
    rules_added: bool
    ai_eng_dir: Path
    ownership_path: Path
    ownership: OwnershipMap


@dataclass(frozen=True)
class _UpdateApplyPayload:
    result: UpdateResult
    backup_dir: Path | None
    orphan_backup_dir: Path | None
    actionable: list[FileChange]
    orphan_changes: list[FileChange]
    removed_legacy_dirs: list[str]
    legacy_audit_log_removed: bool


class _UpdateAdapter:
    """Adapt framework update to inspect/plan/apply/verify reconciliation."""

    def __init__(self, target: Path, *, dry_run: bool) -> None:
        self._target = target
        self._dry_run = dry_run
        self._pending_apply_payload: _UpdateApplyPayload | None = None

    @property
    def name(self) -> str:
        return "updater"

    def inspect(self, _context: object) -> ReconcileInspection:
        ai_eng_dir, ownership_path, ownership, rules_added, vcs_provider, providers = (
            _initialize_update_context(self._target, dry_run=self._dry_run)
        )
        return ReconcileInspection(
            resource_name=self.name,
            payload=_UpdateSnapshot(
                ai_eng_dir=ai_eng_dir,
                ownership_path=ownership_path,
                ownership=ownership,
                rules_added=rules_added,
                vcs_provider=vcs_provider,
                providers=providers,
            ),
        )

    def plan(self, inspection: ReconcileInspection, _context: object) -> ReconcilePlan:
        snapshot = self._coerce_snapshot(inspection.payload)
        changes: list[FileChange] = []
        changes.extend(_evaluate_governance_files(snapshot.ai_eng_dir, snapshot.ownership))
        changes.extend(
            _evaluate_project_files(
                self._target,
                snapshot.ownership,
                vcs_provider=snapshot.vcs_provider,
                providers=snapshot.providers,
            )
        )
        orphan_changes = _detect_orphan_files(self._target, snapshot.providers)
        changes.extend(orphan_changes)
        result = UpdateResult(dry_run=self._dry_run, changes=changes)
        actionable = [change for change in changes if change.action in ("create", "update")]
        actions = [
            self._action_from_change(change, index) for index, change in enumerate(changes, 1)
        ]
        return ReconcilePlan(
            resource_name=self.name,
            actions=actions,
            payload=_UpdatePlanPayload(
                result=result,
                actionable=actionable,
                orphan_changes=orphan_changes,
                rules_added=snapshot.rules_added,
                ai_eng_dir=snapshot.ai_eng_dir,
                ownership_path=snapshot.ownership_path,
                ownership=snapshot.ownership,
            ),
        )

    def apply(self, plan: ReconcilePlan, _context: object) -> ReconcileApplyResult:
        payload = self._coerce_plan_payload(plan.payload)
        backup_dir = _apply_actionable_file_changes(payload.actionable, self._target)
        orphan_backup_dir = _backup_orphan_targets(payload.orphan_changes, self._target)
        self._pending_apply_payload = _UpdateApplyPayload(
            result=payload.result,
            backup_dir=backup_dir,
            orphan_backup_dir=orphan_backup_dir,
            actionable=payload.actionable,
            orphan_changes=payload.orphan_changes,
            removed_legacy_dirs=[],
            legacy_audit_log_removed=False,
        )

        if payload.orphan_changes:
            _apply_orphan_deletions(payload.orphan_changes, self._target)

        if payload.rules_added:
            write_json_model(payload.ownership_path, payload.ownership)

        removed_legacy_dirs = _migrate_legacy_dirs(self._target, payload.ai_eng_dir)
        legacy_audit_log_removed = remove_legacy_audit_log(self._target)
        apply_payload = _UpdateApplyPayload(
            result=payload.result,
            backup_dir=backup_dir,
            orphan_backup_dir=orphan_backup_dir,
            actionable=payload.actionable,
            orphan_changes=payload.orphan_changes,
            removed_legacy_dirs=removed_legacy_dirs,
            legacy_audit_log_removed=legacy_audit_log_removed,
        )
        self._pending_apply_payload = apply_payload
        return ReconcileApplyResult(
            resource_name=self.name,
            applied_actions=[
                action.action_id for action in plan.actions if action.action_type != "skip"
            ],
            skipped_actions=[
                action.action_id for action in plan.actions if action.action_type == "skip"
            ],
            payload=apply_payload,
        )

    def verify(
        self,
        apply_result: ReconcileApplyResult,
        _context: object,
    ) -> ReconcileVerification:
        payload = self._coerce_apply_payload(apply_result.payload)
        errors = _verify_update_postconditions(payload, self._target)
        return ReconcileVerification(
            resource_name=self.name,
            passed=not errors,
            errors=errors,
            payload=payload,
        )

    def rollback(
        self,
        plan: ReconcilePlan,
        _context: object,
        reason: BaseException | ReconcileVerification,
    ) -> None:
        payload = plan.payload
        if not isinstance(payload, _UpdatePlanPayload):
            return
        apply_payload = getattr(reason, "payload", None)
        if not isinstance(apply_payload, _UpdateApplyPayload):
            apply_payload = self._pending_apply_payload
        if isinstance(apply_payload, _UpdateApplyPayload):
            _rollback_update_payload(apply_payload, self._target)

    def finalize(
        self,
        plan: ReconcilePlan,
        apply_result: ReconcileApplyResult,
        _verification: ReconcileVerification,
        _context: object,
    ) -> None:
        plan_payload = self._coerce_plan_payload(plan.payload)
        payload = self._coerce_apply_payload(apply_result.payload)
        if (
            payload.actionable
            or plan_payload.rules_added
            or payload.removed_legacy_dirs
            or payload.legacy_audit_log_removed
        ):
            _log_update_event(
                plan_payload.ai_eng_dir,
                payload.result,
                legacy_audit_log_removed=payload.legacy_audit_log_removed,
            )
        if payload.backup_dir is not None:
            shutil.rmtree(payload.backup_dir, ignore_errors=True)
        if payload.orphan_backup_dir is not None:
            shutil.rmtree(payload.orphan_backup_dir, ignore_errors=True)
        self._pending_apply_payload = None

    @staticmethod
    def _action_from_change(change: FileChange, index: int) -> ReconcileAction:
        action_type = "skip" if change.action.startswith("skip-") else change.action
        return ReconcileAction(
            action_id=f"update:{index}",
            action_type=action_type,
            resource=change.path.as_posix(),
            reason=change.reason_code,
            metadata={"explanation": change.explanation},
        )

    @staticmethod
    def _coerce_snapshot(payload: object | None) -> _UpdateSnapshot:
        if not isinstance(payload, _UpdateSnapshot):
            msg = "update reconciler inspection payload must be _UpdateSnapshot"
            raise TypeError(msg)
        return payload

    @staticmethod
    def _coerce_plan_payload(payload: object | None) -> _UpdatePlanPayload:
        if not isinstance(payload, _UpdatePlanPayload):
            msg = "update reconciler plan payload must be _UpdatePlanPayload"
            raise TypeError(msg)
        return payload

    @staticmethod
    def _coerce_apply_payload(payload: object | None) -> _UpdateApplyPayload:
        if not isinstance(payload, _UpdateApplyPayload):
            msg = "update reconciler apply payload must be _UpdateApplyPayload"
            raise TypeError(msg)
        return payload


def _initialize_update_context(
    target: Path,
    *,
    dry_run: bool,
) -> tuple[Path, Path, OwnershipMap, bool, str | None, list[str] | None]:
    """Load ownership and update state before evaluating changes."""
    ai_eng_dir = target / _AI_ENGINEERING_DIR
    state_dir = ai_eng_dir / "state"

    ownership_path = state_dir / "ownership-map.json"
    if ownership_path.exists():
        ownership = read_json_model(ownership_path, OwnershipMap)
    else:
        ownership = OwnershipMap()

    if not dry_run:
        _migrate_install_manifest(ai_eng_dir)
        _migrate_tools_json(ai_eng_dir)

    if not dry_run:
        _migrate_hooks_dir(target)

    if not dry_run:
        _cleanup_legacy_prompts(target)

    install_state = load_install_state(state_dir)

    root_entry_points = load_manifest_root_entry_points(target)
    manifest_path = target / _AI_ENGINEERING_DIR / "manifest.yml"
    providers = (
        load_manifest_config(target).ai_providers.enabled if manifest_path.is_file() else None
    )

    rules_added = _merge_missing_ownership_rules(
        ownership,
        root_entry_points=root_entry_points,
    )

    return ai_eng_dir, ownership_path, ownership, rules_added, install_state.vcs_provider, providers


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
    adapter = _UpdateAdapter(target, dry_run=dry_run)
    run = ResourceReconciler().run(adapter, target, preview=dry_run)  # ty:ignore[invalid-argument-type]

    if dry_run:
        payload = _UpdateAdapter._coerce_plan_payload(run.plan.payload)
        return payload.result

    if run.apply_result is None:
        msg = "update reconciler did not apply changes"
        raise RuntimeError(msg)
    if run.rolled_back or (run.verification is not None and not run.verification.passed):
        details = []
        if run.verification is not None:
            details.extend(run.verification.errors)
        message = "; ".join(details) or "update verification failed"
        raise RuntimeError(f"update verification failed; rolled back changes: {message}")
    payload = _UpdateAdapter._coerce_apply_payload(run.apply_result.payload)
    return payload.result


def _apply_actionable_file_changes(changes: list[FileChange], target: Path) -> Path | None:
    """Apply file create/update actions and keep rollback material until finalize."""
    if not changes:
        return None

    backup_dir = _backup_targets(changes, target)
    try:
        for change in changes:
            if change.src is None:
                continue
            change.path.parent.mkdir(parents=True, exist_ok=True)
            change.path.write_bytes(change.src.read_bytes())
    except Exception:
        _rollback_created_files(changes)
        if backup_dir is not None:
            _restore_backup(backup_dir, target)
            shutil.rmtree(backup_dir, ignore_errors=True)
        raise
    return backup_dir


def _backup_orphan_targets(orphan_changes: list[FileChange], target: Path) -> Path | None:
    """Back up orphan files before deletion so failed applies can restore them."""
    existing = [change for change in orphan_changes if change.path.is_file()]
    if not existing:
        return None

    backup_dir = Path(tempfile.mkdtemp(prefix="ai-eng-orphan-backup-"))
    for change in existing:
        try:
            relative = change.path.relative_to(target)
        except ValueError:
            continue
        backup_file = backup_dir / relative
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(change.path, backup_file)
    return backup_dir


def _restore_orphan_backup(backup_dir: Path, target: Path) -> None:
    """Restore orphan files deleted during a failed update apply pass."""
    for backup_file in backup_dir.rglob("*"):
        if not backup_file.is_file():
            continue
        relative = backup_file.relative_to(backup_dir)
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, dest)


def _verify_update_postconditions(payload: _UpdateApplyPayload, target: Path) -> list[str]:
    """Return postcondition errors after an update apply pass."""
    errors: list[str] = []
    for change in payload.actionable:
        if change.src is None:
            continue
        if not change.path.is_file():
            errors.append(f"missing applied file: {change.path.relative_to(target).as_posix()}")
            continue
        if change.path.read_bytes() != change.src.read_bytes():
            errors.append(
                f"content mismatch after update: {change.path.relative_to(target).as_posix()}"
            )

    remaining_orphans = [
        change.path.relative_to(target).as_posix()
        for change in payload.orphan_changes
        if change.path.exists()
    ]
    for orphan in remaining_orphans:
        errors.append(f"orphan still exists after update: {orphan}")
    return errors


def _rollback_update_payload(payload: _UpdateApplyPayload, target: Path) -> None:
    """Roll back applied file changes owned by the update reconciler."""
    _rollback_created_files(payload.actionable)
    if payload.backup_dir is not None:
        _restore_backup(payload.backup_dir, target)
        shutil.rmtree(payload.backup_dir, ignore_errors=True)
    if payload.orphan_backup_dir is not None:
        _restore_orphan_backup(payload.orphan_backup_dir, target)
        shutil.rmtree(payload.orphan_backup_dir, ignore_errors=True)


def _rollback_created_files(changes: list[FileChange]) -> None:
    """Remove files created by a failed update apply pass."""
    for change in changes:
        if change.action != "create" or not change.path.exists():
            continue
        try:
            change.path.unlink()
        except OSError:
            logger.debug("could not roll back created file: %s", change.path)


# ---------------------------------------------------------------------------
# Ownership auto-merge
# ---------------------------------------------------------------------------


def _merge_missing_ownership_rules(
    ownership: OwnershipMap,
    *,
    root_entry_points: Mapping[str, RootEntryPointConfig] | None = None,
) -> bool:
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
    defaults = default_ownership_map(root_entry_points=root_entry_points)
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

        # Skip __pycache__ — machine-specific bytecode, never synced
        if _SKIP_DIR_NAMES & set(relative.parts):
            continue

        relative_posix = relative.as_posix()

        # Skip agents/ and skills/ — delivered via IDE project templates
        if any(relative_posix.startswith(p) for p in _GOVERNANCE_EXCLUDE_PREFIXES):
            continue

        ownership_path = f"{_AI_ENGINEERING_DIR}/{relative_posix}"
        dest = ai_eng_dir / relative

        change = _evaluate_file_change(src_file, dest, ownership_path, ownership)
        changes.append(change)

    return changes


def _evaluate_project_files(
    target: Path,
    ownership: OwnershipMap,
    *,
    vcs_provider: str | None = None,
    providers: list[str] | None = None,
) -> list[FileChange]:
    """Evaluate changes for project-level template files."""
    project_root = get_project_template_root()
    resolved = resolve_template_maps(providers, vcs_provider=vcs_provider)
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
            if _SKIP_DIR_NAMES & set(relative_in_tree.parts):
                continue
            dest = target / dest_tree / relative_in_tree
            ownership_path = f"{dest_tree}/{relative_in_tree.as_posix()}"

            change = _evaluate_file_change(src_file, dest, ownership_path, ownership)
            changes.append(change)

    return changes


def _detect_orphan_files(
    target: Path,
    active_providers: list[str] | None,
) -> list[FileChange]:
    """Detect files on disk belonging to disabled providers.

    A file is an orphan when:
    1. It belongs to a provider that is NOT in the active providers list.
    2. No active provider also maps to the same destination path (shared
       file rule -- e.g., AGENTS.md is used by copilot, gemini, codex).
    3. The file exists on disk.

    Args:
        target: Project root directory.
        active_providers: Providers enabled in the manifest.  When None
            (no manifest), all providers are considered active and no
            orphans are detected.

    Returns:
        List of FileChange entries with ``action="orphan"``.
    """
    if active_providers is None:
        return []

    from ai_engineering.installer.templates import _canonicalize_provider

    canonical_active = [_canonicalize_provider(p) for p in active_providers]

    all_known = set(_PROVIDER_FILE_MAPS.keys()) | set(_PROVIDER_TREE_MAPS.keys())
    disabled = all_known - set(canonical_active)

    if not disabled:
        return []

    active_file_dests, active_tree_dests = _active_provider_destinations(canonical_active)
    return [
        orphan
        for provider in sorted(disabled)
        for orphan in _provider_orphan_changes(
            target,
            provider,
            active_file_dests=active_file_dests,
            active_tree_dests=active_tree_dests,
        )
    ]


def _active_provider_destinations(active_providers: list[str]) -> tuple[set[str], set[str]]:
    """Return file and tree destinations still owned by active providers."""
    active_file_dests: set[str] = set()
    active_tree_dests: set[str] = set()
    for provider in active_providers:
        active_file_dests.update(_PROVIDER_FILE_MAPS.get(provider, {}).values())
        active_tree_dests.update(dest for _src_tree, dest in _PROVIDER_TREE_MAPS.get(provider, []))
    return active_file_dests, active_tree_dests


def _provider_orphan_changes(
    target: Path,
    provider: str,
    *,
    active_file_dests: set[str],
    active_tree_dests: set[str],
) -> list[FileChange]:
    """Return orphan changes for one disabled provider."""
    return [
        *_provider_file_orphans(target, provider, active_file_dests),
        *_provider_tree_orphans(target, provider, active_tree_dests),
    ]


def _provider_file_orphans(
    target: Path,
    provider: str,
    active_file_dests: set[str],
) -> list[FileChange]:
    """Return orphaned individual-file mappings for one disabled provider."""
    orphans: list[FileChange] = []
    for destination in _PROVIDER_FILE_MAPS.get(provider, {}).values():
        if destination in active_file_dests:
            continue
        dest = target / destination
        if dest.is_file():
            orphans.append(_orphan_change(dest, provider))
    return orphans


def _provider_tree_orphans(
    target: Path,
    provider: str,
    active_tree_dests: set[str],
) -> list[FileChange]:
    """Return orphaned tree-mapping files for one disabled provider."""
    orphans: list[FileChange] = []
    for _src_tree, dest_tree in _PROVIDER_TREE_MAPS.get(provider, []):
        if dest_tree in active_tree_dests:
            continue
        tree_path = target / dest_tree
        if not tree_path.is_dir():
            continue
        orphans.extend(_orphan_files_in_tree(tree_path, provider))
    return orphans


def _orphan_files_in_tree(tree_path: Path, provider: str) -> list[FileChange]:
    """Return orphan changes for files below a disabled provider tree."""
    return [
        _orphan_change(path, provider)
        for path in sorted(tree_path.rglob("*"))
        if path.is_file() and not (_SKIP_DIR_NAMES & set(path.relative_to(tree_path).parts))
    ]


def _orphan_change(path: Path, provider: str) -> FileChange:
    """Build the standard disabled-provider orphan change."""
    return FileChange(
        path=path,
        action="orphan",
        reason_code="disabled-provider",
        explanation=f"provider '{provider}' is no longer enabled",
    )


def _apply_orphan_deletions(orphan_changes: list[FileChange], target: Path) -> None:
    """Delete orphan files from disk and clean up empty parent directories.

    Args:
        orphan_changes: List of FileChange entries with ``action="orphan"``.
        target: Project root directory (deletion stops at this boundary).
    """
    deleted_dirs: set[Path] = set()

    for change in orphan_changes:
        try:
            change.path.unlink()
        except FileNotFoundError:
            pass
        else:
            deleted_dirs.add(change.path.parent)

    # Remove empty parent directories bottom-up, stopping at target root.
    for d in sorted(deleted_dirs, key=lambda p: len(p.parts), reverse=True):
        current = d
        while current != target and current.is_dir():
            try:
                if any(current.iterdir()):
                    break
                current.rmdir()
                current = current.parent
            except OSError:
                break


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
    legacy = target / _GITHUB_DIR / "prompts"
    new = target / _GITHUB_DIR / "skills"
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
    new_hooks = target / _AI_ENGINEERING_DIR / "scripts" / "hooks"

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
    # .codex/, .gemini/).
    ide_candidates = [
        target / ".claude",
        target / _GITHUB_DIR / "agents",
        target / ".codex",
        target / ".gemini",
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
    """Emit a framework operation event for legacy directory migration."""
    if not (ai_eng_dir / "state").exists():
        return
    emit_framework_operation(
        ai_eng_dir.parent,
        operation="migrate-legacy-dirs",
        component="updater",
        source="cli",
        metadata={"removed": list(removed)},
    )


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def _log_update_event(
    ai_eng_dir: Path,
    result: UpdateResult,
    *,
    legacy_audit_log_removed: bool = False,
) -> None:
    """Emit a framework operation event for update."""
    emit_framework_operation(
        ai_eng_dir.parent,
        operation="update",
        component="updater",
        source="cli",
        metadata={
            "applied": result.applied_count,
            "denied": result.denied_count,
            "legacy_audit_log_removed": legacy_audit_log_removed,
        },
    )
