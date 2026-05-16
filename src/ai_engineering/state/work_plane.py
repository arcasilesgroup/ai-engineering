"""Active work-plane path resolution.

Spec-123 Theme 1 collapsed `.ai-engineering/specs/` to exactly three canonical
files: ``spec.md``, ``plan.md``, ``_history.md``. The work-plane resolver no
longer surfaces the dead HX-02 artifacts (task-ledger.json, current-summary.md,
history-summary.md, handoffs/, evidence/); CI guard
``tests/unit/specs/test_canonical_structure.py`` enforces the three-file
contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.state.models import TaskLedger

ACTIVE_WORK_PLANE_POINTER_REL = Path(".ai-engineering") / "specs" / "active-work-plane.json"
# POSIX-style relative key used by gate config-hash maps so the dictionary
# keys stay platform-agnostic (Path.__str__ uses os.sep on Windows).
ACTIVE_WORK_PLANE_POINTER_KEY = ".ai-engineering/specs/active-work-plane.json"
_LEGACY_SPECS_DIR_REL = ACTIVE_WORK_PLANE_POINTER_REL.parent
_HISTORY_FILENAME = "_history.md"
_NO_ACTIVE_SPEC_PREFIX = "# No active spec"


@dataclass(frozen=True)
class ActiveWorkPlane:
    """Resolved paths for the currently active work plane."""

    project_root: Path
    ai_eng_dir: Path
    specs_dir: Path
    spec_path: Path
    plan_path: Path
    history_path: Path


def active_work_plane_pointer_path(project_root: Path) -> Path:
    """Return the canonical pointer file path for the active work plane."""
    return project_root / ACTIVE_WORK_PLANE_POINTER_REL


def write_active_work_plane_pointer(project_root: Path, specs_dir: Path) -> None:
    """Persist a project-relative pointer to the active work-plane root.

    Pointing at the legacy singleton specs dir clears the pointer instead of
    writing a redundant compatibility artifact.
    """
    candidate = specs_dir if specs_dir.is_absolute() else project_root / specs_dir
    project_root_resolved = project_root.resolve()
    try:
        relative_specs_dir = candidate.resolve().relative_to(project_root_resolved)
    except ValueError as exc:
        msg = "Active work-plane specs dir must stay inside the project root"
        raise ValueError(msg) from exc

    if relative_specs_dir == _LEGACY_SPECS_DIR_REL:
        clear_active_work_plane_pointer(project_root)
        return

    pointer_path = active_work_plane_pointer_path(project_root)
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(
        json.dumps({"specsDir": relative_specs_dir.as_posix()}, sort_keys=True),
        encoding="utf-8",
    )


def clear_active_work_plane_pointer(project_root: Path) -> None:
    """Remove the active work-plane pointer when present."""
    pointer_path = active_work_plane_pointer_path(project_root)
    pointer_path.unlink(missing_ok=True)


def ensure_work_plane_artifacts(specs_dir: Path) -> None:
    """Ensure the canonical three-file contract: spec.md, plan.md, _history.md.

    Creates each missing file with empty content. Existing files are left
    untouched.
    """
    specs_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("spec.md", "plan.md", _HISTORY_FILENAME):
        candidate = specs_dir / filename
        if not candidate.exists():
            candidate.write_text("", encoding="utf-8")


def read_task_ledger(project_root: Path) -> TaskLedger | None:
    """Backwards-compat shim — task ledger no longer exists post-spec-123.

    Returns ``None`` unconditionally. Callers should treat this as "no ledger
    available" and continue gracefully. Removed in a future cleanup once all
    consumers stop importing this symbol.
    """
    return None


def task_ledger_has_open_tasks(project_root: Path) -> bool:
    """Backwards-compat shim — task ledger no longer exists post-spec-123.

    Always returns ``False``.
    """
    return False


def active_work_plane_placeholder_fallback_id(project_root: Path) -> str | None:
    """Backwards-compat shim — fallback id no longer derives from task ledger.

    Always returns ``None``. The "no active spec" placeholder check now relies
    solely on ``spec.md`` content.
    """
    return None


def active_work_plane_has_active_spec(project_root: Path) -> bool:
    """Return True when spec.md indicates active work (not the placeholder)."""
    spec_path = resolve_active_work_plane(project_root).spec_path
    if not spec_path.exists():
        return False
    try:
        text = spec_path.read_text(encoding="utf-8").lstrip()
    except OSError:
        return False
    return not text.startswith(_NO_ACTIVE_SPEC_PREFIX)


def write_task_ledger(project_root: Path, ledger: TaskLedger) -> Path:
    """Backwards-compat shim — task ledger writes are a no-op post-spec-123.

    Returns the would-be ledger path for callers that still inspect it. Does
    not write to disk.
    """
    return resolve_active_work_plane(project_root).specs_dir / "task-ledger.json"


def _pointer_specs_dir(project_root: Path) -> Path | None:
    """Return the pointer-selected specs dir when a valid pointer exists."""
    pointer_path = active_work_plane_pointer_path(project_root)
    if not pointer_path.exists():
        return None

    try:
        payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    specs_dir_value = payload.get("specsDir")
    if not isinstance(specs_dir_value, str) or not specs_dir_value.strip():
        return None

    raw_specs_dir = Path(specs_dir_value)
    if raw_specs_dir.is_absolute():
        return None
    specs_dir = project_root / raw_specs_dir
    try:
        specs_dir.resolve().relative_to(project_root.resolve())
    except ValueError:
        return None
    return specs_dir


def resolve_active_work_plane(project_root: Path) -> ActiveWorkPlane:
    """Resolve the active work plane.

    Returns the canonical three-file contract (spec.md, plan.md, _history.md)
    rooted at the active specs dir.
    """
    ai_eng_dir = project_root / ".ai-engineering"
    specs_dir = _pointer_specs_dir(project_root) or (ai_eng_dir / "specs")
    return ActiveWorkPlane(
        project_root=project_root,
        ai_eng_dir=ai_eng_dir,
        specs_dir=specs_dir,
        spec_path=specs_dir / "spec.md",
        plan_path=specs_dir / "plan.md",
        history_path=specs_dir / _HISTORY_FILENAME,
    )
