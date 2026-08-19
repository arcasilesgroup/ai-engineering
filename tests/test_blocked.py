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
    """Over this tree, with the numbers written down so a reader can re-derive them.

    Measured while specification 020 was planned: `docs/requirements.toml` holds 385 rows, of
    which 17 are BLOCKED or CONTRADICTED and all 17 carry both a note and an evidence command;
    eleven specifications are at `status: draft` and four of them have a `plan.md`. So 21 rows
    of 28 considered, and the seven dropped are drafts waiting on the build rather than on a
    person.

    The numbers are asserted as a relationship rather than as constants. A tree gains
    specifications, and a test that pinned 21 would go red for the right reason on the wrong
    day; what must hold is that everything considered is either shown or named as dropped, and
    that nothing is both.
    """

    shown, dropped = blocked.collect(ROOT)

    assert shown, "this tree has BLOCKED verdicts and unapproved drafts, so it is not empty"
    assert len(shown) + len(dropped) == blocked.considered(ROOT)
    assert not set(row.id for row in shown) & set(dropped)

    kinds = {row.kind for row in shown}
    assert kinds <= {"halt", "draft", "verdict"}, kinds

    # Stops first, then drafts, then verdicts: the question the section answers is what
    # unsticks the build, not what is worst.
    order = [row.kind for row in shown]
    assert order == sorted(order, key=["halt", "draft", "verdict"].index)

    for row in shown:
        for field in blocked.FIELDS:
            assert getattr(row, field).strip(), (row.id, field)

    # A draft's action names the digest of the file as it is on disk, so approving it cannot
    # silently approve a later edit.
    from hashlib import sha256

    for row in (one for one in shown if one.kind == "draft"):
        home = next((ROOT / "specs").glob(f"{row.id}-*"))
        digest = sha256((home / "spec.md").read_bytes()).hexdigest()
        assert digest[:12] in row.action, (row.id, row.action)


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
