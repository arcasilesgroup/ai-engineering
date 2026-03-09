"""Unit tests for spec helper functions in ai_engineering.lib.parsing.

Covers:
- next_spec_number: sequential numbering, archive scanning, empty/missing dirs.
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
    """Tests for next_spec_number()."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty specs directory returns 1."""
        specs = tmp_path / "specs"
        specs.mkdir()
        assert next_spec_number(specs) == 1

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent directory returns 1."""
        specs = tmp_path / "nonexistent"
        assert next_spec_number(specs) == 1

    def test_existing_specs(self, tmp_path: Path) -> None:
        """Returns max existing number + 1."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "035-something").mkdir()
        (specs / "036-other").mkdir()
        assert next_spec_number(specs) == 37

    def test_scans_archive(self, tmp_path: Path) -> None:
        """Archive directory is included in the scan."""
        specs = tmp_path / "specs"
        specs.mkdir()
        archive = specs / "archive"
        archive.mkdir()
        (archive / "030-old").mkdir()
        (specs / "036-current").mkdir()
        assert next_spec_number(specs) == 37

    def test_archive_has_higher_number(self, tmp_path: Path) -> None:
        """When archive contains the highest number, it is respected."""
        specs = tmp_path / "specs"
        specs.mkdir()
        archive = specs / "archive"
        archive.mkdir()
        (archive / "040-archived").mkdir()
        (specs / "036-current").mkdir()
        assert next_spec_number(specs) == 41

    def test_ignores_non_matching_dirs(self, tmp_path: Path) -> None:
        """Directories without NNN- prefix are ignored."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "readme.md").touch()
        (specs / "_active.md").touch()
        (specs / "not-a-spec").mkdir()
        (specs / "005-real-spec").mkdir()
        assert next_spec_number(specs) == 6

    def test_ignores_files(self, tmp_path: Path) -> None:
        """Files (not directories) are ignored even if they match the pattern."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "099-this-is-a-file.md").touch()
        assert next_spec_number(specs) == 1
