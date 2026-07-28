"""spec-148 P1: token rollups computed directly from framework-events.ndjson.

Replaces the SQLite `skill/agent/session_token_rollup` views (audit_index)
with pure NDJSON scans. Semantics MUST match the retired views:

* skill_token_rollup  — kind='skill_invoked', GROUP BY detail.skill
* agent_token_rollup  — kind='agent_dispatched', GROUP BY detail.agent
* session_token_rollup — GROUP BY sessionId (non-null), MIN/MAX timestamp

Token fields live at detail.genai.usage.{input,output,total}_tokens + cost_usd.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.audit_rollup import (
    agent_token_rollup,
    session_token_rollup,
    skill_token_rollup,
)


def _usage(inp: int, out: int, total: int, cost: float, system: str | None = None) -> dict:
    genai: dict = {
        "usage": {
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": total,
            "cost_usd": cost,
        }
    }
    if system is not None:
        genai["system"] = system
    return {"genai": genai}


def _write(path: Path, events: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _ndjson(tmp_path: Path) -> Path:
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            {
                "kind": "skill_invoked",
                "timestamp": "2026-05-21T10:00:00Z",
                "sessionId": "s1",
                "detail": {"skill": "ai-plan", **_usage(100, 50, 150, 0.01)},
            },
            {
                "kind": "skill_invoked",
                "timestamp": "2026-05-21T10:01:00Z",
                "sessionId": "s1",
                "detail": {"skill": "ai-plan", **_usage(200, 60, 260, 0.02)},
            },
            {
                "kind": "skill_invoked",
                "timestamp": "2026-05-21T10:02:00Z",
                "sessionId": "s2",
                "detail": {"skill": "ai-build", **_usage(10, 5, 15, 0.001)},
            },
            {
                "kind": "agent_dispatched",
                "timestamp": "2026-05-21T10:03:00Z",
                "sessionId": "s2",
                "detail": {"agent": "ai-explore", **_usage(300, 100, 400, 0.05)},
            },
            {
                "kind": "git_hook",
                "timestamp": "2026-05-21T10:04:00Z",
                "sessionId": "s2",
                "detail": {"checks": {}},
            },  # no tokens, not skill/agent
        ],
    )
    return p


def test_skill_rollup_groups_and_sums(tmp_path: Path) -> None:
    rows = {r["skill"]: r for r in skill_token_rollup(_ndjson(tmp_path))}
    assert rows["ai-plan"]["invocations"] == 2
    assert rows["ai-plan"]["input_tokens"] == 300
    assert rows["ai-plan"]["output_tokens"] == 110
    assert rows["ai-plan"]["total_tokens"] == 410
    assert abs(rows["ai-plan"]["cost_usd"] - 0.03) < 1e-9
    assert rows["ai-build"]["invocations"] == 1
    assert "ai-explore" not in rows  # agent_dispatched excluded from skill rollup


def test_agent_rollup_groups_and_sums(tmp_path: Path) -> None:
    rows = {r["agent"]: r for r in agent_token_rollup(_ndjson(tmp_path))}
    assert rows["ai-explore"]["dispatches"] == 1
    assert rows["ai-explore"]["total_tokens"] == 400
    assert "ai-plan" not in rows  # skill_invoked excluded


def test_session_rollup_min_max_and_sums(tmp_path: Path) -> None:
    rows = {r["session_id"]: r for r in session_token_rollup(_ndjson(tmp_path))}
    assert rows["s1"]["events"] == 2
    assert rows["s1"]["started_at"] == "2026-05-21T10:00:00Z"
    assert rows["s1"]["ended_at"] == "2026-05-21T10:01:00Z"
    assert rows["s1"]["total_tokens"] == 410
    # s2 has 3 events (2 with tokens, 1 git_hook with none)
    assert rows["s2"]["events"] == 3
    assert rows["s2"]["total_tokens"] == 415


# ---------------------------------------------------------------------------
# spec-201 sub-003: summary/member de-duplication + the genai_system column
# ---------------------------------------------------------------------------


def _member(sid: str, ts: str, *, tokens: tuple[int, int, int], cost: float, system=None) -> dict:
    inp, out, total = tokens
    return {
        "kind": "skill_invoked",
        "timestamp": ts,
        "sessionId": sid,
        "detail": {"skill": "ai-plan", **_usage(inp, out, total, cost, system)},
    }


def _summary(sid: str, ts: str, *, tokens: tuple[int, int, int], cost: float, system=None) -> dict:
    """The ``session_token_rollup`` event ``runtime-stop.py`` now emits.

    It restates the whole session, so it must NOT be added to the members it
    summarises.
    """
    inp, out, total = tokens
    return {
        "kind": "framework_operation",
        "timestamp": ts,
        "sessionId": sid,
        "detail": {
            "operation": "session_token_rollup",
            "session_id": sid,
            **_usage(inp, out, total, cost, system),
        },
    }


def test_session_summary_does_not_double_count_members(tmp_path: Path) -> None:
    """A summary restating its members reports 410, not 820.

    Invisible today (no live event carries a genai block) and a silent 2x
    overstatement the moment per-call usage starts shipping -- which is an
    explicit goal of this same spec. Same max-merge rule the emitter uses.
    """
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _member("s1", "2026-05-21T10:00:00Z", tokens=(100, 50, 150), cost=0.01),
            _member("s1", "2026-05-21T10:01:00Z", tokens=(200, 60, 260), cost=0.02),
            _summary("s1", "2026-05-21T10:02:00Z", tokens=(300, 110, 410), cost=0.03),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert row["total_tokens"] == 410
    assert row["input_tokens"] == 300
    assert row["output_tokens"] == 110


def test_repeated_session_summaries_report_the_last_total_not_their_sum(
    tmp_path: Path,
) -> None:
    """N summaries per session are a monotone cumulative series, not N sessions.

    ``runtime-stop.py`` emits one ``session_token_rollup`` per turn and each
    restates the session's *cumulative* total. Summing them reported the sum of
    the series instead of its maximum — an overstatement that grows with turn
    count and multiplies any reported cost by the same factor (spec-201 B1).
    Every pre-existing summary test used exactly ONE summary, which is why the
    bug shipped; this one uses four, matching the live evidence for session
    ``69b84fb2`` (``[170922, 189500, 360422, 720844]`` reported as 1441688).
    """
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _summary("s1", "2026-05-21T10:00:00Z", tokens=(120000, 50922, 170922), cost=0.10),
            _summary("s1", "2026-05-21T10:01:00Z", tokens=(130000, 59500, 189500), cost=0.20),
            _summary("s1", "2026-05-21T10:02:00Z", tokens=(250000, 110422, 360422), cost=0.40),
            _summary("s1", "2026-05-21T10:03:00Z", tokens=(500000, 220844, 720844), cost=0.80),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert row["total_tokens"] == 720844, "the cumulative total, not the sum of the series"
    assert row["input_tokens"] == 500000
    assert row["output_tokens"] == 220844
    assert abs(row["cost_usd"] - 0.80) < 1e-9, "dollars inherit the same multiplier"


def test_repeated_summaries_still_never_undercount_members(tmp_path: Path) -> None:
    """MAX over summaries must not shadow members that carry more usage."""
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _member("s1", "2026-05-21T10:00:00Z", tokens=(400, 200, 600), cost=0.05),
            _member("s1", "2026-05-21T10:01:00Z", tokens=(400, 200, 600), cost=0.05),
            _summary("s1", "2026-05-21T10:02:00Z", tokens=(100, 50, 150), cost=0.01),
            _summary("s1", "2026-05-21T10:03:00Z", tokens=(200, 100, 300), cost=0.02),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert row["total_tokens"] == 1200  # member sum wins over summary max
    assert abs(row["cost_usd"] - 0.10) < 1e-9


def test_session_summary_cost_is_max_not_sum(tmp_path: Path) -> None:
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _member("s1", "2026-05-21T10:00:00Z", tokens=(100, 50, 150), cost=0.01),
            _member("s1", "2026-05-21T10:01:00Z", tokens=(200, 60, 260), cost=0.02),
            _summary("s1", "2026-05-21T10:02:00Z", tokens=(300, 110, 410), cost=0.03),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert abs(row["cost_usd"] - 0.03) < 1e-9


def test_session_summary_wins_when_members_carry_nothing(tmp_path: Path) -> None:
    """The live case: members have no usage at all, the summary has the truth."""
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            {
                "kind": "ide_hook",
                "timestamp": "2026-05-21T10:00:00Z",
                "sessionId": "s9",
                "detail": {"event": "Stop"},
            },
            _summary("s9", "2026-05-21T10:05:00Z", tokens=(41, 17870, 17911), cost=0.42),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s9"]

    assert row["total_tokens"] == 17911
    assert abs(row["cost_usd"] - 0.42) < 1e-9
    assert row["events"] == 2


def test_session_events_count_includes_the_summary(tmp_path: Path) -> None:
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _member("s1", "2026-05-21T10:00:00Z", tokens=(100, 50, 150), cost=0.01),
            _summary("s1", "2026-05-21T10:02:00Z", tokens=(100, 50, 150), cost=0.01),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert row["events"] == 2
    assert row["started_at"] == "2026-05-21T10:00:00Z"
    assert row["ended_at"] == "2026-05-21T10:02:00Z"


def test_session_genai_system_column_single_driver(tmp_path: Path) -> None:
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _member("s1", "2026-05-21T10:00:00Z", tokens=(1, 1, 2), cost=0.0, system="anthropic"),
            _member("s1", "2026-05-21T10:01:00Z", tokens=(1, 1, 2), cost=0.0, system="anthropic"),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert row["genai_system"] == "anthropic"


def test_session_genai_system_column_multi_driver(tmp_path: Path) -> None:
    """Subagents on different models are real; one value would hide a driver."""
    p = tmp_path / "framework-events.ndjson"
    _write(
        p,
        [
            _member("s1", "2026-05-21T10:00:00Z", tokens=(1, 1, 2), cost=0.0, system="openai"),
            _member("s1", "2026-05-21T10:01:00Z", tokens=(1, 1, 2), cost=0.0, system="anthropic"),
            _member("s1", "2026-05-21T10:02:00Z", tokens=(1, 1, 2), cost=0.0, system="openai"),
        ],
    )

    row = {r["session_id"]: r for r in session_token_rollup(p)}["s1"]

    assert row["genai_system"] == "anthropic,openai"


def test_session_genai_system_empty_when_no_system_reported(tmp_path: Path) -> None:
    rows = {r["session_id"]: r for r in session_token_rollup(_ndjson(tmp_path))}
    assert rows["s1"]["genai_system"] == ""


def test_session_row_key_order_appends_genai_system_last(tmp_path: Path) -> None:
    """``audit_cmd`` derives CLI columns from ``rows[0].keys()`` -- order is wire."""
    rows = session_token_rollup(_ndjson(tmp_path))
    assert list(rows[0].keys()) == [
        "session_id",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cost_usd",
        "events",
        "started_at",
        "ended_at",
        "genai_system",
    ]


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "nope.ndjson"
    assert skill_token_rollup(missing) == []
    assert agent_token_rollup(missing) == []
    assert session_token_rollup(missing) == []


def test_malformed_line_skipped_not_fatal(tmp_path: Path) -> None:
    p = tmp_path / "framework-events.ndjson"
    p.write_text(
        json.dumps(
            {
                "kind": "skill_invoked",
                "timestamp": "t",
                "detail": {"skill": "ai-x", **_usage(1, 1, 2, 0.0)},
            }
        )
        + "\nnot json\n",
        encoding="utf-8",
    )
    rows = skill_token_rollup(p)
    assert len(rows) == 1 and rows[0]["skill"] == "ai-x"
