"""What is waiting for a person, and the four things a row has to say before it counts.

Specification 020. A list of things nobody can act on is a list people stop opening, so the
only rows this module returns are the ones carrying what is waiting, since when, why it
stopped and a literal the reader can copy. A row missing any of them is dropped and counted,
never returned with the gap filled in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering import blocked

ROOT = Path(__file__).resolve().parents[1]


def _ledger(root: Path, body: str) -> Path:
    (root / "docs").mkdir(exist_ok=True)
    where = root / "docs" / "blocked.toml"
    where.write_text(body, encoding="utf-8")
    return where


def test_a_row_missing_any_of_the_four_is_refused(tmp_path):
    """Four fields, and the fourth is the one that cannot be faked.

    The first three make a row readable. The fourth makes it actionable, and a section of
    rows a reader cannot act on is the failure mode specification 020 was challenged with
    and kept its scope to answer. So a row without one is not returned with an empty string
    in its place — an empty field renders as a blank cell, which reads as "nothing to do"
    rather than as "this row should not be here".
    """

    _ledger(
        tmp_path,
        """
[[stop]]
id = "whole"
what = "block H needs written authority"
since = "2026-08-19"
why = "the block header requires two digests and neither was named"
action = "apruebo 019 en cbba04d9"

[[stop]]
id = "no-action"
what = "something is stuck"
since = "2026-08-19"
why = "a reason"

[[stop]]
id = "empty-action"
what = "something else is stuck"
since = "2026-08-19"
why = "another reason"
action = "   "
""",
    )

    rows, dropped = blocked.stops(tmp_path)

    assert [row.id for row in rows] == ["whole"]
    assert rows[0].action == "apruebo 019 en cbba04d9"
    # Named, not just counted. A drop nobody can trace is a filter that hides itself, which
    # is the same defect as the silent block this specification exists to remove.
    assert sorted(dropped) == ["empty-action", "no-action"]

    for field in blocked.FIELDS:
        assert getattr(rows[0], field), field


def test_a_ledger_nobody_can_parse_refuses_rather_than_reading_empty(tmp_path):
    """The fail-open direction, closed in the same place the page's tracked-file list closed
    it. An unreadable record of what is stuck, read as "nothing is stuck", is worse than no
    record: it renders a green section over a tree nobody measured."""

    _ledger(tmp_path, "[[stop]\nid = broken")

    with pytest.raises(blocked.Unreadable):
        blocked.stops(tmp_path)


def test_a_tree_with_no_ledger_is_not_an_error(tmp_path):
    """A repository that has never halted has nothing to say, and saying nothing is the
    correct answer rather than a missing file."""

    (tmp_path / "docs").mkdir()

    rows, dropped = blocked.stops(tmp_path)

    assert rows == []
    assert dropped == []


def test_the_collector_says_what_it_dropped():
    """Over this tree, with the relationship asserted rather than the constants.

    A tree gains specifications, so a test that pinned "22 shown" would go red for the right
    reason on the wrong day. What must hold is that everything considered is either shown or
    named as dropped and nothing is both — plus, and this is the half the first version
    missed, that every class the collector claims to read actually produced something.

    The first version asserted `len(shown) + len(dropped) == considered(ROOT)`, where
    `considered` was `collect` called a second time. Both sides were the same expression. A
    reviewer deleted `_verdicts` outright — seventeen of the twenty-two rows, the entire
    class the specification's success example is about — and the whole suite stayed green.
    """

    shown, dropped = blocked.collect(ROOT)

    assert shown, "this tree has BLOCKED verdicts and unapproved drafts, so it is not empty"
    assert not set(row.id for row in shown) & set(dropped)

    # Every class this collector reads, present. `_verdicts` returning nothing at all was the
    # sabotage that survived the first version of this file.
    assert {row.kind for row in shown} == {"draft", "verdict"}, "this tree has no recorded halt"
    assert sum(1 for row in shown if row.kind == "verdict") >= 10

    # Both halves, because each alone is defeated. Restating the literal was a second copy
    # of a constant; reading `blocked.ORDER` on both sides of a list `collect` built by
    # iterating `blocked.ORDER` is a tautology that survives reversing it. So: the constant is
    # pinned to the literal, and the rows are sorted by the constant.
    assert blocked.ORDER == ("halt", "draft", "verdict")
    order = [row.kind for row in shown]
    assert order == sorted(order, key=blocked.ORDER.index)

    for row in shown:
        for field in blocked.FIELDS:
            assert getattr(row, field).strip(), (row.id, field)

    # A draft's action names the digest of the file as it is on disk, so approving it cannot
    # silently approve a later edit, and names the path so the reader can check it.
    from hashlib import sha256

    for row in (one for one in shown if one.kind == "draft"):
        home = next((ROOT / "specs").glob(f"{row.id}-*"))
        digest = sha256((home / "spec.md").read_bytes()).hexdigest()
        assert digest[:12] in row.action, (row.id, row.action)
        assert (home / "spec.md").relative_to(ROOT).as_posix() in row.action, row.action


def test_a_verdict_says_since_when_or_the_whole_class_refuses(tmp_path):
    """The seventeen rows four auditors filled in without knowing what for, and the one field
    they did not: the date, which is the file's rather than each row's.

    Refusing when the header stops saying it is deliberate. Dropped quietly, the count line
    would report seventeen items as waiting on the build when they are waiting on a person —
    a true number with a false reason, which is the defect this repository has shipped five
    times and the one `_rows` exists to stop.
    """

    (tmp_path / "docs").mkdir()
    where = tmp_path / "docs" / "requirements.toml"
    rows = """
[[requirement]]
id = "EP-018"
verdict = "BLOCKED"
subject = "a live editor invocation is receipted"
evidence = "find . -iname openai.yaml"
note = "needs an actual editor invoking a denial from a live session"

[[requirement]]
id = "EP-099"
verdict = "BLOCKED"
subject = "something unreachable"
evidence = "some command"

[[requirement]]
id = "EP-100"
verdict = "PROVEN"
subject = "not on this list at all"
evidence = "a command"
"""
    where.write_text("# Measured on 2026-08-17 by four auditors\n" + rows, encoding="utf-8")

    shown, dropped = blocked.collect(tmp_path)

    assert [row.id for row in shown] == ["EP-018"]
    assert dropped == ["EP-099"], "a row with no note is counted, not hidden"
    assert shown[0].kind == "verdict"
    assert shown[0].what == "a live editor invocation is receipted"
    assert shown[0].since == "2026-08-17"
    assert shown[0].why.startswith("needs an actual editor")
    assert shown[0].action == "find . -iname openai.yaml"

    where.write_text("# Re-measured on 2026-08-17\n" + rows, encoding="utf-8")
    with pytest.raises(blocked.Unreadable):
        blocked.collect(tmp_path)


def test_a_fourth_field_that_says_nothing_is_the_same_as_no_fourth_field(tmp_path):
    """The bug tracker specification 020 was challenged with, arriving through the one field
    that was supposed to prevent it. `action = "TODO"` is present, non-blank and useless."""

    for placeholder in ("TODO", "TBD", "ask the owner", "decide this", "n/a", "  "):
        _ledger(
            tmp_path,
            '[[stop]]\nid = "one"\nwhat = "a gate"\nsince = "2026-08-19"\n'
            f'why = "a reason"\naction = "{placeholder}"\n',
        )
        rows, dropped = blocked.stops(tmp_path)
        assert rows == [], placeholder
        assert dropped == ["one"], placeholder

    # And a field that is not a string at all is a drop, not something to coerce: a record
    # holding `true` or a list was hand-edited by somebody who meant something unknowable.
    _ledger(
        tmp_path,
        '[[stop]]\nid = "two"\nwhat = "a gate"\nsince = "2026-08-19"\n'
        'why = "a reason"\naction = true\n',
    )
    assert blocked.stops(tmp_path) == ([], ["two"])


def test_valid_toml_of_the_wrong_shape_refuses_rather_than_raising(tmp_path):
    """`[stop]` instead of `[[stop]]` is the likeliest hand-edit typo, and it parses. The
    first version called `.get` on the result and raised `AttributeError` through every
    caller that promised to refuse — including the one that runs while a build is failing."""

    for shape in ('[stop]\nid = "one"\n', 'stop = ["one"]\n'):
        _ledger(tmp_path, shape)
        with pytest.raises(blocked.Unreadable):
            blocked.stops(tmp_path)


def test_a_spec_nobody_can_read_the_front_of_is_counted_rather_than_skipped(tmp_path):
    """Three shapes made a specification vanish from both halves of the count, which is the
    filter hiding itself — the failure the specification says it must not have. The third is
    the dangerous one: a file that was never frontmattered was handed an approval literal."""

    (tmp_path / "docs").mkdir()
    bodies = {
        "040-quoted": ("---\nid: \"040\"\nstatus: 'draft'\ndate: 2026-08-19\n---\n\n# x\n"),
        "041-inner": (
            '---\nid: "041"\nstatus: draft\ndate: 2026-08-19\nsupersedes: "039---a"\n---\n\n# x\n'
        ),
        "042-none": "# a title\n\n---\n\nstatus: draft\n\n---\n\nmore prose\n",
    }
    for name, body in bodies.items():
        home = tmp_path / "specs" / name
        home.mkdir(parents=True)
        (home / "spec.md").write_text(body, encoding="utf-8")
        (home / "plan.md").write_text("# plan\n", encoding="utf-8")

    shown, dropped = blocked.collect(tmp_path)

    # The two real drafts are read despite the quoting and the inner marker; the file with no
    # frontmatter is counted as unreadable rather than handed an approval literal.
    assert sorted(row.id for row in shown) == ["040", "041"]
    assert dropped == ["042"]
    assert not any("042" in row.action for row in shown)


def test_a_draft_with_no_plan_is_counted_and_not_shown(tmp_path):
    """It is waiting on the build, not on a person, and a list of things the build owes
    itself is the bug tracker specification 020 refused to become."""

    (tmp_path / "docs").mkdir()
    for name, plan in (("030-with-a-plan", True), ("031-without", False)):
        home = tmp_path / "specs" / name
        home.mkdir(parents=True)
        (home / "spec.md").write_text(
            f'---\nid: "{name[:3]}"\nstatus: draft\ndate: 2026-08-19\n---\n\n# {name}\n',
            encoding="utf-8",
        )
        if plan:
            (home / "plan.md").write_text("# plan\n\n1. **a task**\n", encoding="utf-8")

    shown, dropped = blocked.collect(tmp_path)

    assert [row.id for row in shown] == ["030"]
    assert dropped == ["031"]


def test_the_six_repairs_that_had_no_check(tmp_path):
    """Six behaviours were repaired and then proved by nothing.

    A bounded re-review sabotaged each one and the suite stayed green: the id lost its hash,
    the nameless fallback went away, the directory stopped being created, the atomic rename
    became a plain write. A fix whose whole justification is a case the suite cannot see is a
    fix that will be undone by the next person who finds it untidy.
    """

    # `_name` carries a hash, because two gates whose first forty characters agree — and
    # block headers phrased by the same skill routinely do — otherwise share one id.
    long_one = "the block header requires written authority naming two digests and neither came"
    long_two = "the block header requires written authority naming two SHA-256 digests"
    assert blocked._name(long_one) != blocked._name(long_two)
    assert blocked._name(long_one) == blocked._name(long_one)
    assert len(blocked._name(long_one).rsplit("-", 1)[1]) == 8

    # A drop is never nameless: an entry with no id gets a positional label, because a drop
    # nobody can trace is the filter hiding itself.
    _ledger(tmp_path, '[[stop]]\nwhat = "a gate"\n')
    assert blocked.stops(tmp_path) == ([], ["halt[0]"])

    # `docs/` is created. Most repositories installing the wheel do not have one, and without
    # this the whole of repair 2 is inert for them.
    fresh = tmp_path / "elsewhere"
    fresh.mkdir()
    blocked.record(fresh, what="a gate", why="a reason", action="run this", since="2026-08-19")
    assert (fresh / blocked.LEDGER).is_file()

    # The sibling the atomic write goes through is gone afterwards, whether or not the rename
    # happened. It sits in a committed directory and nothing gitignores it.
    assert not list((fresh / "docs").glob("*.writing"))


def test_a_write_that_fails_leaves_no_half_file_behind(tmp_path, monkeypatch):
    """The interrupted case, which is the reason the sibling exists at all. A lone surrogate
    from a shell argument fails at encode time, after the sibling has been opened."""

    (tmp_path / "docs").mkdir()
    blocked.record(tmp_path, what="first", why="a reason", action="run this", since="2026-08-19")

    with pytest.raises(UnicodeEncodeError):
        blocked.record(tmp_path, what="second", why="\udcff", action="run this", since="2026-08-19")

    assert not list((tmp_path / "docs").glob("*.writing"))
    rows, _ = blocked.stops(tmp_path)
    assert [row.what for row in rows] == ["first"], "the good file survived the failed write"


def test_a_rewrite_keeps_what_it_does_not_understand(tmp_path):
    """Two ways the rewrite was unfaithful. A key this version does not know was deleted by
    an unrelated halt, and a non-string field was laundered through `str()` into a row that
    read as whole — a dropped row promoted to a shown one carrying a Python repr."""

    _ledger(
        tmp_path,
        '[[stop]]\nid = "kept"\nwhat = "another gate"\nsince = "2026-08-01"\n'
        'why = "a reason"\naction = "run that"\nowner = "dachi"\nseverity = 3\n',
    )

    blocked.record(tmp_path, what="a gate", why="a reason", action="run this", since="2026-08-19")

    body = (tmp_path / blocked.LEDGER).read_text(encoding="utf-8")
    assert 'owner = "dachi"' in body, "a key this version does not know must survive"
    assert "severity = 3" in body

    # A shape this writer cannot reproduce refuses the whole write rather than laundering it.
    _ledger(tmp_path, '[[stop]]\nid = "odd"\nwhat = "a gate"\naction = ["a"]\n')
    with pytest.raises(blocked.Unreadable):
        blocked.record(
            tmp_path, what="new gate", why="a reason", action="run this", since="2026-08-19"
        )


def test_the_placeholder_check_reads_spanish_too(tmp_path):
    """`pending` was refused and `pendiente` was not, in a repository whose approval literals
    are Spanish. And four alternatives carried no word boundary, so `todo` matched "Todos los
    gates" — which meant a halting run could not record its own stop."""

    for useless in ("pendiente", "por decidir", "sin decidir", "?", "???", "-", "...", "WIP"):
        assert blocked.usable(useless) == "", useless

    for real in (
        "apruebo 020 en 1a36b114",
        "Todos los gates de 020 estan rojos",
        "decide-gate --approve 020",
        "figure-out.sh --run",
        "ask-owner.sh --escalate",
    ):
        assert blocked.usable(real) == real, real


def test_a_falsy_stop_key_is_unreadable_rather_than_empty(tmp_path):
    """`stop = false` is valid TOML of the wrong shape. Coalesced to an empty list it
    answered "nothing is stuck" over a ledger nobody could read."""

    for shape in ("stop = false\n", "stop = 0\n", 'stop = ""\n'):
        _ledger(tmp_path, shape)
        with pytest.raises(blocked.Unreadable):
            blocked.stops(tmp_path)
