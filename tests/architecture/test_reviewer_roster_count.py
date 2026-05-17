"""Reviewer roster count enforcement (spec-140 W3).

Spec-140 W3 collapsed the reviewer specialist roster from 11 to 6:

Kept (6):
    - reviewer-correctness   (absorbs architecture + maintainability heuristics)
    - reviewer-security
    - reviewer-testing
    - reviewer-performance
    - reviewer-frontend      (conditional on UI diff)
    - reviewer-compatibility

Merged into reviewer-correctness (file deleted, content absorbed):
    - reviewer-architecture
    - reviewer-maintainability

Deleted outright (categorical mismatch):
    - reviewer-backend

This test pins the count at 6 so a future operator cannot silently
re-add a specialist without touching the canonical SKILL.md roster
table at the same time. Reads ``.claude/agents/`` directly — no
manifest lookup, no decision-store query — per D-134-10.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_AGENTS = _REPO_ROOT / ".claude" / "agents"

EXPECTED_REVIEWERS: frozenset[str] = frozenset(
    {
        "reviewer-correctness",
        "reviewer-security",
        "reviewer-testing",
        "reviewer-performance",
        "reviewer-frontend",
        "reviewer-compatibility",
    }
)


def _reviewer_files() -> list[Path]:
    """Return the sorted list of reviewer-* agent files under .claude/agents/."""
    return sorted(_CANONICAL_AGENTS.glob("reviewer-*.md"))


@pytest.mark.unit
def test_reviewer_roster_has_six_entries() -> None:
    """The collapsed roster (spec-140 W3) declares exactly 6 reviewers."""
    reviewers = _reviewer_files()
    assert len(reviewers) == 6, (
        f"Expected 6 reviewer-* agents post spec-140 W3, found {len(reviewers)}: "
        f"{sorted(f.stem for f in reviewers)}"
    )


@pytest.mark.unit
def test_reviewer_roster_names_match_canonical_set() -> None:
    """Disk names must match the canonical post-W3 reviewer set."""
    names = {f.stem for f in _reviewer_files()}
    assert names == EXPECTED_REVIEWERS, (
        "Reviewer roster drift vs spec-140 W3 canonical set. "
        f"Missing: {EXPECTED_REVIEWERS - names}, "
        f"Extra: {names - EXPECTED_REVIEWERS}"
    )
