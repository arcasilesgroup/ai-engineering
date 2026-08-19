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


def test_a_record_that_changed_makes_the_page_stale():
    """One change to anything the page reads, and the check says so — naming both digests,
    so a reader can tell a stale page from a page nobody generated.

    Driven through the record rather than by editing a file in the tree: the property is
    that a different tree renders a different page, and mutating a governed document to
    assert it would be the test writing where it is only supposed to read.
    """

    import dataclasses

    solution_intent.write(ROOT)
    page = (ROOT / solution_intent.PAGE).read_text(encoding="utf-8")

    tree = solution_intent.read(ROOT)
    moved = dataclasses.replace(tree, decisions=tree.decisions[:-1])

    assert solution_intent.render(moved) != page
    assert solution_intent.digest(moved) != solution_intent.digest(tree)
    # And the tree as it stands still matches, so the difference is the change and not the
    # comparison.
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
    assert solution_intent.NOT_HASHED == ()


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


def test_a_page_somebody_edited_is_not_a_page_this_tree_renders():
    """The defect this control shipped with, as a test.

    It compared a digest of the inputs to an attribute in the file and never asked whether
    the file rendered them. A reviewer flipped nine readiness boxes to PASS and the skill
    count to 99, left the attribute alone, and the gate said PASS — a page claiming
    production readiness it does not have, and the only control that exists calling it fine.

    A hand edit is the unlikely path. A badly resolved merge conflict in a generated file of
    two hundred lines is the likely one, and it looks exactly the same to the gate.
    """

    solution_intent.write(ROOT)
    page = ROOT / solution_intent.PAGE
    before = page.read_text(encoding="utf-8")
    try:
        page.write_text(
            before.replace("INCOMPLETE", "PASS").replace(">13<", ">99<"), encoding="utf-8"
        )
        fresh, why = solution_intent.staleness(ROOT)
    finally:
        page.write_text(before, encoding="utf-8")

    assert not fresh
    assert "edited the page rather than the records" in why
    assert solution_intent.staleness(ROOT)[0]
