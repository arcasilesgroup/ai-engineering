"""Unit tests for ai_engineering.maintenance.spec_reset (Working Buffer model).

Covers:
- check_active_spec: active with content, placeholder, missing file.
- append_history: creates file if missing, appends entry.
- clear_spec_buffer: writes placeholder content.
- SpecResetResult.to_markdown: rendering.
- run_spec_reset: full orchestration.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.maintenance.spec_reset import (
    SpecResetResult,
    append_history,
    check_active_spec,
    clear_spec_buffer,
    run_spec_reset,
)


def _create_spec_md(
    ai_eng_dir: Path,
    *,
    title: str = "Test Feature",
    spec_id: str = "055",
    placeholder: bool = False,
) -> None:
    """Helper to create specs/spec.md."""
    specs_dir = ai_eng_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    if placeholder:
        content = "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n"
    else:
        content = f'---\nid: "{spec_id}"\n---\n\n# {title}\n\nSpec content.\n'

    (specs_dir / "spec.md").write_text(content)


def _create_plan_md(ai_eng_dir: Path, *, placeholder: bool = False) -> None:
    """Helper to create specs/plan.md."""
    specs_dir = ai_eng_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    if placeholder:
        content = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"
    else:
        content = "---\ntotal: 5\ncompleted: 3\n---\n\n# Plan\n\n- [x] Task 1\n"

    (specs_dir / "plan.md").write_text(content)


class TestCheckActiveSpec:
    """Tests for check_active_spec()."""

    def test_active_spec_with_content(self, tmp_path: Path) -> None:
        """Active spec with real content returns title and ID."""
        ai_eng = tmp_path / ".ai-engineering"
        _create_spec_md(ai_eng, title="My Feature", spec_id="042")

        title, spec_id = check_active_spec(ai_eng)
        assert title == "My Feature"
        assert spec_id == "042"

    def test_placeholder_spec(self, tmp_path: Path) -> None:
        """Placeholder spec returns (None, None)."""
        ai_eng = tmp_path / ".ai-engineering"
        _create_spec_md(ai_eng, placeholder=True)

        title, spec_id = check_active_spec(ai_eng)
        assert title is None
        assert spec_id is None

    def test_missing_spec_file(self, tmp_path: Path) -> None:
        """Missing spec.md returns (None, None)."""
        ai_eng = tmp_path / ".ai-engineering"
        (ai_eng / "specs").mkdir(parents=True)

        title, spec_id = check_active_spec(ai_eng)
        assert title is None
        assert spec_id is None


class TestAppendHistory:
    """Tests for append_history()."""

    def test_creates_file_with_header(self, tmp_path: Path) -> None:
        """Creates _history.md with table header if it does not exist."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        result = append_history(specs_dir, "055", "Radical Simplification")
        assert result is True

        content = (specs_dir / "_history.md").read_text()
        assert "# Spec History" in content
        assert "| ID | Title | Date | Branch |" in content
        assert "| 055 | Radical Simplification |" in content

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        """Appends to existing _history.md without duplicating header."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()

        append_history(specs_dir, "054", "First Spec")
        append_history(specs_dir, "055", "Second Spec")

        content = (specs_dir / "_history.md").read_text()
        assert content.count("# Spec History") == 1
        assert "| 054 | First Spec |" in content
        assert "| 055 | Second Spec |" in content


class TestClearSpecBuffer:
    """Tests for clear_spec_buffer()."""

    def test_writes_placeholders(self, tmp_path: Path) -> None:
        """Clears spec.md and plan.md with placeholder content."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "spec.md").write_text("old spec content")
        (specs_dir / "plan.md").write_text("old plan content")

        clear_spec_buffer(specs_dir)

        assert "# No active spec" in (specs_dir / "spec.md").read_text()
        assert "# No active plan" in (specs_dir / "plan.md").read_text()


class TestRunSpecReset:
    """Tests for run_spec_reset() full orchestration."""

    def test_resets_active_spec(self, tmp_path: Path) -> None:
        """Active spec is recorded in history and buffer is cleared."""
        ai_eng = tmp_path / ".ai-engineering"
        _create_spec_md(ai_eng, title="Feature X", spec_id="055")
        _create_plan_md(ai_eng)

        result = run_spec_reset(tmp_path)

        assert result.success is True
        assert result.spec_title == "Feature X"
        assert result.history_updated is True
        assert result.files_cleared is True

        # Verify files cleared
        spec_content = (ai_eng / "specs" / "spec.md").read_text()
        assert spec_content.startswith("# No active spec")
        plan_content = (ai_eng / "specs" / "plan.md").read_text()
        assert plan_content.startswith("# No active plan")

        # Verify history written
        history = (ai_eng / "specs" / "_history.md").read_text()
        assert "| 055 | Feature X |" in history

    def test_noop_for_placeholder(self, tmp_path: Path) -> None:
        """No action taken when spec buffer has placeholder content."""
        ai_eng = tmp_path / ".ai-engineering"
        _create_spec_md(ai_eng, placeholder=True)
        _create_plan_md(ai_eng, placeholder=True)

        result = run_spec_reset(tmp_path)

        assert result.success is True
        assert result.spec_title is None
        assert result.history_updated is False
        assert result.files_cleared is False

    def test_dry_run(self, tmp_path: Path) -> None:
        """Dry run reports without modifying files."""
        ai_eng = tmp_path / ".ai-engineering"
        _create_spec_md(ai_eng, title="Feature Y", spec_id="056")
        _create_plan_md(ai_eng)

        result = run_spec_reset(tmp_path, dry_run=True)

        assert result.spec_title == "Feature Y"
        assert result.history_updated is False
        assert result.files_cleared is False

        # Files unchanged
        assert "Feature Y" in (ai_eng / "specs" / "spec.md").read_text()

    def test_missing_specs_dir(self, tmp_path: Path) -> None:
        """Missing specs directory reports error."""
        result = run_spec_reset(tmp_path)
        assert not result.success
        assert "Specs directory not found" in result.errors[0]


class TestSpecResetResultMarkdown:
    """Tests for SpecResetResult.to_markdown()."""

    def test_empty_result(self) -> None:
        """Empty result renders without errors."""
        result = SpecResetResult()
        md = result.to_markdown()
        assert "## Spec Reset Summary" in md
        assert "none (no active spec)" in md

    def test_with_cleared_spec(self) -> None:
        """Cleared spec is shown."""
        result = SpecResetResult(
            spec_title="Feature Z",
            history_updated=True,
            files_cleared=True,
        )
        md = result.to_markdown()
        assert "`Feature Z`" in md
        assert "History updated**: yes" in md
        assert "Files cleared**: yes" in md

    def test_success_property(self) -> None:
        """success is True when no errors."""
        result = SpecResetResult()
        assert result.success is True

        result.errors.append("Something failed")
        assert result.success is False
