"""Unit tests for ai_engineering.lib.parsing.

Covers:
- parse_frontmatter: various formats, edge cases.
- count_checkboxes: checked/unchecked, mixed content.
"""

from __future__ import annotations

import pytest

from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter

pytestmark = pytest.mark.unit


class TestParseFrontmatter:
    """Tests for parse_frontmatter()."""

    def test_double_quoted_values(self) -> None:
        """Values in double quotes are extracted."""
        text = '---\nid: "033"\nslug: "audit"\n---\n# Body'
        fm = parse_frontmatter(text)
        assert fm == {"id": "033", "slug": "audit"}

    def test_single_quoted_values(self) -> None:
        """Values in single quotes are extracted."""
        text = "---\nid: '033'\nslug: 'audit'\n---\n# Body"
        fm = parse_frontmatter(text)
        assert fm == {"id": "033", "slug": "audit"}

    def test_unquoted_values(self) -> None:
        """Unquoted values are extracted and stripped."""
        text = "---\ntotal: 5\ncompleted: 3\n---\n# Body"
        fm = parse_frontmatter(text)
        assert fm == {"total": "5", "completed": "3"}

    def test_null_value(self) -> None:
        """Unquoted null is extracted as the string 'null'."""
        text = '---\nactive: null\nupdated: "2026-03-04"\n---\n'
        fm = parse_frontmatter(text)
        assert fm["active"] == "null"

    def test_no_frontmatter(self) -> None:
        """Text without --- fences returns empty dict."""
        text = "# Just a heading\nSome content."
        fm = parse_frontmatter(text)
        assert fm == {}

    def test_empty_frontmatter(self) -> None:
        """Empty frontmatter block returns empty dict."""
        text = "---\n---\n# Body"
        fm = parse_frontmatter(text)
        assert fm == {}

    def test_mixed_quotes(self) -> None:
        """Mixed quoting styles in the same frontmatter."""
        text = "---\nid: \"034\"\nslug: lifecycle\nstatus: 'draft'\n---\n"
        fm = parse_frontmatter(text)
        assert fm["id"] == "034"
        assert fm["slug"] == "lifecycle"
        assert fm["status"] == "draft"

    def test_hyphenated_keys(self) -> None:
        """Keys with hyphens are supported."""
        text = "---\nlast-session: 2026-03-04\n---\n"
        fm = parse_frontmatter(text)
        assert fm["last-session"] == "2026-03-04"

    def test_ignores_non_kv_lines(self) -> None:
        """Lines without key-value pattern are skipped."""
        text = '---\nid: "033"\nThis is not a kv line\nslug: "audit"\n---\n'
        fm = parse_frontmatter(text)
        assert "id" in fm
        assert "slug" in fm
        assert len(fm) == 2


class TestCountCheckboxes:
    """Tests for count_checkboxes()."""

    def test_all_unchecked(self) -> None:
        """All unchecked checkboxes."""
        text = "- [ ] Task 1\n- [ ] Task 2\n- [ ] Task 3\n"
        total, checked = count_checkboxes(text)
        assert total == 3
        assert checked == 0

    def test_all_checked(self) -> None:
        """All checked checkboxes."""
        text = "- [x] Task 1\n- [x] Task 2\n"
        total, checked = count_checkboxes(text)
        assert total == 2
        assert checked == 2

    def test_mixed(self) -> None:
        """Mix of checked and unchecked."""
        text = "- [x] Done\n- [ ] Todo\n- [X] Also done\n- [ ] Also todo\n"
        total, checked = count_checkboxes(text)
        assert total == 4
        assert checked == 2

    def test_no_checkboxes(self) -> None:
        """No checkboxes returns (0, 0)."""
        text = "# Heading\nSome paragraph text.\n"
        total, checked = count_checkboxes(text)
        assert total == 0
        assert checked == 0

    def test_checkboxes_with_surrounding_content(self) -> None:
        """Checkboxes embedded in other content."""
        text = (
            "# Tasks\n\n## Phase 1\n\n"
            "- [x] 1.1 Do thing\n"
            "- [ ] 1.2 Do other\n\n"
            "## Phase 2\n\n"
            "- [x] 2.1 Done\n"
            "- [x] 2.2 Done\n"
            "- [ ] 2.3 Not done\n"
        )
        total, checked = count_checkboxes(text)
        assert total == 5
        assert checked == 3

    def test_uppercase_x(self) -> None:
        """Uppercase X is recognized as checked."""
        text = "- [X] Task with uppercase X\n"
        total, checked = count_checkboxes(text)
        assert total == 1
        assert checked == 1
