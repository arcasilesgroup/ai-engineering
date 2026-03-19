"""Unit tests for spec helper functions in ai_engineering.lib.parsing.

Covers:
- next_spec_number: history parsing, frontmatter fallback, empty/missing dirs.
- slugify: kebab-case conversion, special characters, truncation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.lib.parsing import next_spec_number, slugify

pytestmark = pytest.mark.unit


class TestSlugify:
    """Tests for slugify()."""

    def test_basic_title(self) -> None:
        """Simple multi-word title becomes kebab-case."""
        assert slugify("OAuth Authentication") == "oauth-authentication"

    def test_special_characters_stripped(self) -> None:
        """Non-alphanumeric characters (except hyphens) are removed."""
        assert slugify("Add OAuth 2.0!") == "add-oauth-20"

    def test_truncates_long_titles(self) -> None:
        """Slugs are truncated to 40 characters max."""
        long_title = "a very long title that exceeds the maximum slug length allowed"
        result = slugify(long_title)
        assert len(result) <= 40

    def test_collapses_multiple_spaces(self) -> None:
        """Multiple spaces collapse into a single hyphen."""
        assert slugify("too   many   spaces") == "too-many-spaces"

    def test_underscores_become_hyphens(self) -> None:
        """Underscores are converted to hyphens."""
        assert slugify("my_cool_feature") == "my-cool-feature"

    def test_strips_leading_trailing_hyphens(self) -> None:
        """Leading and trailing hyphens are removed."""
        assert slugify("--hello--") == "hello"

    def test_empty_string(self) -> None:
        """Empty input returns empty string."""
        assert slugify("") == ""

    def test_only_special_chars(self) -> None:
        """Input with only special characters returns empty string."""
        assert slugify("!!!@@@###") == ""


class TestNextSpecNumber:
    """Tests for next_spec_number() (Working Buffer model)."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty specs directory returns 1."""
        specs = tmp_path / "specs"
        specs.mkdir()
        assert next_spec_number(specs) == 1

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent directory returns 1."""
        specs = tmp_path / "nonexistent"
        assert next_spec_number(specs) == 1

    def test_reads_from_history(self, tmp_path: Path) -> None:
        """Reads highest ID from _history.md table."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "_history.md").write_text(
            "# Spec History\n\n"
            "| ID | Title | Date | Branch |\n"
            "|-----|-------|------|--------|\n"
            "| 035 | Something | 2026-01-01 | spec/035 |\n"
            "| 036 | Other | 2026-01-15 | spec/036 |\n"
        )
        assert next_spec_number(specs) == 37

    def test_reads_from_current_spec_frontmatter(self, tmp_path: Path) -> None:
        """Reads current spec ID from spec.md frontmatter."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "spec.md").write_text('---\nid: "040"\n---\n\n# Feature\n')
        assert next_spec_number(specs) == 41

    def test_history_and_spec_combined(self, tmp_path: Path) -> None:
        """Takes the maximum of history and current spec."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "_history.md").write_text(
            "# Spec History\n\n"
            "| ID | Title | Date | Branch |\n"
            "|-----|-------|------|--------|\n"
            "| 030 | Old | 2025-01-01 | spec/030 |\n"
        )
        (specs / "spec.md").write_text('---\nid: "042"\n---\n\n# Current\n')
        assert next_spec_number(specs) == 43

    def test_ignores_placeholder_spec(self, tmp_path: Path) -> None:
        """Placeholder spec.md does not contribute a number."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "spec.md").write_text("# No active spec\n\nRun /ai-brainstorm.\n")
        assert next_spec_number(specs) == 1

    def test_ignores_non_numeric_ids_in_history(self, tmp_path: Path) -> None:
        """Non-numeric table rows in _history.md are ignored."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "_history.md").write_text(
            "# Spec History\n\n"
            "| ID | Title | Date | Branch |\n"
            "|-----|-------|------|--------|\n"
            "| abc | Invalid | 2026-01-01 | x |\n"
            "| 005 | Valid | 2026-01-02 | y |\n"
        )
        assert next_spec_number(specs) == 6
