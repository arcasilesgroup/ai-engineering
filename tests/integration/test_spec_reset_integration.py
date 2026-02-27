"""Integration tests for ai_engineering.maintenance.spec_reset.

Tests run_spec_reset() with real filesystem operations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.maintenance.spec_reset import (
    run_spec_reset,
)

pytestmark = pytest.mark.integration


def _create_project(tmp_path: Path) -> Path:
    """Create a project with .ai-engineering/context/specs/ structure."""
    specs_dir = tmp_path / ".ai-engineering" / "context" / "specs"
    archive_dir = specs_dir / "archive"
    archive_dir.mkdir(parents=True)
    return tmp_path


def _add_spec(
    project: Path,
    slug: str,
    *,
    done: bool = False,
    tasks_complete: bool = False,
):
    """Add a spec directory to the project."""
    specs_dir = project / ".ai-engineering" / "context" / "specs"
    spec_dir = specs_dir / slug
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(f"# Spec {slug}\n")
    (spec_dir / "plan.md").write_text(f"# Plan {slug}\n")

    if done:
        (spec_dir / "done.md").write_text("# Done\nCompleted.\n")

    total = 5
    completed = total if tasks_complete else 2
    (spec_dir / "tasks.md").write_text(
        f'---\nspec: "{slug}"\ntotal: {total}\ncompleted: {completed}\n---\n\n# Tasks\n'
    )


def _set_active(project: Path, slug: str | None):
    """Set _active.md to point to slug."""
    active_path = project / ".ai-engineering" / "context" / "specs" / "_active.md"
    if slug is None:
        content = '---\nactive: null\nupdated: "2026-01-01"\n---\n\n# No active spec.\n'
    else:
        content = f'---\nactive: "{slug}"\nupdated: "2026-01-01"\n---\n\n# Active: {slug}\n'
    active_path.write_text(content)


class TestRunSpecResetIntegration:
    """Integration tests for run_spec_reset()."""

    def test_archives_completed_spec_with_done_md(self, tmp_path):
        """Spec with done.md is archived."""
        project = _create_project(tmp_path)
        _add_spec(project, "001-done", done=True)
        _add_spec(project, "002-wip")
        _set_active(project, "001-done")

        result = run_spec_reset(project)

        assert result.success
        assert "001-done" in result.archived_specs
        assert "002-wip" not in result.archived_specs
        assert result.active_spec_cleared is True
        assert result.active_spec_was == "001-done"

        # Verify filesystem
        specs_dir = project / ".ai-engineering" / "context" / "specs"
        assert (specs_dir / "archive" / "001-done" / "spec.md").exists()
        assert not (specs_dir / "001-done").exists()
        assert (specs_dir / "002-wip" / "spec.md").exists()

    def test_archives_completed_spec_with_tasks(self, tmp_path):
        """Spec with tasks completed==total is archived."""
        project = _create_project(tmp_path)
        _add_spec(project, "003-tasks-done", tasks_complete=True)
        _set_active(project, "003-tasks-done")

        result = run_spec_reset(project)

        assert "003-tasks-done" in result.archived_specs
        assert result.active_spec_cleared is True

    def test_does_not_archive_in_progress(self, tmp_path):
        """In-progress spec is not archived."""
        project = _create_project(tmp_path)
        _add_spec(project, "004-wip")
        _set_active(project, "004-wip")

        result = run_spec_reset(project)

        assert result.archived_specs == []
        assert result.active_spec_cleared is False

    def test_resets_active_md(self, tmp_path):
        """_active.md is reset after archiving."""
        project = _create_project(tmp_path)
        _add_spec(project, "005-done", done=True)
        _set_active(project, "005-done")

        run_spec_reset(project)

        active_content = (
            project / ".ai-engineering" / "context" / "specs" / "_active.md"
        ).read_text()
        assert "active: null" in active_content
        assert "No active spec" in active_content

    def test_dry_run_does_not_modify(self, tmp_path):
        """Dry run reports but does not modify files."""
        project = _create_project(tmp_path)
        _add_spec(project, "006-done", done=True)
        _set_active(project, "006-done")

        result = run_spec_reset(project, dry_run=True)

        assert "006-done" in result.orphan_specs
        assert result.archived_specs == []
        assert result.active_spec_cleared is False

        # Spec still exists in place
        specs_dir = project / ".ai-engineering" / "context" / "specs"
        assert (specs_dir / "006-done" / "spec.md").exists()

    def test_multiple_orphans_archived(self, tmp_path):
        """Multiple completed specs are all archived."""
        project = _create_project(tmp_path)
        _add_spec(project, "007-done-a", done=True)
        _add_spec(project, "008-done-b", tasks_complete=True)
        _add_spec(project, "009-wip")
        _set_active(project, "007-done-a")

        result = run_spec_reset(project)

        assert "007-done-a" in result.archived_specs
        assert "008-done-b" in result.archived_specs
        assert "009-wip" not in result.archived_specs
        assert len(result.archived_specs) == 2

    def test_null_active_no_orphans(self, tmp_path):
        """Null active with no completed specs is a no-op."""
        project = _create_project(tmp_path)
        _add_spec(project, "010-wip")
        _set_active(project, None)

        result = run_spec_reset(project)

        assert result.archived_specs == []
        assert result.active_spec_cleared is False
        assert result.active_spec_was is None

    def test_missing_specs_dir(self, tmp_path):
        """Missing specs directory returns error."""
        result = run_spec_reset(tmp_path)
        assert not result.success
        assert len(result.errors) > 0

    def test_markdown_output(self, tmp_path):
        """to_markdown renders after a real reset."""
        project = _create_project(tmp_path)
        _add_spec(project, "011-done", done=True)
        _set_active(project, "011-done")

        result = run_spec_reset(project)
        md = result.to_markdown()

        assert "## Spec Reset Summary" in md
        assert "`011-done`" in md
