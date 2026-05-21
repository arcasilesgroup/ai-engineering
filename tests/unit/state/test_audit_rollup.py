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


def _usage(inp: int, out: int, total: int, cost: float) -> dict:
    return {
        "genai": {
            "usage": {
                "input_tokens": inp,
                "output_tokens": out,
                "total_tokens": total,
                "cost_usd": cost,
            }
        }
    }


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
