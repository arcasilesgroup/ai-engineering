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


# `staleness(ROOT)` is asserted by `just intent-page`, not from here, and the reason is a
# measurement rather than a preference. `read` opens live files in the working tree — every
# `SKILL.md` among them — while `-n auto` runs two thousand tests over that same tree, and
# at least one of them rewrites `.agents/skills/ai-build/SKILL.md` and puts it back within
# a single test. Polling caught the edit in flight; a before-and-after digest around every
# test never saw it. So a worker rendering the page while that file is briefly its other
# shape computes a different tree, and the check reds for a reason that has nothing to do
# with the page. A gate that fails on a coin flip is worse than no gate, because the first
# repair anyone reaches for is to stop believing it.
#
# The property is not weakened by moving it: `just intent-page` runs `staleness` on a quiet
# tree, alone, and `check` depends on it, so a stale page still fails the gate — that is the
# run that produced "was built from 5b289a3b8584; this tree hashes to efd74d77fd34" an hour
# ago. What is dropped is the second, concurrent copy of the same assertion.
#
# The test that edits a repository file transiently is its own defect and is recorded as
# one; it was not hunted down here because the page gate should not depend on the answer.


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
    # The tree as it stands matching is the other half of this claim, and it is asserted by
    # `just intent-page` for the reason written above the first test in this file.


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
