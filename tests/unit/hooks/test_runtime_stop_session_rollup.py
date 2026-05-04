"""Tests for the spec-120 T-E1 session token rollup wiring inside
``runtime-stop.py``.

Pin three branches of ``_emit_session_token_rollup`` so the best-effort
contract stays honest:

1. **Rollup row found** -> a single ``framework_operation`` event with
   ``detail.operation = "session_token_rollup"`` and the rollup payload.
2. **Rollup view exists but no row for the session_id** -> silent skip
   (no ``framework_operation``, no ``framework_error``).
3. **SQLite index file missing** -> a single ``framework_error`` event
   with ``detail.error_code = "session_rollup_skipped"``; the hook never
   raises.

The earlier ``runtime-stop.py`` had no session-end rollup, so the
NDJSON stream lost the per-session token tally that the audit-index
view publishes -- this suite is the regression guard.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
INDEX_REL = Path(".ai-engineering") / "state" / "audit-index.sqlite"


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


def _seed_index(project_root: Path, *, session_id: str, totals: dict) -> None:
    """Write a minimal SQLite DB with the spec-120 session_token_rollup view.

    Mirrors the schema in ``ai_engineering.state.audit_index`` so the
    hook's read-only query lands on the same column ordering.
    """
    path = project_root / INDEX_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
              span_id            TEXT PRIMARY KEY,
              trace_id           TEXT,
              parent_span_id     TEXT,
              correlation_id     TEXT NOT NULL,
              session_id         TEXT,
              timestamp          TEXT NOT NULL,
              ts_unix_ms         INTEGER NOT NULL,
              engine             TEXT NOT NULL,
              kind               TEXT NOT NULL,
              component          TEXT NOT NULL,
              outcome            TEXT NOT NULL,
              source             TEXT,
              prev_event_hash    TEXT,
              genai_system       TEXT,
              genai_model        TEXT,
              input_tokens       INTEGER,
              output_tokens      INTEGER,
              total_tokens       INTEGER,
              cost_usd           REAL,
              detail_json        TEXT NOT NULL
            );
            CREATE VIEW IF NOT EXISTS session_token_rollup AS
              SELECT session_id,
                     MIN(timestamp)        AS started_at,
                     MAX(timestamp)        AS ended_at,
                     COUNT(*)              AS events,
                     SUM(input_tokens)     AS input_tokens,
                     SUM(output_tokens)    AS output_tokens,
                     SUM(total_tokens)     AS total_tokens,
                     SUM(cost_usd)         AS cost_usd
                FROM events
               WHERE session_id IS NOT NULL
               GROUP BY session_id;
            """
        )
        conn.execute(
            "INSERT INTO events VALUES "
            "(:span_id, :trace_id, :parent_span_id, :correlation_id, :session_id, "
            ":timestamp, :ts_unix_ms, :engine, :kind, :component, :outcome, :source, "
            ":prev_event_hash, :genai_system, :genai_model, :input_tokens, "
            ":output_tokens, :total_tokens, :cost_usd, :detail_json)",
            {
                "span_id": "0123456789abcdef",
                "trace_id": "f" * 32,
                "parent_span_id": None,
                "correlation_id": "corr-1",
                "session_id": session_id,
                "timestamp": "2026-05-04T00:00:00Z",
                "ts_unix_ms": 1_746_316_800_000,
                "engine": "claude_code",
                "kind": "skill_invoked",
                "component": "hook.telemetry-skill",
                "outcome": "success",
                "source": "hook",
                "prev_event_hash": None,
                "genai_system": "anthropic",
                "genai_model": "claude-opus-4.7",
                "input_tokens": totals["input_tokens"],
                "output_tokens": totals["output_tokens"],
                "total_tokens": totals["total_tokens"],
                "cost_usd": totals["cost_usd"],
                "detail_json": "{}",
            },
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Branch 1: rollup row found
# ---------------------------------------------------------------------------


def test_session_rollup_emits_framework_operation_when_row_found(rstop, project: Path) -> None:
    """Happy path: SQLite index has a row for the session -> one
    ``framework_operation`` event with the rollup payload."""
    session_id = "sess-happy"
    totals = {
        "input_tokens": 1000,
        "output_tokens": 250,
        "total_tokens": 1250,
        "cost_usd": 0.0125,
    }
    _seed_index(project, session_id=session_id, totals=totals)

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
# Branch 2: rollup view exists, no row for this session_id
# ---------------------------------------------------------------------------


def test_session_rollup_silent_skip_when_no_row_for_session(rstop, project: Path) -> None:
    """View exists but the session has no events -> no event emitted at all
    (neither framework_operation nor framework_error)."""
    _seed_index(
        project,
        session_id="sess-other",
        totals={
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
            "cost_usd": 0.0,
        },
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
# Branch 3: SQLite missing -> framework_error
# ---------------------------------------------------------------------------


def test_session_rollup_emits_framework_error_when_sqlite_missing(rstop, project: Path) -> None:
    """Index file absent -> single ``framework_error`` event with
    ``error_code = session_rollup_skipped``; hook does not raise."""
    assert not (project / INDEX_REL).exists()

    rstop._emit_session_token_rollup(
        project, session_id="sess-no-index", correlation_id="corr-test"
    )

    events = _read_events(project)
    errors = [
        e
        for e in events
        if e.get("kind") == "framework_error"
        and (e.get("detail") or {}).get("error_code") == "session_rollup_skipped"
    ]
    assert len(errors) == 1, f"expected exactly one error event, got {events}"
    assert errors[0]["component"] == "hook.runtime-stop"
    assert errors[0]["correlationId"] == "corr-test"
    assert errors[0]["sessionId"] == "sess-no-index"
    assert errors[0]["detail"]["reason"] == "audit_index_missing"


# ---------------------------------------------------------------------------
# Branch 4: session_id is None -> silent (no event of any kind)
# ---------------------------------------------------------------------------


def test_session_rollup_silent_when_session_id_missing(rstop, project: Path) -> None:
    """No session_id from the IDE payload -> nothing meaningful to roll up;
    hook stays silent (no ``framework_operation`` and no ``framework_error``)."""
    rstop._emit_session_token_rollup(project, session_id=None, correlation_id="corr-test")

    events = _read_events(project)
    assert events == []


# ---------------------------------------------------------------------------
# Branch 5: SQLite raises -> framework_error with sqlite_error metadata
# ---------------------------------------------------------------------------


def test_session_rollup_emits_framework_error_on_sqlite_failure(
    rstop, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force ``sqlite3.connect`` to raise mid-call -> single framework_error
    with ``reason`` starting with ``sqlite_error:``."""
    # Write a valid-looking file so the existence check passes; the
    # connect call below is what raises.
    (project / INDEX_REL).parent.mkdir(parents=True, exist_ok=True)
    (project / INDEX_REL).write_bytes(b"not a real sqlite db")

    real_connect = sqlite3.connect

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise sqlite3.OperationalError("synthetic failure")

    monkeypatch.setattr(rstop.sqlite3, "connect", boom)

    rstop._emit_session_token_rollup(project, session_id="sess-locked", correlation_id="corr-test")

    # Restore so other tests see the real sqlite3.connect.
    monkeypatch.setattr(rstop.sqlite3, "connect", real_connect)

    events = _read_events(project)
    errors = [
        e
        for e in events
        if e.get("kind") == "framework_error"
        and (e.get("detail") or {}).get("error_code") == "session_rollup_skipped"
    ]
    assert len(errors) == 1
    assert errors[0]["detail"]["reason"].startswith("sqlite_error:")
