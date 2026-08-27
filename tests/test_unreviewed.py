"""The derivation, and the one way it must not be generous.

`PO-04` asks that a task checkpoint be labelled unreviewed. The approved plan forbids the
obvious implementation in as many words — "a commit message, model statement, test label, or
metadata field cannot turn it into approval" — so the label is derived from the block
hand-offs, and the only interesting failure is the derivation crediting a review that did not
happen.

There is one way that happens and it is silent: a range whose ends this clone cannot resolve.
`git rev-list nonexistent..HEAD` prints nothing, but `git rev-list ..HEAD` prints the whole
history, and a base that resolves to nothing is one typo away from the second. Every commit
would then read as reviewed by a block that reviewed none of them, and the report would be at
its most reassuring exactly when it knew least.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import unreviewed  # noqa: E402 — the reader under test, beside this file


def test_the_hand_offs_are_read_from_the_record_and_not_written_here():
    """Three closed blocks, each naming a base and a final HEAD. A second list of ranges in
    this file would be a second place for them to disagree with the audit."""

    found = unreviewed.blocks()

    assert len(found) >= 3, f"{found} — three blocks have closed and each names both ends"
    for name, base, head, looked in found:
        assert name
        assert base
        assert head, (name, base, head)
        assert looked, f"Block {name}'s hand-off names no reviewer"


def test_a_range_this_clone_cannot_resolve_credits_nothing(monkeypatch):
    """The silent generosity. An unresolvable base must contribute no commits at all, never
    the whole history — a report that credits every commit to a review nobody ran is worse
    than no report, because it is confident."""

    monkeypatch.setattr(unreviewed, "blocks", lambda: [("Ghost", "0" * 40, "0" * 40, True)])

    assert unreviewed.reviewed() == set()


def test_a_missing_audit_leaves_every_commit_unreviewed(monkeypatch, tmp_path):
    """Absence is not approval. Delete the record and nothing is reviewed, which is the
    honest reading — not "no blocks are recorded, so nothing needed one"."""

    monkeypatch.setattr(unreviewed, "AUDIT", tmp_path / "gone.md")

    assert unreviewed.blocks() == []
    assert unreviewed.reviewed() == set()


def test_a_hand_off_that_names_no_reviewer_credits_nothing(monkeypatch, capsys):
    """The loophole this opened and had to close in the same commit.

    Writing a hand-off is typing a table. If the derivation credited every table, anybody
    could clear this whole report by adding one — a range would read as reviewed because a
    document said a block closed there, which is the exact substitution of a record for the
    thing it records that this repository keeps finding.

    So the reviewer's own row decides. "none", "pending" and an empty cell are all somebody
    saying nobody looked, and a block is credited only where the disposition says a person
    found something or found nothing.
    """

    real = unreviewed.blocks()[0]
    monkeypatch.setattr(unreviewed, "blocks", lambda: [(real[0], real[1], real[2], False)])

    assert unreviewed.reviewed() == set()
    assert "names no reviewer" in capsys.readouterr().out


def test_the_words_for_nobody_having_looked_include_the_empty_cell():
    """An empty cell is the most likely way this arrives: a table copied from another block
    with the row left to fill in. It must read as nobody, not as an answer nobody parsed."""

    assert "" in unreviewed.NOBODY
    assert "none" in unreviewed.NOBODY
    assert "pending" in unreviewed.NOBODY
