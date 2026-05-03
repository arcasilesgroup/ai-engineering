"""spec-118 T-5.4 -- end-to-end Stop -> SessionStart round-trip."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Inject the canonical scripts dir so `import memory` works from tests.
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / ".ai-engineering" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

pytestmark = [pytest.mark.memory, pytest.mark.integration]


@pytest.fixture
def integration_project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "runtime").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "instincts").mkdir(parents=True)
    return tmp_path


def _seed_session_events(project_root: Path, session_id: str, count: int = 3) -> None:
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    rows = []
    for i in range(count):
        rows.append(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "timestamp": f"2026-05-01T10:{i:02d}:00Z",
                    "engine": "claude_code",
                    "kind": "skill_invoked",
                    "outcome": "success",
                    "component": "skill",
                    "correlationId": f"corr-{i}",
                    "detail": {"skill": f"ai-test-{i}"},
                    "sessionId": session_id,
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(rows) + "\n")


def test_episode_writer_round_trip(integration_project: Path) -> None:
    from memory import episodic, store

    sid = "session-integration-1"
    _seed_session_events(integration_project, sid)

    row = episodic.write_episode(integration_project, session_id=sid)
    assert row is not None
    assert row.session_id == sid
    assert "ai-test-0" in row.summary

    with store.connect(integration_project) as conn:
        episodes = conn.execute("SELECT episode_id, summary FROM episodes").fetchall()
    assert len(episodes) == 1
    assert episodes[0]["summary"] == row.summary


def test_audit_chain_records_episode_stored(integration_project: Path) -> None:
    from memory import audit, episodic

    sid = "session-integration-2"
    _seed_session_events(integration_project, sid)
    row = episodic.write_episode(integration_project, session_id=sid)
    assert row is not None
    audit.emit_episode_stored(
        integration_project,
        episode_id=row.episode_id,
        embedding_status="pending",
        duration_ms=15,
        source="hook",
        session_id=sid,
    )
    events_path = integration_project / ".ai-engineering" / "state" / "framework-events.ndjson"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1])
    assert last["kind"] == "memory_event"
    assert last["detail"]["operation"] == "episode_stored"
    assert last["detail"]["episode_id"] == row.episode_id


def test_ingest_then_status_round_trip(integration_project: Path) -> None:
    from memory import knowledge, store

    store.bootstrap(integration_project)

    lessons = integration_project / ".ai-engineering" / "LESSONS.md"
    lessons.write_text("## A\n\nbody A.\n\n## B\n\nbody B.\n", encoding="utf-8")

    decisions = integration_project / ".ai-engineering" / "state" / "decision-store.json"
    decisions.write_text(
        json.dumps(
            {
                "decisions": [
                    {"id": "DEC-001", "title": "t", "description": "d", "status": "active"},
                ]
            }
        )
    )

    with store.connect(integration_project) as conn:
        counts = knowledge.ingest_all(conn, integration_project)
        conn.commit()
    assert counts["lesson"] == 2
    assert counts["decision"] == 1
