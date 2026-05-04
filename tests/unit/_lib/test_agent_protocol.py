"""Tests for the A2A agent artifact protocol (P3.1 / 2026-05-04 gap closure).

The doctrine §72-78 mandate: every agent dispatch produces a
schema-bound artifact persisted under
``.ai-engineering/state/agent-artifacts/<run-id>.json``. These tests
pin the schema, the atomic-write semantics, and the trace_session
walker.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "agent_protocol.py"


@pytest.fixture(scope="module")
def proto_mod():
    sys.modules.pop("aieng_agent_protocol_test", None)
    spec = importlib.util.spec_from_file_location("aieng_agent_protocol_test", PROTOCOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_agent_protocol_test"] = module
    spec.loader.exec_module(module)
    return module


def _make_artifact(proto_mod, **overrides):
    base = {
        "run_id": proto_mod.new_run_id(),
        "agent_type": "ai-explore",
        "inputs": {"task": "scan repo"},
        "outputs": {"summary": "found 12 hooks"},
        "citations": ["1:50:CLAUDE.md"],
        "started_at": "2026-05-04T10:00:00Z",
        "ended_at": "2026-05-04T10:00:05Z",
        "status": "success",
    }
    base.update(overrides)
    return proto_mod.AgentArtifact(**base)


def test_write_and_load_round_trip(proto_mod, tmp_path: Path) -> None:
    artifact = _make_artifact(proto_mod)
    proto_mod.write_artifact(tmp_path, artifact)
    loaded = proto_mod.load_artifact(tmp_path, artifact.run_id)
    assert loaded is not None
    assert loaded.run_id == artifact.run_id
    assert loaded.agent_type == "ai-explore"
    assert loaded.outputs == {"summary": "found 12 hooks"}
    assert loaded.status == "success"


def test_invalid_status_raises(proto_mod, tmp_path: Path) -> None:
    artifact = _make_artifact(proto_mod, status="not-a-valid-status")
    with pytest.raises(ValueError, match="status must be one of"):
        proto_mod.write_artifact(tmp_path, artifact)


def test_load_returns_none_for_missing(proto_mod, tmp_path: Path) -> None:
    out = proto_mod.load_artifact(tmp_path, "nonexistent-run-id-xyz")
    assert out is None


def test_load_returns_none_for_malformed(proto_mod, tmp_path: Path) -> None:
    """A corrupt JSON file → None (not an exception)."""
    artifacts = proto_mod.artifacts_dir(tmp_path)
    bad = artifacts / "broken.json"
    bad.write_text("{not valid json", encoding="utf-8")
    out = proto_mod.load_artifact(tmp_path, "broken")
    assert out is None


def test_atomic_write_concurrent_writers(proto_mod, tmp_path: Path) -> None:
    """Two threads writing the same run_id → exactly one valid JSON wins."""
    run_id = proto_mod.new_run_id()
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def writer(suffix: str) -> None:
        try:
            barrier.wait(timeout=2)
            artifact = _make_artifact(
                proto_mod,
                run_id=run_id,
                outputs={"thread": suffix},
            )
            proto_mod.write_artifact(tmp_path, artifact)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=writer, args=("a",))
    t2 = threading.Thread(target=writer, args=("b",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not errors, f"writers failed: {errors}"

    loaded = proto_mod.load_artifact(tmp_path, run_id)
    assert loaded is not None
    assert loaded.outputs.get("thread") in ("a", "b"), (
        "loaded artifact should be one of the two writers' payloads"
    )

    # Only one persistent JSON file remains; tmp files were cleaned up.
    artifacts = proto_mod.artifacts_dir(tmp_path)
    json_files = list(artifacts.glob("*.json"))
    assert len(json_files) == 1
    tmp_files = list(artifacts.glob(".*.tmp"))
    assert tmp_files == [], f"tmp files leaked: {tmp_files}"


def test_trace_session_walks_by_session_id(proto_mod, tmp_path: Path) -> None:
    """Artifacts tagged with session_id in extras are returned in order."""
    sess_a = "session-aaa"
    sess_b = "session-bbb"

    a1 = _make_artifact(
        proto_mod,
        started_at="2026-05-04T10:00:01Z",
        extras={"session_id": sess_a},
    )
    a2 = _make_artifact(
        proto_mod,
        started_at="2026-05-04T10:00:03Z",
        extras={"session_id": sess_a},
    )
    b1 = _make_artifact(
        proto_mod,
        started_at="2026-05-04T10:00:02Z",
        extras={"session_id": sess_b},
    )
    for art in (a1, a2, b1):
        proto_mod.write_artifact(tmp_path, art)

    trace_a = proto_mod.trace_session(tmp_path, sess_a)
    assert [a.run_id for a in trace_a] == [a1.run_id, a2.run_id]
    trace_b = proto_mod.trace_session(tmp_path, sess_b)
    assert [a.run_id for a in trace_b] == [b1.run_id]


def test_nested_parent_run_id(proto_mod, tmp_path: Path) -> None:
    """Nested subagent dispatches preserve the parent_run_id chain."""
    parent = _make_artifact(proto_mod)
    proto_mod.write_artifact(tmp_path, parent)
    child = _make_artifact(proto_mod, parent_run_id=parent.run_id)
    proto_mod.write_artifact(tmp_path, child)

    loaded_child = proto_mod.load_artifact(tmp_path, child.run_id)
    assert loaded_child is not None
    assert loaded_child.parent_run_id == parent.run_id


def test_write_persists_jsonschema_compatible_dict(proto_mod, tmp_path: Path) -> None:
    """The on-disk JSON has stable, sorted keys for diffability."""
    artifact = _make_artifact(proto_mod)
    path = proto_mod.write_artifact(tmp_path, artifact)
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected_keys = {
        "run_id",
        "agent_type",
        "inputs",
        "outputs",
        "citations",
        "started_at",
        "ended_at",
        "status",
        "parent_run_id",
        "confidence",
        "extras",
    }
    assert set(raw.keys()) == expected_keys
