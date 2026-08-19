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
