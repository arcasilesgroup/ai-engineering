"""Integration tests for ai_engineering.maintenance.spec_reset.

Tests run_spec_reset() with real filesystem operations using the
Working Buffer model: fixed files specs/spec.md, specs/plan.md,
specs/_history.md -- no numbered directories, no archive.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.maintenance.spec_reset import (
    SpecResetResult,
    run_spec_reset,
)

pytestmark = pytest.mark.integration


def _create_project(tmp_path: Path) -> Path:
    """Create a project with .ai-engineering/specs/ structure."""
    specs_dir = tmp_path / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True)
    return tmp_path


def _set_active_spec(
    project: Path,
    title: str,
    *,
    spec_id: str = "055",
) -> None:
    """Write an active spec into specs/spec.md with frontmatter."""
    spec_path = project / ".ai-engineering" / "specs" / "spec.md"
    content = f'---\nid: "{spec_id}"\n---\n\n# {title}\n\nSpec content.\n'
    spec_path.write_text(content, encoding="utf-8")


def _set_placeholder(project: Path) -> None:
    """Write placeholder (no active spec) to specs/spec.md."""
    spec_path = project / ".ai-engineering" / "specs" / "spec.md"
    spec_path.write_text(
        "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
        encoding="utf-8",
    )


class TestRunSpecResetIntegration:
    """Integration tests for run_spec_reset()."""

    def test_resets_active_spec(self, tmp_path: Path) -> None:
        """Active spec is cleared and history is updated."""
        project = _create_project(tmp_path)
        _set_active_spec(project, "Feature Alpha", spec_id="042")

        result = run_spec_reset(project)

        assert result.success
        assert result.spec_title == "Feature Alpha"
        assert result.history_updated is True
        assert result.files_cleared is True

        # spec.md now has placeholder
        spec_text = (project / ".ai-engineering" / "specs" / "spec.md").read_text()
        assert "No active spec" in spec_text

        # plan.md now has placeholder
        plan_text = (project / ".ai-engineering" / "specs" / "plan.md").read_text()
        assert "No active plan" in plan_text

    def test_creates_history_file_on_first_reset(self, tmp_path: Path) -> None:
        """_history.md is created with table header on first reset."""
        project = _create_project(tmp_path)
        _set_active_spec(project, "First Spec", spec_id="001")

        run_spec_reset(project)

        history_path = project / ".ai-engineering" / "specs" / "_history.md"
        assert history_path.exists()
        text = history_path.read_text()
        assert "# Spec History" in text
        assert "| 001 |" in text
        assert "First Spec" in text

    def test_appends_to_existing_history(self, tmp_path: Path) -> None:
        """Second reset appends to existing _history.md."""
        project = _create_project(tmp_path)

        # First reset
        _set_active_spec(project, "Spec One", spec_id="001")
        run_spec_reset(project)

        # Second reset
        _set_active_spec(project, "Spec Two", spec_id="002")
        run_spec_reset(project)

        history_text = (project / ".ai-engineering" / "specs" / "_history.md").read_text()
        assert "| 001 |" in history_text
        assert "| 002 |" in history_text

    def test_noop_when_no_active_spec(self, tmp_path: Path) -> None:
        """No-op when spec.md has placeholder content."""
        project = _create_project(tmp_path)
        _set_placeholder(project)

        result = run_spec_reset(project)

        assert result.success
        assert result.spec_title is None
        assert result.history_updated is False
        assert result.files_cleared is False

    def test_noop_when_spec_md_missing(self, tmp_path: Path) -> None:
        """No-op when specs/ exists but spec.md does not."""
        project = _create_project(tmp_path)

        result = run_spec_reset(project)

        assert result.success
        assert result.spec_title is None

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        """Dry run reports findings without modifying files."""
        project = _create_project(tmp_path)
        _set_active_spec(project, "Dry Run Spec", spec_id="099")

        result = run_spec_reset(project, dry_run=True)

        assert result.success
        assert result.spec_title == "Dry Run Spec"
        assert result.history_updated is False
        assert result.files_cleared is False

        # spec.md still has real content
        spec_text = (project / ".ai-engineering" / "specs" / "spec.md").read_text()
        assert "Dry Run Spec" in spec_text

    def test_missing_specs_dir(self, tmp_path: Path) -> None:
        """Missing specs directory returns error."""
        result = run_spec_reset(tmp_path)
        assert not result.success
        assert len(result.errors) > 0

    def test_result_is_spec_reset_result(self, tmp_path: Path) -> None:
        """run_spec_reset returns SpecResetResult dataclass."""
        project = _create_project(tmp_path)
        _set_active_spec(project, "Type Check")

        result = run_spec_reset(project)

        assert isinstance(result, SpecResetResult)

    def test_markdown_output(self, tmp_path: Path) -> None:
        """to_markdown renders after a real reset."""
        project = _create_project(tmp_path)
        _set_active_spec(project, "Markdown Test", spec_id="011")

        result = run_spec_reset(project)
        md = result.to_markdown()

        assert "## Spec Reset Summary" in md
        assert "`Markdown Test`" in md
        assert "History updated" in md

    def test_to_dict_output(self, tmp_path: Path) -> None:
        """to_dict serializes correctly after reset."""
        project = _create_project(tmp_path)
        _set_active_spec(project, "Dict Test", spec_id="012")

        result = run_spec_reset(project)
        data = result.to_dict()

        assert data["success"] is True
        assert data["spec_title"] == "Dict Test"
        assert data["history_updated"] is True
        assert data["files_cleared"] is True
