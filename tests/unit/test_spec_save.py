"""Unit tests for ai-eng spec save command."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.cli_commands.spec_save import (
    _build_spec_md,
    _build_tasks_md,
    _extract_section,
    _extract_title,
    _next_spec_number,
    _slugify,
    _validate_spec_content,
)


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
