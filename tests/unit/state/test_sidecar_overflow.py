"""Sidecar offload tests (spec-122-b T-2.7)."""

from __future__ import annotations

import json

from ai_engineering.state.sidecar import (
    SIDECAR_CEILING_BYTES,
    maybe_offload,
)


def test_ceiling_constant_is_3kb():
    """Spec D-122-23 fixes the ceiling at 3 KB."""
    assert SIDECAR_CEILING_BYTES == 3072


def test_small_event_passes_through(tmp_path):
    """Events under the ceiling are returned unchanged."""
    event = {
        "kind": "skill_invoked",
        "engine": "ai_engineering",
        "component": "test",
        "outcome": "success",
        "timestamp": "2026-05-05T00:00:00Z",
        "detail": {"skill": "ai-plan"},
    }
    result = maybe_offload(event, project_root=tmp_path)
    assert result is event
    sidecar_dir = tmp_path / ".ai-engineering" / "state" / "runtime" / "event-sidecars"
    assert not sidecar_dir.exists() or not list(sidecar_dir.iterdir())


def test_large_event_offloaded(tmp_path):
    """Events over the ceiling get hashed + offloaded; inline carries hash."""
    big_payload = "X" * 5000
    event = {
        "kind": "tool_call",
        "engine": "ai_engineering",
        "component": "claude_code",
        "outcome": "success",
        "timestamp": "2026-05-05T00:00:00Z",
        "detail": {"tool": "Bash", "raw_output": big_payload},
    }
    result = maybe_offload(event, project_root=tmp_path)

    assert "sidecar_sha256" in result
    assert "summary" in result
    assert len(json.dumps(result)) < SIDECAR_CEILING_BYTES

    sidecar_path = (
        tmp_path
        / ".ai-engineering"
        / "state"
        / "runtime"
        / "event-sidecars"
        / f"{result['sidecar_sha256']}.json"
    )
    assert sidecar_path.exists()
    payload = json.loads(sidecar_path.read_text())
    assert payload["detail"]["raw_output"] == big_payload


def test_deterministic_hash(tmp_path):
    """Same input -> same sidecar path (content-addressed)."""
    big_payload = "Y" * 4000
    event = {
        "kind": "tool_call",
        "engine": "ai_engineering",
        "component": "claude_code",
        "outcome": "success",
        "timestamp": "2026-05-05T00:00:00Z",
        "detail": {"tool": "Bash", "raw_output": big_payload},
    }
    a = maybe_offload(event, project_root=tmp_path)
    b = maybe_offload(event, project_root=tmp_path)
    assert a["sidecar_sha256"] == b["sidecar_sha256"]


def test_collision_safe(tmp_path):
    """Re-offloading the same event does not re-write the sidecar file."""
    big_payload = "Z" * 4000
    event = {
        "kind": "tool_call",
        "engine": "ai_engineering",
        "component": "claude_code",
        "outcome": "success",
        "timestamp": "2026-05-05T00:00:00Z",
        "detail": {"tool": "Bash", "raw_output": big_payload},
    }
    a = maybe_offload(event, project_root=tmp_path)
    sidecar_path = (
        tmp_path
        / ".ai-engineering"
        / "state"
        / "runtime"
        / "event-sidecars"
        / f"{a['sidecar_sha256']}.json"
    )
    mtime_before = sidecar_path.stat().st_mtime_ns
    # Idempotent re-call
    b = maybe_offload(event, project_root=tmp_path)
    assert b["sidecar_sha256"] == a["sidecar_sha256"]
    mtime_after = sidecar_path.stat().st_mtime_ns
    assert mtime_before == mtime_after, "sidecar must not be re-written"
