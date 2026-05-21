"""Tests for the session token rollup wiring inside ``runtime-stop.py``
(spec-120 T-E1; spec-148 files-only).

Pins ``_emit_session_token_rollup`` against the append-only NDJSON audit
log (no SQLite). Best-effort contract:

1. **Session has NDJSON events** -> a single ``framework_operation`` event
   with ``detail.operation = "session_token_rollup"`` and the rollup payload.
2. **No events for the session_id** -> silent skip (no operation, no error).
3. **No NDJSON + no transcript** -> silent skip (nothing to roll up).
4. **session_id is None** -> silent skip.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _project_slug(project: Path) -> str:
    """Cross-OS Claude Code transcripts slug (mirrors ``_lib.transcript_usage``)."""
    return str(project.resolve()).replace("/", "-").replace("\\", "-").replace(":", "-")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rstop(monkeypatch: pytest.MonkeyPatch):
    """Load the runtime-stop module fresh in each test for monkey-safety."""
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_stop", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_stop", RUNTIME_STOP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _read_events(project_root: Path) -> list[dict]:
    path = project_root / NDJSON_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _seed_ndjson(project_root: Path, *, session_id: str, totals: dict) -> None:
    """Append one ``skill_invoked`` NDJSON event carrying a usage block.

    spec-148: the rollup is computed directly from this NDJSON, not a
    SQLite projection.
    """
    path = project_root / NDJSON_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-05-04T00:00:00Z",
        "component": "hook.telemetry-skill",
        "outcome": "success",
        "correlationId": "corr-1",
        "schemaVersion": "1.0",
        "project": "test",
        "spanId": "0123456789abcdef",
        "sessionId": session_id,
        "detail": {
            "skill": "ai-brainstorm",
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-opus-4.7"},
                "usage": {
                    "input_tokens": totals["input_tokens"],
                    "output_tokens": totals["output_tokens"],
                    "total_tokens": totals["total_tokens"],
                    "cost_usd": totals["cost_usd"],
                },
            },
        },
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# Branch 1: session has NDJSON events
# ---------------------------------------------------------------------------


def test_session_rollup_emits_framework_operation_when_events_found(rstop, project: Path) -> None:
    """Happy path: NDJSON has an event for the session -> one
    ``framework_operation`` event with the rollup payload."""
    session_id = "sess-happy"
    totals = {
        "input_tokens": 1000,
        "output_tokens": 250,
        "total_tokens": 1250,
        "cost_usd": 0.0125,
    }
    _seed_ndjson(project, session_id=session_id, totals=totals)

    rstop._emit_session_token_rollup(project, session_id=session_id, correlation_id="corr-test")

    events = _read_events(project)
    rollup_events = [
        e
        for e in events
        if e.get("kind") == "framework_operation"
        and (e.get("detail") or {}).get("operation") == "session_token_rollup"
    ]
    assert len(rollup_events) == 1, f"expected exactly one rollup event, got {events}"

    detail = rollup_events[0]["detail"]
    assert detail["operation"] == "session_token_rollup"
    assert detail["session_id"] == session_id
    assert detail["events"] == 1
    assert detail["input_tokens"] == 1000
    assert detail["output_tokens"] == 250
    assert detail["total_tokens"] == 1250
    assert detail["cost_usd"] == pytest.approx(0.0125)
    assert detail["started_at"] == "2026-05-04T00:00:00Z"
    assert detail["ended_at"] == "2026-05-04T00:00:00Z"
    assert rollup_events[0]["component"] == "hook.runtime-stop"
    assert rollup_events[0]["correlationId"] == "corr-test"


# ---------------------------------------------------------------------------
# Branch 2: NDJSON exists, no event for this session_id
# ---------------------------------------------------------------------------


def test_session_rollup_silent_skip_when_no_event_for_session(rstop, project: Path) -> None:
    """NDJSON has events for another session -> no event emitted at all
    (neither framework_operation nor framework_error)."""
    _seed_ndjson(
        project,
        session_id="sess-other",
        totals={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "cost_usd": 0.0},
    )

    rstop._emit_session_token_rollup(project, session_id="sess-missing", correlation_id="corr-test")

    events = _read_events(project)
    rollup_kinds = {(e.get("kind"), (e.get("detail") or {}).get("operation")) for e in events}
    assert ("framework_operation", "session_token_rollup") not in rollup_kinds
    assert not any(
        e.get("kind") == "framework_error"
        and (e.get("detail") or {}).get("error_code") == "session_rollup_skipped"
        for e in events
    )


# ---------------------------------------------------------------------------
# Branch 3: no NDJSON + no transcript -> silent skip (spec-148 change)
# ---------------------------------------------------------------------------


def test_session_rollup_silent_when_no_ndjson_and_no_transcript(rstop, project: Path) -> None:
    """spec-148: no NDJSON (and no transcript) -> nothing to roll up; the
    hook stays silent (no framework_operation, no framework_error). This
    replaces the old SQLite-missing -> framework_error behavior; an empty
    repo simply has no events to summarise."""
    assert not (project / NDJSON_REL).exists()

    rstop._emit_session_token_rollup(
        project, session_id="sess-no-events", correlation_id="corr-test"
    )

    events = _read_events(project)
    assert not any(
        e.get("kind") == "framework_operation"
        and (e.get("detail") or {}).get("operation") == "session_token_rollup"
        for e in events
    )
    assert not any(
        e.get("kind") == "framework_error"
        and (e.get("detail") or {}).get("error_code") == "session_rollup_skipped"
        for e in events
    )


# ---------------------------------------------------------------------------
# Branch 4: session_id is None -> silent
# ---------------------------------------------------------------------------


def test_session_rollup_silent_when_session_id_missing(rstop, project: Path) -> None:
    """No session_id from the IDE payload -> nothing meaningful to roll up;
    hook stays silent (no ``framework_operation`` and no ``framework_error``)."""
    rstop._emit_session_token_rollup(project, session_id=None, correlation_id="corr-test")

    events = _read_events(project)
    assert events == []
