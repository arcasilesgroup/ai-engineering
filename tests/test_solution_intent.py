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


def test_the_committed_page_is_the_page_one_reading_of_this_tree_renders():
    """The property, asserted without writing anything and over a single reading.

    It used to write the real page and then ask about it, which is the same claim and a
    worse test: the suite runs across workers, so two tests writing one file in the tree
    they are both reading is a race, and it found it — a worker read the page mid-write and
    reported that it carried no digest at all.

    The second race is the one this shape fixes. `staleness` reads the tree, then the byte
    comparison read it again, and between the two another worker's write can move a record —
    so the page was compared against a tree that never existed at any single instant. It
    failed exactly that way once the surface receipts started proving three states, and the
    failure said the page was stale when the page was correct.

    One read, used for both halves. The gate's own `intent-page` step makes the same
    comparison in a single process at a defined moment, and that is the one a person should
    believe; this case exists to keep the mechanism honest, not to re-run the gate.
    """

    tree = solution_intent.read(ROOT)
    page = (ROOT / solution_intent.PAGE).read_text(encoding="utf-8")

    assert page == solution_intent.render(tree)
    assert solution_intent.digest(tree) in page, (
        "the page does not carry the digest of the tree it renders, so nothing later can "
        "tell a stale page from a page nobody generated"
    )


def test_a_record_that_changed_makes_the_page_stale():
    """One change to anything the page reads, and the check says so — naming both digests,
    so a reader can tell a stale page from a page nobody generated.

    Driven through the record rather than by editing a file in the tree: the property is
    that a different tree renders a different page, and mutating a governed document to
    assert it would be the test writing where it is only supposed to read.
    """

    import dataclasses

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


def test_a_page_somebody_edited_is_not_a_page_this_tree_renders(tmp_path):
    """The defect this control shipped with, as a test.

    It compared a digest of the inputs to an attribute in the file and never asked whether
    the file rendered them. A reviewer flipped nine readiness boxes to PASS and the skill
    count to 99, left the attribute alone, and the gate said PASS — a page claiming
    production readiness it does not have, and the only control that exists calling it fine.

    A hand edit is the unlikely path. A badly resolved merge conflict in a generated file of
    two hundred lines is the likely one, and it looks exactly the same to the gate.
    """

    solution_intent.write(tmp_path)
    page = tmp_path / solution_intent.PAGE
    honest = page.read_text(encoding="utf-8")
    assert solution_intent.staleness(tmp_path)[0]

    # The digest attribute is left exactly as it was; only what a reader sees changes.
    page.write_text(honest.replace("INCOMPLETE", "PASS").replace(">0<", ">99<"), encoding="utf-8")
    fresh, why = solution_intent.staleness(tmp_path)

    assert not fresh
    assert "edited the page rather than the records" in why

    # In its own directory, because the suite runs across workers and a test that edits the
    # page in the tree it is reading is a race with every other test that reads it.
    page.write_text(honest, encoding="utf-8")
    assert solution_intent.staleness(tmp_path)[0]


def test_a_tree_git_cannot_list_refuses_rather_than_rendering_nothing(tmp_path):
    """The write used to fail open where the check fails closed.

    With an empty index every collector comes back empty, so `staleness` compares an empty
    page to the committed one and reds — correctly. And the operator's next move after a red
    gate is the command the message names, which would have written that empty page over the
    good one. The check and the write now fail the same way.
    """

    import pytest

    (tmp_path / "specs").mkdir()

    with pytest.raises(solution_intent.Unreadable):
        solution_intent.read(tmp_path)
    with pytest.raises(solution_intent.Unreadable):
        solution_intent.write(tmp_path)

    assert not (tmp_path / solution_intent.PAGE).exists()
