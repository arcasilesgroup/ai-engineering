"""The reader for Task 53's live half, and the two answers it must keep apart.

`specs/010/plan.md` reserves the shipped transition until both workflows are complete and
successful at exactly the candidate's own HEAD. The reason P0 sits in `draft` was recorded as
those lanes being red for reasons the branch could not resolve from inside — true when
written, and untrue for a day before anything re-measured it.

Nothing here decides that transition. What is held is the reader: a run that has not finished
is not a pass, and a machine that could not ask is not a failure. Both are ways this could
report a green nobody earned, and they arrive from opposite directions.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import own_head_receipts  # noqa: E402 — the reader under test, beside this file


def _row(sha: str, workflow: str, status: str = "completed", conclusion: str = "success") -> dict:
    return {
        "headSha": sha,
        "workflowName": workflow,
        "status": status,
        "conclusion": conclusion,
    }


def test_a_commit_needs_every_required_workflow_and_not_just_one():
    """One green lane is half a proof and reads exactly like a whole one in a list."""

    one = [_row("a" * 40, "check")]
    both = [_row("a" * 40, "check"), _row("a" * 40, "install")]

    assert own_head_receipts.proven(one) == {}
    assert set(own_head_receipts.proven(both)) == {"a" * 40}


def test_a_run_that_has_not_finished_is_not_a_pass():
    """`status` is asked before `conclusion` because a cancelled run carries no conclusion and
    an in-flight one has none yet. Reading the conclusion alone makes both absent rather than
    unfinished, and absent is what a commit with no run at all looks like."""

    for status, conclusion in (("in_progress", ""), ("completed", "cancelled"), ("queued", "")):
        rows = [_row("b" * 40, "check", status, conclusion), _row("b" * 40, "install")]
        assert own_head_receipts.proven(rows) == {}, (status, conclusion)


def test_a_run_at_another_commit_proves_nothing_about_this_one():
    """The whole point of the word *exact*. A green run on the commit before is the strongest
    thing there is that is still not evidence about these bytes."""

    rows = [_row("c" * 40, "check"), _row("d" * 40, "install")]

    assert own_head_receipts.proven(rows) == {}


def test_a_machine_that_could_not_ask_says_so_rather_than_reporting_none(capsys, monkeypatch):
    """Absence of an answer and an answer of none are opposite facts. Without this, a laptop
    with no `gh` would report that no commit has receipts, which reads as a finding about the
    branch and is a finding about the laptop."""

    monkeypatch.setattr(own_head_receipts, "runs", lambda branch, limit: [])

    own_head_receipts.main([])

    printed = capsys.readouterr().out
    assert "UNDECIDED" in printed
    assert "absence is not an answer" in printed
