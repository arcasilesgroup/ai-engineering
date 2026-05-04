from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from ai_engineering.state.models import (
    FrameworkEvent,
    TaskLedger,
    TaskLedgerTask,
    TaskLifecycleState,
)
from ai_engineering.state.work_plane import (
    active_work_plane_pointer_path,
    read_task_ledger,
    resolve_active_work_plane,
    write_active_work_plane_pointer,
    write_task_ledger,
)


def test_resolve_active_work_plane_uses_legacy_singleton_buffer_paths(tmp_path: Path) -> None:
    work_plane = resolve_active_work_plane(tmp_path)

    assert work_plane.project_root == tmp_path
    assert work_plane.ai_eng_dir == tmp_path / ".ai-engineering"
    assert work_plane.specs_dir == tmp_path / ".ai-engineering" / "specs"
    assert work_plane.spec_path == tmp_path / ".ai-engineering" / "specs" / "spec.md"
    assert work_plane.plan_path == tmp_path / ".ai-engineering" / "specs" / "plan.md"
    assert work_plane.ledger_path == tmp_path / ".ai-engineering" / "specs" / "task-ledger.json"
    assert work_plane.current_summary_path == (
        tmp_path / ".ai-engineering" / "specs" / "current-summary.md"
    )
    assert work_plane.history_summary_path == (
        tmp_path / ".ai-engineering" / "specs" / "history-summary.md"
    )
    assert work_plane.handoffs_dir == tmp_path / ".ai-engineering" / "specs" / "handoffs"
    assert work_plane.evidence_dir == tmp_path / ".ai-engineering" / "specs" / "evidence"


def test_resolve_active_work_plane_prefers_pointer_specs_dir_when_present(tmp_path: Path) -> None:
    pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text(
        json.dumps({"specsDir": ".ai-engineering/specs/spec-117-hx-02"}),
        encoding="utf-8",
    )

    work_plane = resolve_active_work_plane(tmp_path)

    assert work_plane.specs_dir == tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
    assert (
        work_plane.spec_path
        == tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "spec.md"
    )
    assert (
        work_plane.plan_path
        == tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "plan.md"
    )
    assert work_plane.ledger_path == (
        tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "task-ledger.json"
    )
    assert work_plane.current_summary_path == (
        tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "current-summary.md"
    )
    assert work_plane.history_summary_path == (
        tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "history-summary.md"
    )
    assert work_plane.handoffs_dir == (
        tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "handoffs"
    )
    assert work_plane.evidence_dir == (
        tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "evidence"
    )


def test_resolve_active_work_plane_falls_back_when_pointer_is_invalid(tmp_path: Path) -> None:
    pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text("{not-json", encoding="utf-8")

    work_plane = resolve_active_work_plane(tmp_path)

    assert work_plane.specs_dir == tmp_path / ".ai-engineering" / "specs"
    assert work_plane.spec_path == tmp_path / ".ai-engineering" / "specs" / "spec.md"
    assert work_plane.plan_path == tmp_path / ".ai-engineering" / "specs" / "plan.md"
    assert work_plane.ledger_path == tmp_path / ".ai-engineering" / "specs" / "task-ledger.json"
    assert work_plane.current_summary_path == (
        tmp_path / ".ai-engineering" / "specs" / "current-summary.md"
    )
    assert work_plane.history_summary_path == (
        tmp_path / ".ai-engineering" / "specs" / "history-summary.md"
    )
    assert work_plane.handoffs_dir == tmp_path / ".ai-engineering" / "specs" / "handoffs"
    assert work_plane.evidence_dir == tmp_path / ".ai-engineering" / "specs" / "evidence"


def test_write_active_work_plane_pointer_records_project_relative_specs_dir(
    tmp_path: Path,
) -> None:
    specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"

    write_active_work_plane_pointer(tmp_path, specs_dir)

    pointer_path = active_work_plane_pointer_path(tmp_path)
    assert json.loads(pointer_path.read_text(encoding="utf-8")) == {
        "specsDir": ".ai-engineering/specs/spec-117-hx-02"
    }
    assert resolve_active_work_plane(tmp_path).specs_dir == specs_dir


def test_write_active_work_plane_pointer_clears_pointer_for_legacy_specs_dir(
    tmp_path: Path,
) -> None:
    pointer_path = active_work_plane_pointer_path(tmp_path)
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text(
        json.dumps({"specsDir": ".ai-engineering/specs/spec-117-hx-02"}),
        encoding="utf-8",
    )

    write_active_work_plane_pointer(tmp_path, tmp_path / ".ai-engineering" / "specs")

    assert not pointer_path.exists()
    assert resolve_active_work_plane(tmp_path).specs_dir == tmp_path / ".ai-engineering" / "specs"


def test_read_task_ledger_returns_none_when_missing_or_invalid(tmp_path: Path) -> None:
    assert read_task_ledger(tmp_path) is None

    ledger_path = resolve_active_work_plane(tmp_path).ledger_path
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("{not-json", encoding="utf-8")

    assert read_task_ledger(tmp_path) is None


def test_write_task_ledger_round_trips_at_active_work_plane_root(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
    write_active_work_plane_pointer(tmp_path, specs_dir)

    ledger = TaskLedger(
        tasks=[
            TaskLedgerTask(
                id="T-2.1",
                title="Define task ledger schema",
                ownerRole="orchestrator",
                writeScope=["src/ai_engineering/state/**"],
            )
        ]
    )

    ledger_path = write_task_ledger(tmp_path, ledger)
    reloaded = read_task_ledger(tmp_path)

    assert ledger_path == specs_dir / "task-ledger.json"
    assert reloaded is not None
    assert reloaded.model_dump(by_alias=True) == ledger.model_dump(by_alias=True)


def test_write_task_ledger_emits_task_trace_for_new_or_changed_tasks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
    write_active_work_plane_pointer(tmp_path, specs_dir)

    emitted: list[dict[str, object]] = []

    def _emit_task_trace(project_root: Path, **kwargs: object) -> FrameworkEvent:
        emitted.append({"project_root": project_root, **kwargs})
        return FrameworkEvent.model_validate(
            {
                "schemaVersion": "1.0",
                "timestamp": "2026-05-01T12:00:00Z",
                "project": project_root.name,
                "engine": "ai_engineering",
                "kind": "task_trace",
                "outcome": "success",
                "component": kwargs["component"],
                "correlationId": "corr-task-trace-1",
                "detail": {
                    "task_id": kwargs["task_id"],
                    "lifecycle_phase": kwargs["lifecycle_phase"],
                    "artifact_refs": kwargs["artifact_refs"],
                },
            }
        )

    def _build_task_trace_event(project_root, **kwargs):
        return _emit_task_trace(project_root, **kwargs)

    monkeypatch.setattr(
        "ai_engineering.state.observability.build_task_trace_event",
        _build_task_trace_event,
    )
    monkeypatch.setattr(
        "ai_engineering.state.observability.append_framework_events",
        lambda *_args, **_kwargs: None,
    )

    initial_ledger = TaskLedger(
        tasks=[
            TaskLedgerTask(
                id="HX-05-T-3.3",
                title="Emit task traces",
                status=TaskLifecycleState.PLANNED,
                ownerRole="Build",
                writeScope=["src/ai_engineering/state/**"],
                handoffs=[{"kind": "build-packet", "path": "handoffs/build.md"}],
                evidence=[{"kind": "verification-summary", "path": "evidence/verify.md"}],
            )
        ]
    )

    write_task_ledger(tmp_path, initial_ledger)

    assert len(emitted) == 1
    assert emitted[0]["project_root"] == tmp_path
    assert emitted[0]["task_id"] == "HX-05-T-3.3"
    assert emitted[0]["lifecycle_phase"] == "planned"
    assert emitted[0]["artifact_refs"] == ["handoffs/build.md", "evidence/verify.md"]

    emitted.clear()
    write_task_ledger(tmp_path, initial_ledger)
    assert emitted == []

    updated_ledger = TaskLedger(
        tasks=[
            TaskLedgerTask(
                id="HX-05-T-3.3",
                title="Emit task traces",
                status=TaskLifecycleState.IN_PROGRESS,
                ownerRole="Build",
                writeScope=["src/ai_engineering/state/**"],
                handoffs=[{"kind": "build-packet", "path": "handoffs/build.md"}],
                evidence=[
                    {"kind": "verification-summary", "path": "evidence/verify.md"},
                    {"kind": "verification-summary", "path": "evidence/verify-green.md"},
                ],
            )
        ]
    )

    write_task_ledger(tmp_path, updated_ledger)

    assert len(emitted) == 1
    assert emitted[0]["lifecycle_phase"] == "in-progress"
    assert emitted[0]["artifact_refs"] == [
        "handoffs/build.md",
        "evidence/verify.md",
        "evidence/verify-green.md",
    ]


def test_write_task_ledger_serializes_authoritative_mutation_with_framework_events_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, str]] = []

    @contextmanager
    def _lock_spy(project_root: Path, artifact_name: str):
        calls.append((project_root, artifact_name))
        yield project_root / ".ai-engineering" / "state" / "locks" / f"{artifact_name}.lock"

    monkeypatch.setattr("ai_engineering.state.work_plane.artifact_lock", _lock_spy)
    monkeypatch.setattr(
        "ai_engineering.state.observability.emit_task_trace",
        lambda *_args, **_kwargs: FrameworkEvent.model_validate(
            {
                "schemaVersion": "1.0",
                "timestamp": "2026-05-01T12:00:00Z",
                "project": "demo-project",
                "engine": "ai_engineering",
                "kind": "task_trace",
                "outcome": "success",
                "component": "state.task-ledger",
                "correlationId": "corr-task-lock-1",
                "detail": {
                    "task_id": "HX-05-T-4.2",
                    "lifecycle_phase": "planned",
                    "artifact_refs": [],
                },
            }
        ),
    )

    ledger = TaskLedger(
        tasks=[
            TaskLedgerTask(
                id="HX-05-T-4.2",
                title="Sequence task-trace writes",
                status=TaskLifecycleState.PLANNED,
                ownerRole="Build",
                writeScope=["src/**"],
            )
        ]
    )

    write_task_ledger(tmp_path, ledger)

    assert calls == [(tmp_path, "framework-events")]
