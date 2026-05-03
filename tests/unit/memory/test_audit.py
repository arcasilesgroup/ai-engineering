"""spec-118 T-2.6 -- memory_event audit emission."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.memory


def _read_events(project_root):
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def test_emit_episode_stored_writes_one_event(memory_project):
    from memory import audit

    audit.emit_episode_stored(
        memory_project,
        episode_id="ep-1",
        embedding_status="pending",
        duration_ms=42,
        source="hook",
    )
    events = _read_events(memory_project)
    assert len(events) == 1
    e = events[0]
    assert e["kind"] == "memory_event"
    assert e["component"] == "memory"
    assert e["source"] == "hook"
    assert e["detail"]["operation"] == "episode_stored"
    assert e["detail"]["episode_id"] == "ep-1"
    assert e["detail"]["embedding_status"] == "pending"


def test_emit_rejects_unknown_source(memory_project):
    from memory import audit

    with pytest.raises(ValueError, match="memory.audit.emit refuses"):
        audit.emit(
            memory_project,
            operation=audit.Operation.EPISODE_STORED,
            source="bogus",
        )


def test_emit_dream_run_carries_metrics(memory_project):
    from memory import audit

    audit.emit_dream_run(
        memory_project,
        decay_factor=0.97,
        clusters_found=4,
        promoted_count=1,
        retired_count=2,
        duration_ms=1234,
        outcome="ok",
    )
    events = _read_events(memory_project)
    assert events[-1]["detail"]["operation"] == "dream_run"
    assert events[-1]["detail"]["clusters_found"] == 4
    assert events[-1]["detail"]["outcome"] == "ok"


def test_hash_chain_intact(memory_project):
    from memory import audit

    audit.emit_episode_stored(
        memory_project,
        episode_id="ep-a",
        embedding_status="complete",
        duration_ms=10,
        source="hook",
    )
    audit.emit_episode_stored(
        memory_project,
        episode_id="ep-b",
        embedding_status="complete",
        duration_ms=10,
        source="hook",
    )
    events = _read_events(memory_project)
    assert "prev_event_hash" in events[1]
    # First record gets a None or empty pointer (anchor); second must reference prior.
    assert events[1]["prev_event_hash"] is not None
