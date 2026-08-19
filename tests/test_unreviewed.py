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
    for name, base, head in found:
        assert name and base and head, (name, base, head)


def test_a_range_this_clone_cannot_resolve_credits_nothing(monkeypatch):
    """The silent generosity. An unresolvable base must contribute no commits at all, never
    the whole history — a report that credits every commit to a review nobody ran is worse
    than no report, because it is confident."""

    monkeypatch.setattr(unreviewed, "blocks", lambda: [("Ghost", "0" * 40, "0" * 40)])

    assert unreviewed.reviewed() == set()


def test_a_missing_audit_leaves_every_commit_unreviewed(monkeypatch, tmp_path):
    """Absence is not approval. Delete the record and nothing is reviewed, which is the
    honest reading — not "no blocks are recorded, so nothing needed one"."""

    monkeypatch.setattr(unreviewed, "AUDIT", tmp_path / "gone.md")

    assert unreviewed.blocks() == []
    assert unreviewed.reviewed() == set()
