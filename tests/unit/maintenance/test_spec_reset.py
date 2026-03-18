"""Unit tests for ai_engineering.maintenance.spec_reset.

Covers:
- check_active_spec: active with done.md, active without, null active.
- find_completed_specs: mixed completed/in-progress specs.
- archive_spec: successful move, already archived.
- reset_active_md: writes correct frontmatter.
- SpecResetResult.to_markdown: rendering.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.maintenance.spec_reset import (
    SpecResetResult,
    archive_spec,
    check_active_spec,
    find_completed_specs,
    reset_active_md,
)

pytestmark = pytest.mark.unit


def _create_spec_dir(
    specs_dir: Path, slug: str, *, done: bool = False, tasks_complete: bool = False
):
    """Helper to create a spec directory with optional done.md and tasks.md."""
    spec_dir = specs_dir / slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text(f"# Spec {slug}\n")

    if done:
        (spec_dir / "done.md").write_text("# Done\n")

    if tasks_complete:
        (spec_dir / "tasks.md").write_text(
            '---\nspec: "001"\ntotal: 5\ncompleted: 5\n---\n\n# Tasks\n'
        )
    else:
        (spec_dir / "tasks.md").write_text(
            '---\nspec: "001"\ntotal: 5\ncompleted: 2\n---\n\n# Tasks\n'
        )

    return spec_dir


def _create_active_md(specs_dir: Path, slug: str | None):
    """Helper to create _active.md with given slug."""
    if slug is None:
        content = (
            '---\nactive: null\nupdated: "2026-01-01"\n---\n\n# Active Spec\n\nNo active spec.\n'
        )
    else:
        content = f'---\nactive: "{slug}"\nupdated: "2026-01-01"\n---\n\n# Active Spec\n\n{slug}\n'
    (specs_dir / "_active.md").write_text(content)


class TestCheckActiveSpec:
    """Tests for check_active_spec()."""

    def test_active_with_done_md(self, tmp_path):
        """Active spec with done.md is detected as completed."""
        ai_eng = tmp_path / ".ai-engineering"
        specs_dir = ai_eng / "context" / "specs"
        specs_dir.mkdir(parents=True)

        _create_spec_dir(specs_dir, "001-feature", done=True)
        _create_active_md(specs_dir, "001-feature")

        slug, completed = check_active_spec(ai_eng)
        assert slug == "001-feature"
        assert completed is True

    def test_active_with_complete_tasks_but_no_done(self, tmp_path):
        """Active spec with completed==total but no done.md is NOT completed.

        done.md is mandatory for closure; completed==total is necessary but
        not sufficient.
        """
        ai_eng = tmp_path / ".ai-engineering"
        specs_dir = ai_eng / "context" / "specs"
        specs_dir.mkdir(parents=True)

        _create_spec_dir(specs_dir, "002-refactor", tasks_complete=True)
        _create_active_md(specs_dir, "002-refactor")

        slug, completed = check_active_spec(ai_eng)
        assert slug == "002-refactor"
        assert completed is False

    def test_active_in_progress(self, tmp_path):
        """Active spec without done.md and incomplete tasks is not completed."""
        ai_eng = tmp_path / ".ai-engineering"
        specs_dir = ai_eng / "context" / "specs"
        specs_dir.mkdir(parents=True)

        _create_spec_dir(specs_dir, "003-wip")
        _create_active_md(specs_dir, "003-wip")

        slug, completed = check_active_spec(ai_eng)
        assert slug == "003-wip"
        assert completed is False

    def test_null_active(self, tmp_path):
        """Null active returns (None, False)."""
        ai_eng = tmp_path / ".ai-engineering"
        specs_dir = ai_eng / "context" / "specs"
        specs_dir.mkdir(parents=True)

        _create_active_md(specs_dir, None)

        slug, completed = check_active_spec(ai_eng)
        assert slug is None
        assert completed is False

    def test_missing_active_file(self, tmp_path):
        """Missing _active.md returns (None, False)."""
        ai_eng = tmp_path / ".ai-engineering"
        (ai_eng / "context" / "specs").mkdir(parents=True)

        slug, completed = check_active_spec(ai_eng)
        assert slug is None
        assert completed is False

    def test_missing_spec_dir(self, tmp_path):
        """Active pointing to non-existent dir returns (slug, False)."""
        ai_eng = tmp_path / ".ai-engineering"
        specs_dir = ai_eng / "context" / "specs"
        specs_dir.mkdir(parents=True)

        _create_active_md(specs_dir, "999-nonexistent")

        slug, completed = check_active_spec(ai_eng)
        assert slug == "999-nonexistent"
        assert completed is False


class TestFindCompletedSpecs:
    """Tests for find_completed_specs()."""

    def test_finds_specs_with_done_md(self, tmp_path):
        """Specs with done.md are found."""
        specs_dir = tmp_path / "specs"
        _create_spec_dir(specs_dir, "001-done", done=True)
        _create_spec_dir(specs_dir, "002-wip")

        completed = find_completed_specs(specs_dir)
        assert "001-done" in completed
        assert "002-wip" not in completed

    def test_does_not_find_complete_tasks_without_done(self, tmp_path):
        """Specs with completed==total but no done.md are NOT found."""
        specs_dir = tmp_path / "specs"
        _create_spec_dir(specs_dir, "003-tasks-done", tasks_complete=True)
        _create_spec_dir(specs_dir, "004-tasks-wip")

        completed = find_completed_specs(specs_dir)
        assert "003-tasks-done" not in completed
        assert "004-tasks-wip" not in completed

    def test_ignores_archive_dir(self, tmp_path):
        """Specs inside archive/ are not returned."""
        specs_dir = tmp_path / "specs"
        archive = specs_dir / "archive"
        _create_spec_dir(archive, "old-done", done=True)
        _create_spec_dir(specs_dir, "005-done", done=True)

        completed = find_completed_specs(specs_dir)
        assert "005-done" in completed
        assert "old-done" not in completed

    def test_empty_directory(self, tmp_path):
        """Empty specs directory returns empty list."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        completed = find_completed_specs(specs_dir)
        assert completed == []


class TestArchiveSpec:
    """Tests for archive_spec()."""

    def test_successful_archive(self, tmp_path):
        """Spec is moved to archive/."""
        specs_dir = tmp_path / "specs"
        _create_spec_dir(specs_dir, "001-done", done=True)

        result = archive_spec(specs_dir, "001-done")
        assert result is True
        assert (specs_dir / "archive" / "001-done" / "spec.md").exists()
        assert not (specs_dir / "001-done").exists()

    def test_already_archived(self, tmp_path):
        """Attempting to archive an already-archived spec returns False."""
        specs_dir = tmp_path / "specs"
        _create_spec_dir(specs_dir, "001-done", done=True)
        archive_spec(specs_dir, "001-done")

        # Create another with same name
        _create_spec_dir(specs_dir, "001-done", done=True)
        result = archive_spec(specs_dir, "001-done")
        assert result is False

    def test_nonexistent_spec(self, tmp_path):
        """Non-existent spec returns False."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        result = archive_spec(specs_dir, "nonexistent")
        assert result is False


class TestResetActiveMd:
    """Tests for reset_active_md()."""

    def test_writes_null_active(self, tmp_path):
        """reset_active_md writes correct frontmatter."""
        active_path = tmp_path / "_active.md"
        active_path.write_text("old content")

        reset_active_md(active_path)

        content = active_path.read_text()
        assert "active: null" in content
        assert "No active spec" in content
        assert "/create-spec" in content

    def test_creates_file_if_missing(self, tmp_path):
        """reset_active_md creates the file if it doesn't exist."""
        active_path = tmp_path / "_active.md"

        reset_active_md(active_path)

        assert active_path.exists()
        assert "active: null" in active_path.read_text()


class TestSpecResetResultMarkdown:
    """Tests for SpecResetResult.to_markdown()."""

    def test_empty_result(self):
        """Empty result renders without errors."""
        result = SpecResetResult()
        md = result.to_markdown()
        assert "## Spec Reset Summary" in md
        assert "Previous active spec**: none" in md

    def test_with_archived_specs(self):
        """Archived specs are listed."""
        result = SpecResetResult(
            active_spec_was="001-done",
            active_spec_cleared=True,
            archived_specs=["001-done"],
        )
        md = result.to_markdown()
        assert "### Archived" in md
        assert "`001-done`" in md
        assert "Active spec cleared**: yes" in md

    def test_with_orphans(self):
        """Orphan specs are listed."""
        result = SpecResetResult(
            orphan_specs=["002-orphan"],
        )
        md = result.to_markdown()
        assert "### Orphans" in md
        assert "`002-orphan`" in md

    def test_success_property(self):
        """success is True when no errors."""
        result = SpecResetResult()
        assert result.success is True

        result.errors.append("Something failed")
        assert result.success is False
