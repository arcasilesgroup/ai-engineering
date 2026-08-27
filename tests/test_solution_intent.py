"""The page a person reads, and the three things that make it worth reading.

A generated document is only worth what its freshness check is worth. This one carries a
digest of every fact it was built from, and the gate recomputes it — so the page cannot
quietly stop being true. The third test below is the regression for the defect this
generator already had once: three numbers were printed and left out of the digest, so they
could drift while the check reported fresh.
"""

from __future__ import annotations

import dataclasses
import html
from pathlib import Path

import pytest

from ai_engineering import blocked, solution_intent

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


def _tree():
    """This tree as the page reads it, or a skip when it cannot be read at all.

    Every case here that calls `read(ROOT)` assumes there is a repository to read. Under
    `mutmut` there is not: the copied tree is not a git checkout, `read` raises `Unreadable`
    exactly as it is designed to, and a case that meant to compare a page against a tree
    fails because there was no tree. That is the product being right and the test being
    two-state.

    Cannot-read is the third state and it belongs here rather than in each case, because the
    mutation lane found this file one case at a time.
    """

    try:
        return solution_intent.read(ROOT)
    except solution_intent.Unreadable as why:
        pytest.skip(f"this tree cannot be read as a repository, so the page is unrenderable: {why}")


def test_a_record_that_changed_makes_the_page_stale():
    """One change to anything the page reads, and the check says so — naming both digests,
    so a reader can tell a stale page from a page nobody generated.

    Driven through the record rather than by editing a file in the tree: the property is
    that a different tree renders a different page, and mutating a governed document to
    assert it would be the test writing where it is only supposed to read.
    """

    import dataclasses

    page = (ROOT / solution_intent.PAGE).read_text(encoding="utf-8")

    tree = _tree()
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

    covered = set(solution_intent.digested(_tree()))
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

    tree = _tree()
    tests, product = contract.test_ratio(ROOT)

    assert (tree.test_lines, tree.src_lines) == (tests, product)
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


def test_a_row_that_changed_makes_the_page_stale(tmp_path):
    """What is waiting for a person is in the digest, so a new halt cannot arrive quietly.

    The page carries a hash of every record it was built from and `just check` recomputes it.
    A row added, a reason reworded or an action changed all move that hash — which is the
    point: a build that halts and records it makes the committed page stale, and the gate
    says so on the next run rather than the person finding out never.
    """

    tree = solution_intent.read(ROOT)
    payload = solution_intent.digested(tree)
    assert "blocked" in payload
    assert "considered" in payload

    assert tree.blocked, "this tree has unapproved drafts and BLOCKED verdicts"
    assert tree.considered >= len(tree.blocked)

    import dataclasses

    reworded = dataclasses.replace(
        tree,
        blocked=tuple(dataclasses.replace(row, action="something else") for row in tree.blocked),
    )
    assert solution_intent.digest(reworded) != solution_intent.digest(tree)
    assert solution_intent.render(reworded) != solution_intent.render(tree)

    # And the denominator moves on its own: a row dropped for saying nothing is invisible in
    # the table and visible in the count, which is the whole reason the count is rendered.
    fewer = dataclasses.replace(tree, considered=tree.considered + 1)
    assert solution_intent.digest(fewer) != solution_intent.digest(tree)


def test_an_unreadable_ledger_refuses_rather_than_rendering_nothing_is_stuck(monkeypatch):
    """The fail-open this page already closed once for the tracked-file list. A ledger nobody
    can parse, read as "nothing is waiting", renders a green section over a tree nobody
    measured — and the operator's next move after a red gate is to regenerate the page, which
    would then commit that green.

    Driven through the collector rather than by writing a broken `docs/blocked.toml` into the
    repository: the suite runs across workers over this one tree, and a test that corrupts a
    governed file for the length of two calls is the defect that cost two gates a day ago.
    """

    def refuse(_root):
        raise blocked.Unreadable("docs/blocked.toml could not be read")

    monkeypatch.setattr(solution_intent.blocked_ledger, "collect", refuse)

    with pytest.raises(blocked.Unreadable):
        solution_intent.read(ROOT)


def test_a_row_with_no_action_is_absent_and_the_count_says_so():
    """The filter has to be visible or it is the thing it was built to remove.

    Twenty-two rows of twenty-eight candidates on this tree: the six missing are drafts with
    no plan, waiting on the build rather than on a person. A section that showed twenty-two
    and said nothing about the six would read as "this is everything", which is exactly how a
    list stops being trusted the first time somebody finds something it did not mention.
    """

    tree = solution_intent.read(ROOT)
    page = solution_intent.render(tree)

    assert '<section id="bloqueos">' in page
    # Immediately after the summary. It is the thing a person opens this page for, and a
    # section below the fold is a section behind a scroll nobody makes.
    assert page.index('id="bloqueos"') < page.index('id="ciclo"')
    assert page.index('id="resumen"') < page.index('id="bloqueos"')

    section = page.split('<section id="bloqueos">', 1)[1].split("</section>", 1)[0]

    # Every row the collector returns, and none it dropped.
    for row in tree.blocked:
        assert html.escape(row.what) in section, row.id
        assert html.escape(row.action) in section, row.id
    assert section.count("<tr>") == len(tree.blocked) + 1, "one header row and one per item"

    # The denominator, recomputed here rather than read off the tree it is supposed to check.
    # Asserting `considered >= len(blocked)` was the first version and it survives the
    # sabotage that matters: `considered = len(waiting)` collapses the denominator to the
    # numerator, the page reads "22 de 22", the six drops vanish, and the whole disclosure —
    # which is the only answer specification 020 gave to its own strongest challenge — is
    # gone with the suite green.
    shown, dropped = blocked.collect(ROOT)
    assert tree.considered == len(shown) + len(dropped)
    assert tree.considered > len(tree.blocked), "this tree drops six drafts with no plan"
    assert f"{len(tree.blocked)} of {tree.considered}" in section

    # And the clause, not the bare digit. `str(considered - len(blocked))` is "6" on this
    # tree, and every date cell in the table contains "2026" — so deleting the entire
    # disclosure paragraph left that assertion passing on a substring of a date.
    assert f"{tree.considered - len(tree.blocked)} do not say the four things" in " ".join(
        section.split()
    )


def test_a_tree_with_nothing_waiting_says_so_in_a_sentence():
    """Zero rows is not an empty table, and two different zeros are not the same sentence.

    Nothing looked at is good news. Twenty-eight looked at and every one refused is not: some
    of those really do wait on a person, and a page that answered both with "nada espera a una
    persona" would be asserting the headline over a tree it had just failed to read.

    Both branches are asserted on their distinguishing words. The first version tested only
    the first and looked for "nada", which is a substring of the second sentence too — so
    deleting one branch entirely left the suite green.
    """

    import dataclasses

    def section(considered: int) -> str:
        tree = dataclasses.replace(solution_intent.read(ROOT), blocked=(), considered=considered)
        return (
            solution_intent.render(tree)
            .split('<section id="bloqueos">', 1)[1]
            .split("</section>", 1)[0]
        )

    clear = section(0)
    assert "<table>" not in clear
    assert "Nothing is waiting for a person right now." in clear
    assert "the four things" not in clear

    refused = section(28)
    assert "<table>" not in refused
    assert "candidates were examined" in refused
    assert "none of them says all" in refused
    assert "nothing says what to do" in refused

    # One candidate is one candidate, and the verb agrees with it. A count line that
    # cannot count to one reads as generated, and this one is the first thing a person
    # sees on the page.
    assert "1 candidate was examined" in section(1)


def test_a_hostile_row_cannot_reach_the_page_unescaped():
    """Every cell in this section is untrusted input. `what`, `why` and `action` arrive from
    `docs/requirements.toml` and from argv through `ai-eng report blocked`, and they land in
    a rendered document somebody opens in a browser.

    Asserted over a synthetic row rather than over the tree's own data: the tree happens to
    carry an apostrophe in two evidence commands, so removing `html.escape` from the action
    cell fails today by luck. Luck is not a control.
    """

    import dataclasses

    hostile = blocked.Row(
        kind="halt",
        id='<img src=x onerror="alert(1)">',
        what="gate <b>one</b>",
        since="2026-08-19 & later",
        why='missing "authority" & more',
        action="</code><script>alert(document.domain)</script><code>",
    )
    tree = dataclasses.replace(solution_intent.read(ROOT), blocked=(hostile,), considered=1)
    section = (
        solution_intent.render(tree)
        .split('<section id="bloqueos">', 1)[1]
        .split("</section>", 1)[0]
    )

    # Every cell, not the three a hand-written assertion happened to name. Removing
    # `html.escape` one cell at a time, the first version caught `id`, `why` and `action` and
    # missed `what` and `since` — and `what` is the one that comes straight from argv.
    for cell in (hostile.id, hostile.what, hostile.since, hostile.why, hostile.action):
        assert cell not in section, cell
    assert "<script>" not in section
    assert "<img" not in section
    assert "&lt;script&gt;alert(document.domain)&lt;/script&gt;" in section


def test_every_kind_the_collector_can_return_has_a_label():
    """`_KIND` restates `blocked.ORDER` and nothing held them equal. A fourth kind added in
    the collector printed its raw English identifier in a Spanish column — the documented
    fallback firing, which is correct behaviour for an unknown kind and wrong for a known
    one nobody remembered to name here."""

    assert set(solution_intent._KIND) == set(blocked.ORDER)


def test_a_percentage_the_page_prints_covers_the_whole_population_it_names():
    """The page said `18/18` at 100% for months, and every digit of it was true.

    It counted `- [x]` list checkboxes. Exactly two of sixteen plans use that shape, so the
    other fourteen left the numerator *and* the denominator in silence — and a number that
    is arithmetically correct read as a finished project. The small print said "in 2 of 14
    plans" underneath, which is not where anybody looks before the headline.

    So the rule this pins is not "compute it from the tree": that number always was. It is
    that a denominator has to be the whole population its label names, and the "of how many"
    has to survive inside the number rather than under it."""

    tree = _tree()
    page = solution_intent.render(tree)

    # The population the label names is tasks, so every plan that has tasks is in it.
    numbered = sum(s.tasks for s in tree.specs)
    with_check = sum(s.checks for s in tree.specs)
    assert numbered > 0, "no plan carries a task a script can enumerate; this asserts nothing"
    assert f"{with_check}/{numbered}" in page

    # And the plans that carry none are named rather than dropped, because "6 of 16" with no
    # account of the other ten is the same silence one level down.
    plans_with = sum(1 for s in tree.specs if s.tasks)
    plans_all = sum(1 for s in tree.specs if s.has_plan)
    assert f"in {plans_with} of {plans_all} plans" in page
    assert f"the other {plans_all - plans_with}" in page

    # The shape that produced the lie does not come back.
    assert "casillas de plan marcadas" not in page
