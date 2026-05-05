from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.work_plane import (
    active_work_plane_pointer_path,
    ensure_work_plane_artifacts,
    read_task_ledger,
    resolve_active_work_plane,
    task_ledger_has_open_tasks,
    write_active_work_plane_pointer,
)


def test_resolve_active_work_plane_uses_canonical_three_file_contract(tmp_path: Path) -> None:
    """Spec-123 collapsed specs/ to spec.md, plan.md, _history.md."""
    work_plane = resolve_active_work_plane(tmp_path)

    assert work_plane.project_root == tmp_path
    assert work_plane.ai_eng_dir == tmp_path / ".ai-engineering"
    assert work_plane.specs_dir == tmp_path / ".ai-engineering" / "specs"
    assert work_plane.spec_path == tmp_path / ".ai-engineering" / "specs" / "spec.md"
    assert work_plane.plan_path == tmp_path / ".ai-engineering" / "specs" / "plan.md"
    assert work_plane.history_path == tmp_path / ".ai-engineering" / "specs" / "_history.md"


def test_resolve_active_work_plane_dataclass_drops_dead_artifacts(tmp_path: Path) -> None:
    """Dead HX-02 fields must not be reachable from the resolver dataclass."""
    work_plane = resolve_active_work_plane(tmp_path)
    field_names = {field.name for field in work_plane.__dataclass_fields__.values()}

    assert field_names == {
        "project_root",
        "ai_eng_dir",
        "specs_dir",
        "spec_path",
        "plan_path",
        "history_path",
    }


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
    assert (
        work_plane.history_path
        == tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02" / "_history.md"
    )


def test_resolve_active_work_plane_falls_back_when_pointer_is_invalid(tmp_path: Path) -> None:
    pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text("{not-json", encoding="utf-8")

    work_plane = resolve_active_work_plane(tmp_path)

    assert work_plane.specs_dir == tmp_path / ".ai-engineering" / "specs"
    assert work_plane.spec_path == tmp_path / ".ai-engineering" / "specs" / "spec.md"
    assert work_plane.plan_path == tmp_path / ".ai-engineering" / "specs" / "plan.md"
    assert work_plane.history_path == tmp_path / ".ai-engineering" / "specs" / "_history.md"


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


def test_read_task_ledger_returns_none_post_spec_123(tmp_path: Path) -> None:
    """Spec-123 removed task ledger; shim always returns None."""
    assert read_task_ledger(tmp_path) is None


def test_task_ledger_has_open_tasks_returns_false_post_spec_123(tmp_path: Path) -> None:
    """Spec-123 removed task ledger; shim always returns False."""
    assert task_ledger_has_open_tasks(tmp_path) is False


def test_ensure_work_plane_artifacts_creates_canonical_three_files(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".ai-engineering" / "specs"

    ensure_work_plane_artifacts(specs_dir)

    assert (specs_dir / "spec.md").exists()
    assert (specs_dir / "plan.md").exists()
    assert (specs_dir / "_history.md").exists()
    # No dead artifacts created.
    assert not (specs_dir / "task-ledger.json").exists()
    assert not (specs_dir / "current-summary.md").exists()
    assert not (specs_dir / "history-summary.md").exists()
    assert not (specs_dir / "handoffs").exists()
    assert not (specs_dir / "evidence").exists()


def test_ensure_work_plane_artifacts_is_idempotent(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text("# Existing Spec\n", encoding="utf-8")

    ensure_work_plane_artifacts(specs_dir)

    # Existing content preserved.
    assert (specs_dir / "spec.md").read_text(encoding="utf-8") == "# Existing Spec\n"
    # Missing files created.
    assert (specs_dir / "plan.md").exists()
    assert (specs_dir / "_history.md").exists()
