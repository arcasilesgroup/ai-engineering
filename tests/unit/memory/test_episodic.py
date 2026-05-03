"""spec-118 T-2.6 -- episode build and persist round-trip."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.memory


def _seed_events(project_root, session_id, events):
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for e in events:
        e = dict(e)
        e.setdefault("sessionId", session_id)
        payload.append(json.dumps(e, sort_keys=True))
    path.write_text("\n".join(payload) + "\n")
    return path


def test_no_events_returns_none(memory_project):
    from memory import episodic

    row = episodic.build_episode(memory_project, session_id="missing")
    assert row is None


def test_event_aggregation(memory_project):
    from memory import episodic

    sid = "abcdef0123456789"
    _seed_events(
        memory_project,
        sid,
        [
            {
                "timestamp": "2026-04-01T10:00:00Z",
                "kind": "skill_invoked",
                "outcome": "success",
                "detail": {"skill": "ai-plan"},
            },
            {
                "timestamp": "2026-04-01T10:00:30Z",
                "kind": "agent_dispatched",
                "outcome": "success",
                "detail": {"agent": "ai-build"},
            },
            {
                "timestamp": "2026-04-01T10:01:00Z",
                "kind": "ide_hook",
                "outcome": "failure",
                "detail": {"tool": "Edit"},
            },
            {
                "timestamp": "2026-04-01T10:01:30Z",
                "kind": "ide_hook",
                "outcome": "success",
                "detail": {"tool": "Edit"},
            },
        ],
    )
    row = episodic.build_episode(memory_project, session_id=sid)
    assert row is not None
    assert row.session_id == sid
    assert row.duration_sec == 90
    assert "ai-plan" in row.skill_invocations
    assert "ai-build" in row.agents_dispatched
    assert row.tools_used.get("Edit") == 2
    assert row.outcomes.get("success") == 3
    assert row.outcomes.get("failure") == 1
    assert "skills=" in row.summary


def test_persistence_round_trip(memory_project):
    from memory import episodic, store

    sid = "session-x" * 4
    _seed_events(
        memory_project,
        sid,
        [
            {
                "timestamp": "2026-04-01T10:00:00Z",
                "kind": "skill_invoked",
                "outcome": "success",
                "detail": {"skill": "ai-plan"},
            },
        ],
    )
    row = episodic.write_episode(memory_project, session_id=sid)
    assert row is not None
    with store.connect(memory_project) as conn:
        cur = conn.execute("SELECT episode_id, session_id, summary FROM episodes")
        rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0]["session_id"] == sid
    assert "ai-plan" in rows[0]["summary"]


def test_plane_resolution_from_checkpoint(memory_project):
    from memory import episodic

    sid = "sid-plane-test"
    _seed_events(
        memory_project,
        sid,
        [
            {
                "timestamp": "2026-04-01T10:00:00Z",
                "kind": "skill_invoked",
                "outcome": "success",
                "detail": {"skill": "ai-plan"},
            },
        ],
    )
    checkpoint = memory_project / ".ai-engineering" / "state" / "runtime" / "checkpoint.json"
    checkpoint.write_text(json.dumps({"active_plane": "spec-118"}))
    row = episodic.build_episode(memory_project, session_id=sid)
    assert row is not None
    assert row.plane == "spec-118"
