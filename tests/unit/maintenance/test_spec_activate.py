"""Unit tests for ai_engineering.maintenance.spec_activate."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.maintenance.spec_activate import run_spec_activate
from ai_engineering.state.work_plane import (
    active_work_plane_pointer_path,
    read_task_ledger,
    resolve_active_work_plane,
)


class TestRunSpecActivate:
    """Tests for run_spec_activate()."""

    def test_creates_pointer_and_missing_placeholders(self, tmp_path: Path) -> None:
        result = run_spec_activate(tmp_path, Path(".ai-engineering/specs/spec-117-hx-02"))

        specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
        assert result.success is True
        assert result.pointer_enabled is True
        assert result.spec_created is True
        assert result.plan_created is True
        assert active_work_plane_pointer_path(tmp_path).exists() is True
        assert resolve_active_work_plane(tmp_path).specs_dir == specs_dir
        assert (specs_dir / "spec.md").read_text(encoding="utf-8").startswith("# No active spec")
        assert (specs_dir / "plan.md").read_text(encoding="utf-8").startswith("# No active plan")
        assert read_task_ledger(tmp_path) is not None
        assert read_task_ledger(tmp_path).tasks == []
        assert (specs_dir / "current-summary.md").exists() is True
        assert (specs_dir / "history-summary.md").exists() is True
        assert (specs_dir / "handoffs").is_dir() is True
        assert (specs_dir / "evidence").is_dir() is True

    def test_preserves_existing_spec_and_plan_content(self, tmp_path: Path) -> None:
        specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            '---\nid: "117-02"\n---\n\n# Existing Spec\n',
            encoding="utf-8",
        )
        (specs_dir / "plan.md").write_text(
            "---\ntotal: 1\ncompleted: 0\n---\n\n- [ ] Task\n",
            encoding="utf-8",
        )

        result = run_spec_activate(tmp_path, specs_dir)

        assert result.success is True
        assert result.spec_created is False
        assert result.plan_created is False
        assert "Existing Spec" in (specs_dir / "spec.md").read_text(encoding="utf-8")
        assert "- [ ] Task" in (specs_dir / "plan.md").read_text(encoding="utf-8")

    def test_legacy_specs_dir_clears_pointer(self, tmp_path: Path) -> None:
        active_work_plane_pointer_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
        active_work_plane_pointer_path(tmp_path).write_text(
            '{"specsDir": ".ai-engineering/specs/spec-117-hx-02"}',
            encoding="utf-8",
        )

        result = run_spec_activate(tmp_path, Path(".ai-engineering/specs"))

        assert result.success is True
        assert result.pointer_enabled is False
        assert active_work_plane_pointer_path(tmp_path).exists() is False
        assert (
            resolve_active_work_plane(tmp_path).specs_dir == tmp_path / ".ai-engineering" / "specs"
        )

    def test_rejects_specs_dir_outside_project_root(self, tmp_path: Path) -> None:
        outside_dir = tmp_path.parent / "outside-specs"

        result = run_spec_activate(tmp_path, outside_dir)

        assert result.success is False
        assert result.errors == ["Specs directory must stay inside the project root"]
