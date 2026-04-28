"""Tests guarding the spec-101 BREAKING entry in CHANGELOG.md (T-5.12/T-5.13).

The release engineer or future contributors might trim the BREAKING block
when consolidating Unreleased changes; this test pins the four contract
keywords so a regression cannot land silently:

- ``EXIT 80``  (missing required tool)
- ``EXIT 81``  (missing SDK prereq)
- ``python_env.mode``  (default flip + escape hatches)
- ``14 stacks``  (required_tools coverage scope)

The test reads the most recent ``BREAKING`` block in CHANGELOG.md and
asserts each keyword is present. "Most recent" = the first BREAKING
section after the topmost ``## [...]`` header, which is currently the
``[Unreleased]`` section.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHANGELOG = _REPO_ROOT / "CHANGELOG.md"

# Keywords that MUST appear in the most recent BREAKING entry.
_REQUIRED_KEYWORDS: tuple[str, ...] = (
    "EXIT 80",
    "EXIT 81",
    "python_env.mode",
    "14 stacks",
)


def _extract_most_recent_breaking_block(changelog_text: str) -> str:
    """Return the body of the most recent ``### BREAKING`` block.

    We scan from the top of the file for the first ``### BREAKING`` heading
    and stop at the next top-level ``## `` heading or the next ``### ``
    heading at the same level. Anything between those bounds is the body.

    Raises:
        AssertionError if no BREAKING block is found.
    """
    lines = changelog_text.splitlines()

    start = None
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith("### breaking"):
            start = idx + 1
            break

    if start is None:
        msg = "CHANGELOG.md must contain a `### BREAKING` section after spec-101."
        raise AssertionError(msg)

    end = len(lines)
    for idx in range(start, len(lines)):
        line = lines[idx]
        # Stop at next top-level version heading or next sibling section.
        if line.startswith("## "):
            end = idx
            break
        if line.startswith("### ") and idx != start - 1:
            end = idx
            break

    return "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChangelogBreakingKeywords:
    """The most recent BREAKING entry mentions the spec-101 contract keywords."""

    def test_changelog_exists(self) -> None:
        assert _CHANGELOG.exists(), f"CHANGELOG.md must exist at {_CHANGELOG}"

    def test_breaking_block_present(self) -> None:
        text = _CHANGELOG.read_text(encoding="utf-8")
        block = _extract_most_recent_breaking_block(text)
        assert block.strip(), "Most recent BREAKING block must not be empty"

    @pytest.mark.parametrize("keyword", _REQUIRED_KEYWORDS)
    def test_keyword_in_breaking_block(self, keyword: str) -> None:
        """Every required spec-101 keyword shows up in the BREAKING block."""
        text = _CHANGELOG.read_text(encoding="utf-8")
        block = _extract_most_recent_breaking_block(text)
        assert keyword in block, (
            f"Spec-101 keyword {keyword!r} missing from most recent BREAKING block. "
            "Restore it -- this guards against accidental documentation regression."
        )
