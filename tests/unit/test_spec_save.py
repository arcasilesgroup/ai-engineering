"""Unit tests for ai-eng spec save command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands.spec_save import (
    _build_plan_md,
    _build_spec_md,
    _build_tasks_md,
    _extract_section,
    _extract_title,
    _next_spec_number,
    _project_root,
    _slugify,
    _specs_dir,
    _update_active_md,
    _validate_spec_content,
    spec_save,
)

runner = CliRunner()


class TestExtractSection:
    def test_extracts_problem(self):
        text = "## Problem\nSomething is broken.\n## Solution\nFix it."
        assert _extract_section(text, "Problem") == "Something is broken."

    def test_extracts_solution(self):
        text = "## Problem\nBroken.\n## Solution\nFix it.\n## Scope\nAll."
        assert _extract_section(text, "Solution") == "Fix it."

    def test_returns_empty_for_missing(self):
        text = "## Problem\nBroken."
        assert _extract_section(text, "Solution") == ""

    def test_extracts_multiline(self):
        text = "## Problem\nLine 1.\nLine 2.\n\nLine 3.\n## Solution\nFix."
        result = _extract_section(text, "Problem")
        assert "Line 1." in result
        assert "Line 3." in result


class TestExtractTitle:
    def test_extracts_h1(self):
        assert _extract_title("# My Feature\n## Problem") == "My Feature"

    def test_returns_empty_without_h1(self):
        assert _extract_title("## Problem\nStuff") == ""


class TestSlugify:
    def test_basic(self):
        assert _slugify("OAuth Authentication") == "oauth-authentication"

    def test_special_chars(self):
        assert _slugify("Add OAuth 2.0!") == "add-oauth-20"

    def test_truncates(self):
        long = "a very long title that exceeds the maximum slug length allowed"
        assert len(_slugify(long)) <= 40


class TestValidateSpecContent:
    def test_valid(self):
        text = "## Problem\nBroken.\n## Solution\nFix it."
        assert _validate_spec_content(text) == []

    def test_missing_problem(self):
        text = "## Solution\nFix it."
        errors = _validate_spec_content(text)
        assert len(errors) == 1
        assert "Problem" in errors[0]

    def test_missing_both(self):
        text = "## Scope\nAll."
        errors = _validate_spec_content(text)
        assert len(errors) == 2


class TestNextSpecNumber:
    def test_empty_dir(self, tmp_path: Path):
        specs = tmp_path / "specs"
        specs.mkdir()
        assert _next_spec_number(specs) == 1

    def test_existing_specs(self, tmp_path: Path):
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "035-something").mkdir()
        (specs / "036-other").mkdir()
        assert _next_spec_number(specs) == 37

    def test_with_archive(self, tmp_path: Path):
        specs = tmp_path / "specs"
        specs.mkdir()
        archive = specs / "archive"
        archive.mkdir()
        (archive / "030-old").mkdir()
        (specs / "036-current").mkdir()
        assert _next_spec_number(specs) == 37

    def test_nonexistent_dir(self, tmp_path: Path):
        specs = tmp_path / "nonexistent"
        assert _next_spec_number(specs) == 1


class TestBuildSpecMd:
    def test_contains_frontmatter(self):
        result = _build_spec_md(
            37,
            "oauth",
            "OAuth Auth",
            "## Problem\nBroken.\n## Solution\nFix.",
            "standard",
            "M",
            ["auth"],
            "feat/037-oauth",
        )
        assert 'id: "037"' in result
        assert 'slug: "oauth"' in result
        assert 'status: "in-progress"' in result
        assert "# Spec 037 — OAuth Auth" in result
        assert "Broken." in result
        assert "Fix." in result


class TestBuildTasksMd:
    def test_extracts_tasks(self):
        content = "## Tasks\n- [ ] 1.1 Do thing\n- [ ] 1.2 Do other"
        result = _build_tasks_md(37, "Test", content)
        assert "total: 2" in result
        assert "completed: 0" in result
        assert "- [ ] 1.1 Do thing" in result

    def test_fallback_to_todo(self):
        content = "## Problem\nStuff\n## Solution\nFix"
        result = _build_tasks_md(37, "Test", content)
        assert "total: 1" in result

    def test_finds_checkboxes_outside_tasks_section(self):
        content = "## Problem\nBroken.\n## Solution\nFix.\n- [ ] 1.1 Do A\n- [x] 1.2 Do B"
        result = _build_tasks_md(37, "Test", content)
        assert "total: 2" in result
        assert "completed: 1" in result


class TestBuildPlanMd:
    def test_contains_frontmatter(self):
        content = "## Architecture\nMicroservices.\n## Session Map\nPhase 1: Setup."
        result = _build_plan_md(37, "OAuth Auth", content)
        assert 'spec: "037"' in result
        assert "# Plan — OAuth Auth" in result
        assert "Microservices." in result
        assert "Phase 1: Setup." in result

    def test_missing_sections_use_todo(self):
        content = "## Problem\nBroken.\n## Solution\nFix."
        result = _build_plan_md(37, "Test", content)
        assert "TODO" in result
        assert "# Plan — Test" in result

    def test_patterns_section(self):
        content = "## Patterns\nRepository pattern.\n## Other\nStuff."
        result = _build_plan_md(37, "Test", content)
        assert "Repository pattern." in result


class TestUpdateActiveMd:
    def test_writes_active_file(self, tmp_path: Path):
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        _update_active_md(specs_dir, 37, "oauth", "OAuth Auth", "feat/037-oauth")
        active = (specs_dir / "_active.md").read_text(encoding="utf-8")
        assert 'active: "037-oauth"' in active
        assert "Spec 037" in active
        assert "feat/037-oauth" in active


class TestProjectRoot:
    def test_finds_root_with_ai_engineering_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir()
        with patch("ai_engineering.cli_commands.spec_save.Path.cwd", return_value=tmp_path):
            assert _project_root() == tmp_path

    def test_falls_back_to_cwd(self, tmp_path: Path) -> None:
        with patch("ai_engineering.cli_commands.spec_save.Path.cwd", return_value=tmp_path):
            assert _project_root() == tmp_path


class TestSpecsDir:
    def test_returns_correct_path(self, tmp_path: Path) -> None:
        result = _specs_dir(tmp_path)
        assert result == tmp_path / ".ai-engineering" / "context" / "specs"


class TestSpecSaveCommand:
    """Integration tests for the spec_save typer command."""

    @pytest.fixture()
    def project(self, tmp_path: Path) -> Path:
        """Set up a minimal project structure."""
        ai_dir = tmp_path / ".ai-engineering" / "context" / "specs"
        ai_dir.mkdir(parents=True)
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        return tmp_path

    def _make_app(self):
        import typer

        app = typer.Typer()
        app.command()(spec_save)
        return app

    def test_save_from_file(self, project: Path) -> None:
        spec_file = project / "draft.md"
        spec_file.write_text(
            "# OAuth Feature\n\n## Problem\nNo auth.\n\n## Solution\nAdd OAuth.\n\n"
            "## Tasks\n- [ ] 1.1 Configure\n- [ ] 1.2 Test\n",
            encoding="utf-8",
        )
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(
                app,
                ["--file", str(spec_file), "--no-commit", "--no-branch"],
            )
        assert result.exit_code == 0, result.output
        assert "001-oauth-feature" in result.output
        spec_dir = project / ".ai-engineering" / "context" / "specs" / "001-oauth-feature"
        assert (spec_dir / "spec.md").exists()
        assert (spec_dir / "plan.md").exists()
        assert (spec_dir / "tasks.md").exists()

    def test_save_from_stdin(self, project: Path) -> None:
        content = "# Stdin Spec\n\n## Problem\nBroken.\n\n## Solution\nFix it.\n"
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(
                app,
                ["--no-commit", "--no-branch"],
                input=content,
            )
        assert result.exit_code == 0, result.output
        assert "001-stdin-spec" in result.output

    def test_save_with_explicit_title(self, project: Path) -> None:
        content = "## Problem\nBroken.\n\n## Solution\nFix it.\n"
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(
                app,
                ["--title", "Custom Title", "--no-commit", "--no-branch"],
                input=content,
            )
        assert result.exit_code == 0, result.output
        assert "001-custom-title" in result.output

    def test_save_with_tags(self, project: Path) -> None:
        content = "# Tagged\n\n## Problem\nX.\n\n## Solution\nY.\n"
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(
                app,
                ["--tags", "auth,security", "--no-commit", "--no-branch"],
                input=content,
            )
        assert result.exit_code == 0, result.output
        spec_dir = project / ".ai-engineering" / "context" / "specs" / "001-tagged"
        spec_content = (spec_dir / "spec.md").read_text(encoding="utf-8")
        assert '"auth"' in spec_content
        assert '"security"' in spec_content

    def test_error_missing_file(self) -> None:
        app = self._make_app()
        result = runner.invoke(app, ["--file", "/nonexistent/spec.md", "--no-commit"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_error_empty_input(self, project: Path) -> None:
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(app, ["--no-commit", "--no-branch"], input="")
        assert result.exit_code == 1

    def test_error_missing_sections(self, project: Path) -> None:
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(app, ["--no-commit", "--no-branch"], input="## Scope\nAll.\n")
        assert result.exit_code == 1
        assert "Problem" in result.output

    def test_error_no_title(self, project: Path) -> None:
        content = "## Problem\nX.\n\n## Solution\nY.\n"
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(app, ["--no-commit", "--no-branch"], input=content)
        assert result.exit_code == 1
        assert "title" in result.output.lower()

    def test_increments_spec_number(self, project: Path) -> None:
        specs = project / ".ai-engineering" / "context" / "specs"
        (specs / "005-existing").mkdir()
        content = "# New\n\n## Problem\nX.\n\n## Solution\nY.\n"
        app = self._make_app()
        with patch("ai_engineering.cli_commands.spec_save._project_root", return_value=project):
            result = runner.invoke(app, ["--no-commit", "--no-branch"], input=content)
        assert result.exit_code == 0, result.output
        assert "006-new" in result.output
