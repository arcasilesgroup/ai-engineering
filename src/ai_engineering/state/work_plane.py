"""Active work-plane path resolution.

HX-02 starts with a compatibility-backed resolver so runtime consumers can stop
hard-coding ``spec.md`` and ``plan.md`` paths before the task-ledger schema
lands. Today the resolver still points at the singleton working buffer; later
phases can swap in a spec-scoped work plane behind the same contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.locking import artifact_lock
from ai_engineering.state.models import TaskLedger, TaskLedgerTask

ACTIVE_WORK_PLANE_POINTER_REL = Path(".ai-engineering") / "specs" / "active-work-plane.json"
_LEGACY_SPECS_DIR_REL = ACTIVE_WORK_PLANE_POINTER_REL.parent
_TASK_LEDGER_FILENAME = "task-ledger.json"
_CURRENT_SUMMARY_FILENAME = "current-summary.md"
_HISTORY_SUMMARY_FILENAME = "history-summary.md"
_HANDOFFS_DIRNAME = "handoffs"
_EVIDENCE_DIRNAME = "evidence"
_CURRENT_SUMMARY_PLACEHOLDER = "# Current Summary\n\nNo active current summary yet.\n"
_HISTORY_SUMMARY_PLACEHOLDER = "# History Summary\n\nNo history summary yet.\n"
_NO_ACTIVE_SPEC_PREFIX = "# No active spec"


@dataclass(frozen=True)
class ActiveWorkPlane:
    """Resolved paths for the currently active work plane."""

    project_root: Path
    ai_eng_dir: Path
    specs_dir: Path
    spec_path: Path
    plan_path: Path
    ledger_path: Path
    current_summary_path: Path
    history_summary_path: Path
    handoffs_dir: Path
    evidence_dir: Path


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
    """Ensure the non-compatibility work-plane artifacts exist.

    This initializes the task-ledger and artifact-class surfaces without
    overwriting any existing content.
    """
    specs_dir.mkdir(parents=True, exist_ok=True)

    ledger_path = specs_dir / _TASK_LEDGER_FILENAME
    if not ledger_path.exists():
        write_json_model(ledger_path, TaskLedger())

    _ensure_text_artifact(specs_dir / _CURRENT_SUMMARY_FILENAME, _CURRENT_SUMMARY_PLACEHOLDER)
    _ensure_text_artifact(specs_dir / _HISTORY_SUMMARY_FILENAME, _HISTORY_SUMMARY_PLACEHOLDER)
    (specs_dir / _HANDOFFS_DIRNAME).mkdir(parents=True, exist_ok=True)
    (specs_dir / _EVIDENCE_DIRNAME).mkdir(parents=True, exist_ok=True)


def read_task_ledger(project_root: Path) -> TaskLedger | None:
    """Read the task ledger for the active work plane when it is valid."""
    ledger_path = resolve_active_work_plane(project_root).ledger_path
    if not ledger_path.exists():
        return None

    try:
        return read_json_model(ledger_path, TaskLedger)
    except (OSError, ValueError):
        return None


def task_ledger_has_open_tasks(project_root: Path) -> bool:
    """Return True when the active task ledger has at least one non-done task."""
    ledger = read_task_ledger(project_root)
    if ledger is None:
        return False
    return any(task.status.value != "done" for task in ledger.tasks)


def active_work_plane_placeholder_fallback_id(project_root: Path) -> str | None:
    """Return the work-plane directory id when placeholder prose still has open tasks."""
    if not task_ledger_has_open_tasks(project_root):
        return None
    fallback_id = resolve_active_work_plane(project_root).specs_dir.name.strip()
    return fallback_id or None


def active_work_plane_has_active_spec(project_root: Path) -> bool:
    """Return True when spec.md or the open task ledger indicates active work."""
    spec_path = resolve_active_work_plane(project_root).spec_path
    if not spec_path.exists():
        return False
    try:
        text = spec_path.read_text(encoding="utf-8").lstrip()
    except OSError:
        return False
    if not text.startswith(_NO_ACTIVE_SPEC_PREFIX):
        return True
    return task_ledger_has_open_tasks(project_root)


def write_task_ledger(project_root: Path, ledger: TaskLedger) -> Path:
    """Persist the task ledger at the active work-plane root."""
    from ai_engineering.state.observability import (
        append_framework_events,
        build_task_trace_event,
    )

    with artifact_lock(project_root, "framework-events"):
        previous_ledger = read_task_ledger(project_root)
        ledger_path = resolve_active_work_plane(project_root).ledger_path
        write_json_model(ledger_path, ledger)

        previous_tasks = (
            {task.id: _task_trace_signature(task) for task in previous_ledger.tasks}
            if previous_ledger is not None
            else {}
        )

        trace_events = []
        for task in ledger.tasks:
            signature = _task_trace_signature(task)
            if previous_tasks.get(task.id) == signature:
                continue
            trace_events.append(
                build_task_trace_event(
                    project_root,
                    task_id=task.id,
                    lifecycle_phase=task.status.value,
                    component="state.task-ledger",
                    source="work-plane",
                    artifact_refs=_task_artifact_refs(task),
                )
            )

        append_framework_events(
            project_root,
            trace_events,
            lock_acquired=True,
        )

    return ledger_path


def _task_artifact_refs(task: TaskLedgerTask) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()

    for ref in (*task.handoffs, *task.evidence):
        path = ref.path.strip()
        if not path or path in seen:
            continue
        seen.add(path)
        refs.append(path)

    return refs


def _task_trace_signature(task: TaskLedgerTask) -> tuple[str, tuple[str, ...]]:
    return (task.status.value, tuple(_task_artifact_refs(task)))


def _ensure_text_artifact(path: Path, content: str) -> None:
    """Write a placeholder artifact only when the file is missing."""
    if not path.exists():
        path.write_text(content, encoding="utf-8")


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
    """Resolve the active work plane using the legacy singleton buffer layout.

    The compatibility contract keeps current consumers stable while HX-02
    introduces a first-class task ledger and spec-scoped artifact topology.
    When an authoritative pointer exists, prefer the pointed specs dir while
    preserving the same ``spec.md``/``plan.md`` compatibility view contract.
    """
    ai_eng_dir = project_root / ".ai-engineering"
    specs_dir = _pointer_specs_dir(project_root) or (ai_eng_dir / "specs")
    return ActiveWorkPlane(
        project_root=project_root,
        ai_eng_dir=ai_eng_dir,
        specs_dir=specs_dir,
        spec_path=specs_dir / "spec.md",
        plan_path=specs_dir / "plan.md",
        ledger_path=specs_dir / _TASK_LEDGER_FILENAME,
        current_summary_path=specs_dir / _CURRENT_SUMMARY_FILENAME,
        history_summary_path=specs_dir / _HISTORY_SUMMARY_FILENAME,
        handoffs_dir=specs_dir / _HANDOFFS_DIRNAME,
        evidence_dir=specs_dir / _EVIDENCE_DIRNAME,
    )
