"""The page a person reads, and the three things that make it worth reading.

A generated document is only worth what its freshness check is worth. This one carries a
digest of every fact it was built from, and the gate recomputes it — so the page cannot
quietly stop being true. The third test below is the regression for the defect this
generator already had once: three numbers were printed and left out of the digest, so they
could drift while the check reported fresh.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from ai_engineering import solution_intent

ROOT = Path(__file__).resolve().parents[1]


def test_the_page_it_just_wrote_is_about_this_tree():
    """Write, then ask. Anything else is a timestamp wearing a proof."""

    solution_intent.write(ROOT)
    fresh, why = solution_intent.staleness(ROOT)

    assert fresh, why
    assert "matches this tree" in why


def test_a_specification_that_changed_makes_the_page_stale(tmp_path):
    """One edit anywhere the page reads, and the check says so — naming both digests, so a
    reader can tell a stale page from a page nobody generated."""

    solution_intent.write(ROOT)
    home = ROOT / "specs" / "019-the-four-days-two-specs-cost" / "spec.md"
    before = home.read_text(encoding="utf-8")
    try:
        home.write_text(before.replace("status: draft", "status: shipped", 1), encoding="utf-8")
        fresh, why = solution_intent.staleness(ROOT)
    finally:
        home.write_text(before, encoding="utf-8")

    assert not fresh
    assert "was built from" in why and "this tree hashes to" in why

    # And it comes back. A check that stays red after the cause is gone teaches people to
    # ignore it.
    assert solution_intent.staleness(ROOT)[0]


def test_every_fact_the_page_renders_is_a_fact_the_digest_covers():
    """The defect this generator shipped with, as a test.

    The digest was built from a hand-written list of keys. Three fields the page prints as
    headline numbers were not on it, so they could go stale while the gate reported fresh —
    and the page's whole claim is that it cannot. It is derived from the dataclass now, so a
    field added to `Tree` and rendered cannot escape the hash without this going red.
    """

    covered = set(solution_intent.digested(solution_intent.read(ROOT)))
    every = {field.name for field in dataclasses.fields(solution_intent.Tree)}

    escaped = sorted(every - covered - set(solution_intent.NOT_HASHED))
    assert every - covered == set(solution_intent.NOT_HASHED), (
        f"these fields are rendered and not hashed: {escaped}"
    )
    # And the one exclusion is argued rather than assumed.
    assert solution_intent.NOT_HASHED == ("head",)


def test_the_numbers_the_page_prints_are_the_numbers_the_gate_enforces():
    """It counted lines with its own walk and read 1.85:1 where the ratio gate measures
    1.98 against a maximum of 2.0 — a human reading 0.13 of headroom that does not exist.
    Both halves come from `contract` now, so they cannot disagree."""

    from ai_engineering import contract

    tree = solution_intent.read(ROOT)
    tests, product = contract.test_ratio(ROOT)

    assert (tree.test_lines, tree.src_lines) == (tests, product)
    assert tree.ceiling == contract.REPO_CEILING
    assert tree.ratio_max == contract.TEST_RATIO_MAX
