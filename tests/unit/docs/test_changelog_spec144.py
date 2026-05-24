"""Spec-144 changelog coverage.

These acceptance guards prove the spec-144 breaking rename and README brand
change stay documented in the changelog. Release promotion moves entries out of
``[Unreleased]`` into a versioned ``[X.Y.Z]`` section, so the guards search every
``### BREAKING`` / ``### Changed`` subsection across the whole changelog rather
than only the (post-release empty) ``[Unreleased]`` section.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = ROOT / "CHANGELOG.md"
OLD_BRANCH_CLEANUP_SKILL = "/" + "-".join(("ai", "repo", "tidy"))


def _subsection_bodies(heading: str) -> str:
    """Concatenate every ``### {heading}`` subsection body across the changelog."""
    text = CHANGELOG.read_text(encoding="utf-8")
    marker = f"### {heading}"
    bodies: list[str] = []
    for match in re.finditer(rf"^{re.escape(marker)}\s*$", text, re.MULTILINE):
        start = match.end()
        nxt = re.search(r"^(?:### |## )", text[start:], re.MULTILINE)
        end = start + nxt.start() if nxt else len(text)
        bodies.append(text[start:end])
    return "\n".join(bodies)


def test_changelog_records_branch_cleanup_breaking_rename() -> None:
    breaking = _subsection_bodies("BREAKING")
    assert OLD_BRANCH_CLEANUP_SKILL in breaking
    assert "/ai-branch-cleanup" in breaking
    assert "no alias" in breaking.lower() or "no shim" in breaking.lower()


def test_changelog_records_readme_brand_change() -> None:
    changed = _subsection_bodies("Changed")
    lowered = changed.lower()
    assert "readme" in lowered
    assert "brand" in lowered
