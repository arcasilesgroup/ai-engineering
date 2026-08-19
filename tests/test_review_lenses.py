"""The routing `EP-251` asks for, and the one case it exists to get right.

The requirement is narrow and easy to satisfy dishonestly: the motion lens must load only
where the diff carries real motion. A router that loads it on every stylesheet satisfies the
word "frontend" and misses the point — a static layout change is not motion, the lens says so
in its own first paragraph, and until this table nothing computed the difference.

So the case that matters here is the negative one: a stylesheet with no movement in it routes
to frontend and not to motion. Everything else is scaffolding around that.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import review_lenses  # noqa: E402 — the reader under test, beside this file


def by_id(name: str) -> dict:
    return next(row for row in review_lenses.table() if row["id"] == name)


# One file, three changes to it, and the routing each is owed. The same stylesheet appears
# twice on purpose: a router that never loads motion passes the first row and one that loads
# it on every stylesheet passes the second, so only the pair says anything. The third is the
# false positive this would otherwise have — "status transitions" is a phrase this repository
# uses constantly, and matching content without first matching a path would route every
# schema change to the motion lens.
ROUTING = [
    ("site/card.css", "+.card { border: 1px solid #ccc; padding: 12px }", "frontend", "motion"),
    ("site/card.css", "+.card { transition: transform 160ms ease }", "motion", None),
    ("docs/adr/0009-states.md", "+the record's status transitions are closed", "docs", "motion"),
]


@pytest.mark.parametrize("name, added, loads, skips", ROUTING)
def test_the_lens_a_change_routes_to_is_the_one_the_change_is_about(name, added, loads, skips):
    """`EP-251`: the motion lens loads only where the diff carries real motion. Both the
    frontend row and the motion row name `.css`; only one reads the lines, and that
    difference is the whole requirement."""

    assert review_lenses.routes(by_id(loads), [name], added), f"{name} is a {loads} change"
    if skips:
        assert not review_lenses.routes(by_id(skips), [name], added), (
            f"{name} is not what the {skips} lens is for, in that lens's own words"
        )



def test_every_lens_that_always_loads_does_so_over_an_empty_diff():
    """Security is the lens `ai-review` names as the one that gets skipped, and a rule that
    could skip it automates the failure the skill warns about. Asserted over every always-row
    rather than a chosen four, so a row that quietly becomes conditional is caught."""

    always = [row for row in review_lenses.table() if row.get("always")]

    assert len(always) >= 4, "the unconditional half is thinner than the lenses it names"
    assert all(review_lenses.routes(row, [], "") for row in always)
    assert "security" in {row["id"] for row in always}


def test_a_lens_file_with_no_row_is_refused():
    """The gap that made this table worth writing: eight of ten lenses declared nothing, so
    nobody could tell an always-worked lens from one nobody had thought about."""

    rows = [row for row in review_lenses.table() if row["id"] != "motion"]

    wrong = review_lenses.shape(rows)

    assert any("motion.md is a lens with no row" in one for one in wrong)


def test_a_row_that_is_both_always_and_conditional_is_refused():
    """Two rules for one lens is two answers, and the reader would take the first."""

    both = dict(by_id("motion"))
    both["always"] = True

    assert any("both always and conditional" in one for one in review_lenses.shape([both]))
    neither = {"id": "x", "file": "motion.md", "why": "a reason long enough to pass the check"}
    assert any("both always and conditional" in one for one in review_lenses.shape([neither])), (
        "a lens with no rule at all is the same defect as a lens with two"
    )
