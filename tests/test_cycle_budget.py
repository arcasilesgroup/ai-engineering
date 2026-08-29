"""Tests for spec 047: the wall budgets, the critic boxes, the vitals arithmetic.

Red on purpose at landing (task 2): the five critic skills do not yet carry their box,
and `src/ai_engineering/vitals.py` does not exist yet. The plan's check is
`--collect-only`, which proves the shape; the run proves the absence. Every import of a
not-yet-written module lives inside a test body so collection never dies on an ImportError
wearing a red.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_engineering import contract

ROOT = Path(__file__).resolve().parents[1]

CRITICS = (
    "ai-challenge",
    "ai-council",
    "ai-review",
    "ai-verify",
    "ai-security",
)


def _line(session: str, cls: str, at: datetime) -> str:
    return json.dumps({"session": session, "cls": cls, "ts": at.isoformat()})


def _stream(session: str, minutes: float, gap_cls: str = "blocked") -> str:
    """One session's events: a start, one long `gap_cls` span, an end `minutes` later."""
    t0 = datetime(2026, 8, 29, 0, 0, 0, tzinfo=UTC)
    lines = [
        _line(session, "command", t0),
        _line(session, gap_cls, t0 + timedelta(minutes=1)),
        _line(session, "command", t0 + timedelta(minutes=minutes)),
    ]
    return "\n".join(lines) + "\n"


def test_the_budgets_live_in_contract_and_nowhere_else():
    assert contract.CYCLE_WALL_BUDGET_MINUTES == 180
    assert contract.CRITIC_TIMEBOX_MINUTES == 40
    assert contract.CRITIC_CALLS_MAX == 120
    # one home: the skills name the numbers, they never re-derive them
    body = (ROOT / ".agents" / "skills" / "ai-goal" / "SKILL.md").read_text(encoding="utf-8")
    assert "180" not in body or "contract" in body

def test_timebox_pins():
    """(a) each critic skill carries the box: both numbers and the TIMEBOXED exit."""
    for name in CRITICS:
        body = (ROOT / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert str(contract.CRITIC_TIMEBOX_MINUTES) in body, f"{name} names no timebox"
        assert str(contract.CRITIC_CALLS_MAX) in body, f"{name} names no call bound"
        assert "TIMEBOXED" in body, f"{name} has no bounded exit"


def test_vitals_attributes_minutes_between_ts_stamps():
    """(b) a two-hour stream: wall time first-to-last ts, minutes per earlier cls."""
    from ai_engineering import vitals

    raw = _stream("s1", 120.0)
    seen = vitals.read(raw, "s1")
    assert seen["wall_minutes"] == 120.0
    assert seen["by_cls"]["blocked"] == 119.0
    assert seen["by_cls"]["command"] == 1.0


def test_budget_over_ceiling_is_incomplete_naming_the_largest_bucket():
    """(c) 200 minutes: INCOMPLETE, OVER_BUDGET, and the stall it points at."""
    from ai_engineering import vitals

    verdict = vitals.verdict(_stream("s2", 200.0, "blocked"), "s2")
    assert verdict["outcome"] == "INCOMPLETE"
    assert verdict["code"] == "OVER_BUDGET"
    assert verdict["largest"] == "blocked"


def test_budget_inside_ceiling_passes():
    """(d) 90 minutes: PASS — arithmetic, never an approval of the work."""
    from ai_engineering import vitals

    verdict = vitals.verdict(_stream("s3", 90.0), "s3")
    assert verdict["outcome"] == "PASS"
    assert verdict["wall_minutes"] == 90.0


def test_no_session_match_refuses_rather_than_passing_on_emptiness():
    """(e) an empty read is a finding, not a green."""
    from ai_engineering import vitals

    verdict = vitals.verdict(_stream("s4", 10.0), "someone-else")
    assert verdict["outcome"] == "INCOMPLETE"
    assert verdict["code"] == "NO_DATA"



def test_the_verb_reads_the_in_clone_record(tmp_path, monkeypatch):
    """`ai-eng report vitals` dispatches, reads `.ai/events.jsonl`, exits on the verdict.

    Hermetic on purpose: the plan's first check tried a shell substitution `--tick`
    cannot run without a shell, over a file CI does not have. A tmp root with a two-
    line record is the same command the verb runs in production.
    """

    from ai_engineering import paths, report

    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai" / "events.jsonl").write_text(_stream("s9", 10.0), encoding="utf-8")
    result = report.main(["vitals", "--session", "s9"])
    assert result.outcome == "PASS"
    result_over = report.main(["vitals", "--session", "nobody"])
    assert result_over.outcome == "INCOMPLETE"


def test_goal_and_build_name_the_anti_stall_and_the_batch_rule():
    """(7) the unattended cycle never waits, and one red never relaunches the gate."""

    goal = (ROOT / ".agents" / "skills" / "ai-goal" / "SKILL.md").read_text(encoding="utf-8")
    build = (ROOT / ".agents" / "skills" / "ai-build" / "SKILL.md").read_text(encoding="utf-8")
    assert "BLOCKED:" in goal, "ai-goal closes a blocked turn with no named unblock"
    assert "TIMEBOXED" in goal, "ai-goal never names the bounded fork exit"
    assert "just check-all" in goal and "report vitals" in goal, (
        "ai-goal's close prints neither the batched gate nor the wall reading"
    )
    assert "just check-all" in build, "ai-build still relaunches the whole gate per red"