"""Unit tests for ``ai_engineering.state.audit_index`` (spec-120 T-B1).

Covers the public API surface declared in spec-120 §4.3 and the
robustness contract documented in the module docstring:

* full build from a synthetic 50-event NDJSON file
* incremental rebuild advances ``last_offset`` and inserts only new rows
* ``rebuild=True`` drops and recreates schema (and view aggregates
  observe the fresh table)
* legacy events without ``spanId`` get a deterministic synthetic PK
* the three rollup views (skill / agent / session) aggregate correctly
* ``genai`` columns are NULL when absent
* malformed JSON lines are skipped without aborting the run
* :func:`open_index_readonly` rejects writes at the SQLite layer

Each test stages its own NDJSON file under ``tmp_path`` so the suite is
hermetic and never touches the project's real
``framework-events.ndjson``.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ai_engineering.state.audit_index import (
    INDEX_REL,
    NDJSON_REL,
    IndexResult,
    build_index,
    index_path,
    open_index_readonly,
)

# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Return a tmp project root with the standard state directory."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _ndjson_target(project_root: Path) -> Path:
    """Return the canonical NDJSON path under ``project_root``."""
    return project_root / NDJSON_REL


def _write_ndjson(path: Path, events: list[dict[str, Any]]) -> None:
    """Write ``events`` as canonical NDJSON to ``path`` (overwrites)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in events]
    path.write_text("".join(lines), encoding="utf-8")


def _append_ndjson(path: Path, events: list[dict[str, Any]]) -> None:
    """Append ``events`` to an existing NDJSON file."""
    with path.open("a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
            fh.write("\n")


def _hex32(seed: int) -> str:
    """Return a deterministic 32-hex traceId derived from ``seed``."""
    return hashlib.sha256(f"trace-{seed}".encode()).hexdigest()[:32]


def _hex16(seed: str) -> str:
    """Return a deterministic 16-hex spanId derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def _make_event(
    *,
    index: int,
    kind: str = "skill_invoked",
    component: str = "hook.telemetry-skill",
    detail: dict[str, Any] | None = None,
    span_id: str | None = "auto",
    parent_span_id: str | None = None,
    trace_id: str | None = "auto",
    session_id: str | None = "session-A",
    timestamp: str | None = None,
    outcome: str = "success",
    engine: str = "claude_code",
    correlation_id: str | None = None,
    source: str | None = "hook",
    prev_event_hash: str | None = None,
) -> dict[str, Any]:
    """Build a synthetic event in the canonical wire format.

    ``span_id="auto"`` / ``trace_id="auto"`` derive deterministic ids
    from ``index`` so tests can assert on specific values; pass
    ``None`` to omit the field entirely (legacy-event simulation).
    """
    base_ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
    event: dict[str, Any] = {
        "kind": kind,
        "engine": engine,
        "timestamp": timestamp if timestamp is not None else base_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "component": component,
        "outcome": outcome,
        "correlationId": correlation_id or f"corr-{index:04d}",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": detail if detail is not None else {"skill": "ai-brainstorm"},
    }
    if source is not None:
        event["source"] = source
    if prev_event_hash is not None:
        event["prev_event_hash"] = prev_event_hash
    if session_id is not None:
        event["sessionId"] = session_id
    if span_id == "auto":
        event["spanId"] = _hex16(f"span-{index}")
    elif span_id is not None:
        event["spanId"] = span_id
    if trace_id == "auto":
        event["traceId"] = _hex32(0)
    elif trace_id is not None:
        event["traceId"] = trace_id
    if parent_span_id is not None:
        event["parentSpanId"] = parent_span_id
    return event


def _genai_detail(
    *,
    skill: str = "ai-brainstorm",
    input_tokens: int = 100,
    output_tokens: int = 50,
    total_tokens: int = 150,
    cost_usd: float = 0.001,
    system: str = "anthropic",
    model: str = "claude-sonnet-4-5",
) -> dict[str, Any]:
    """Build a ``detail`` dict with a populated ``genai`` block."""
    return {
        "skill": skill,
        "genai": {
            "system": system,
            "request": {"model": model},
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
        },
    }


# ---------------------------------------------------------------------------
# index_path / NDJSON_REL
# ---------------------------------------------------------------------------


def test_index_path_under_state_dir(tmp_path: Path) -> None:
    """``index_path`` returns the canonical SQLite location.

    spec-123 D-123-22 redirected the projection from
    ``audit-index.sqlite`` to the unified ``state.db``.
    """
    expected = tmp_path / ".ai-engineering" / "state" / "state.db"
    assert index_path(tmp_path) == expected
    assert Path(".ai-engineering") / "state" / "state.db" == INDEX_REL


def test_ndjson_rel_constant() -> None:
    """``NDJSON_REL`` matches the canonical framework-events path."""
    assert Path(".ai-engineering") / "state" / "framework-events.ndjson" == NDJSON_REL


# ---------------------------------------------------------------------------
# Soft success on missing file
# ---------------------------------------------------------------------------


def test_build_index_soft_success_when_ndjson_missing(project_root: Path) -> None:
    """No NDJSON -> empty IndexResult; no SQLite file is created."""
    result = build_index(project_root)
    assert isinstance(result, IndexResult)
    assert result.rows_indexed == 0
    assert result.rows_total == 0
    assert result.last_offset == 0
    assert result.elapsed_ms == 0
    assert result.rebuilt is False
    # Soft success: no SQLite created either.
    assert not index_path(project_root).exists()


def test_build_index_rebuild_flag_propagates_when_missing(project_root: Path) -> None:
    """``rebuilt`` reflects the input flag even on the soft-success path."""
    result = build_index(project_root, rebuild=True)
    assert result.rebuilt is True
    assert result.rows_indexed == 0


# ---------------------------------------------------------------------------
# Full build
# ---------------------------------------------------------------------------


def test_full_build_from_synthetic_ndjson(project_root: Path) -> None:
    """50-event synthetic NDJSON produces 50 rows with all columns set."""
    events = [_make_event(index=i) for i in range(50)]
    _write_ndjson(_ndjson_target(project_root), events)

    result = build_index(project_root)

    assert result.rows_indexed == 50
    assert result.rows_total == 50
    assert result.rebuilt is False
    assert result.last_offset > 0
    assert result.elapsed_ms >= 0

    # Spot-check the columns landed.
    conn = open_index_readonly(project_root)
    try:
        rows = conn.execute(
            "SELECT span_id, trace_id, correlation_id, kind, engine, component, "
            "outcome, ts_unix_ms FROM events ORDER BY ts_unix_ms"
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 50
    first = rows[0]
    assert first[0] == _hex16("span-0")
    assert first[1] == _hex32(0)
    assert first[2] == "corr-0000"
    assert first[3] == "skill_invoked"
    assert first[4] == "claude_code"
    assert first[5] == "hook.telemetry-skill"
    assert first[6] == "success"
    assert first[7] > 0  # ISO-8601 timestamp parsed to non-zero unix ms


# ---------------------------------------------------------------------------
# Incremental rebuild
# ---------------------------------------------------------------------------


def test_incremental_rebuild_advances_offset(project_root: Path) -> None:
    """Appending 5 new events and rebuilding without ``rebuild`` ingests
    only the new rows; ``last_offset`` advances past the new tail."""
    initial = [_make_event(index=i) for i in range(10)]
    _write_ndjson(_ndjson_target(project_root), initial)
    first = build_index(project_root)
    assert first.rows_indexed == 10
    assert first.rows_total == 10
    offset_after_first = first.last_offset

    addition = [_make_event(index=i) for i in range(10, 15)]
    _append_ndjson(_ndjson_target(project_root), addition)

    second = build_index(project_root)
    assert second.rows_indexed == 5  # only new rows ingested
    assert second.rows_total == 15  # previously indexed rows preserved
    assert second.last_offset > offset_after_first
    assert second.rebuilt is False

    # File-end offset should match the actual NDJSON byte length.
    actual_size = _ndjson_target(project_root).stat().st_size
    assert second.last_offset == actual_size


# ---------------------------------------------------------------------------
# Rebuild flag
# ---------------------------------------------------------------------------


def test_rebuild_flag_drops_and_recreates(project_root: Path) -> None:
    """``rebuild=True`` drops the table; the result mirrors a fresh run."""
    events = [_make_event(index=i) for i in range(10)]
    _write_ndjson(_ndjson_target(project_root), events)

    build_index(project_root)
    # Mutate the SQLite directly so we can prove the table was dropped:
    # adding a synthetic row that will not appear in the source NDJSON.
    sqlite_path = index_path(project_root)
    direct = sqlite3.connect(str(sqlite_path), timeout=10.0)
    try:
        direct.execute(
            "INSERT INTO events (span_id, correlation_id, timestamp, "
            "engine, kind, component, outcome, detail_json) VALUES (?,?,?,?,?,?,?,?)",
            (
                "deadbeefdeadbeef",
                "synthetic-bypass",
                "2025-01-01T00:00:00Z",
                "claude_code",
                "skill_invoked",
                "synth.bypass",
                "success",
                "{}",
            ),
        )
        direct.commit()
    finally:
        direct.close()

    # rebuild=True should wipe the synthetic row.
    result = build_index(project_root, rebuild=True)
    assert result.rebuilt is True
    assert result.rows_indexed == 10
    assert result.rows_total == 10

    conn = open_index_readonly(project_root)
    try:
        match = conn.execute(
            "SELECT COUNT(*) FROM events WHERE span_id = 'deadbeefdeadbeef'"
        ).fetchone()
    finally:
        conn.close()
    assert match[0] == 0  # synthetic row was dropped


# ---------------------------------------------------------------------------
# Legacy events
# ---------------------------------------------------------------------------


def test_legacy_events_get_synthetic_pk(project_root: Path) -> None:
    """Events without ``spanId`` get a deterministic synthetic PK.

    spec-123 D-123-22: synthetic IDs match migration 0003's
    ``synthetic:<24hex>`` format so the lazy-bootstrap path and the
    ``audit_index`` rebuild path produce identical PKs (no double-insert).
    """
    events = [_make_event(index=i, span_id=None, trace_id=None) for i in range(5)]
    _write_ndjson(_ndjson_target(project_root), events)

    result = build_index(project_root)
    assert result.rows_indexed == 5
    assert result.rows_total == 5

    conn = open_index_readonly(project_root)
    try:
        rows = conn.execute("SELECT span_id FROM events").fetchall()
    finally:
        conn.close()
    span_ids = {row[0] for row in rows}
    assert len(span_ids) == 5  # synthetic PKs must be unique
    for span_id in span_ids:
        assert isinstance(span_id, str)
        assert span_id.startswith("synthetic:")
        digest = span_id.removeprefix("synthetic:")
        assert len(digest) == 24
        assert all(ch in "0123456789abcdef" for ch in digest)


def test_legacy_event_synthetic_pk_is_deterministic(project_root: Path) -> None:
    """Re-running on the same source produces the same synthetic PKs."""
    events = [_make_event(index=i, span_id=None, trace_id=None) for i in range(3)]
    _write_ndjson(_ndjson_target(project_root), events)

    first = build_index(project_root, rebuild=True)
    conn1 = open_index_readonly(project_root)
    try:
        ids_first = sorted(row[0] for row in conn1.execute("SELECT span_id FROM events"))
    finally:
        conn1.close()

    second = build_index(project_root, rebuild=True)
    conn2 = open_index_readonly(project_root)
    try:
        ids_second = sorted(row[0] for row in conn2.execute("SELECT span_id FROM events"))
    finally:
        conn2.close()

    assert first.rows_indexed == second.rows_indexed == 3
    assert ids_first == ids_second


# ---------------------------------------------------------------------------
# Rollup views
# ---------------------------------------------------------------------------


def test_skill_token_rollup_view(project_root: Path) -> None:
    """``skill_token_rollup`` aggregates input/output/total/cost per skill."""
    events = [
        _make_event(
            index=0,
            kind="skill_invoked",
            detail=_genai_detail(
                skill="ai-brainstorm",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.001,
            ),
        ),
        _make_event(
            index=1,
            kind="skill_invoked",
            detail=_genai_detail(
                skill="ai-brainstorm",
                input_tokens=200,
                output_tokens=70,
                total_tokens=270,
                cost_usd=0.002,
            ),
        ),
        _make_event(
            index=2,
            kind="skill_invoked",
            detail=_genai_detail(
                skill="ai-plan",
                input_tokens=80,
                output_tokens=30,
                total_tokens=110,
                cost_usd=0.0005,
            ),
        ),
    ]
    _write_ndjson(_ndjson_target(project_root), events)
    build_index(project_root)

    conn = open_index_readonly(project_root)
    try:
        rows = conn.execute(
            "SELECT skill, invocations, input_tokens, output_tokens, "
            "total_tokens, cost_usd FROM skill_token_rollup ORDER BY skill"
        ).fetchall()
    finally:
        conn.close()

    by_skill = {row[0]: row for row in rows}
    assert by_skill["ai-brainstorm"][1] == 2
    assert by_skill["ai-brainstorm"][2] == 300
    assert by_skill["ai-brainstorm"][3] == 120
    assert by_skill["ai-brainstorm"][4] == 420
    assert by_skill["ai-brainstorm"][5] == pytest.approx(0.003)
    assert by_skill["ai-plan"][1] == 1
    assert by_skill["ai-plan"][4] == 110


def test_agent_token_rollup_view(project_root: Path) -> None:
    """``agent_token_rollup`` aggregates per-agent dispatch counts + tokens."""
    events = [
        _make_event(
            index=0,
            kind="agent_dispatched",
            detail={
                "agent": "ai-build",
                "genai": {
                    "system": "anthropic",
                    "request": {"model": "claude-sonnet-4-5"},
                    "usage": {
                        "input_tokens": 500,
                        "output_tokens": 250,
                        "total_tokens": 750,
                        "cost_usd": 0.005,
                    },
                },
            },
        ),
        _make_event(
            index=1,
            kind="agent_dispatched",
            detail={
                "agent": "ai-build",
                "genai": {
                    "system": "anthropic",
                    "request": {"model": "claude-sonnet-4-5"},
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_tokens": 150,
                        "cost_usd": 0.001,
                    },
                },
            },
        ),
        _make_event(
            index=2,
            kind="agent_dispatched",
            detail={
                "agent": "ai-explore",
                "genai": {
                    "system": "anthropic",
                    "request": {"model": "claude-sonnet-4-5"},
                    "usage": {
                        "input_tokens": 200,
                        "output_tokens": 80,
                        "total_tokens": 280,
                        "cost_usd": 0.002,
                    },
                },
            },
        ),
    ]
    _write_ndjson(_ndjson_target(project_root), events)
    build_index(project_root)

    conn = open_index_readonly(project_root)
    try:
        rows = conn.execute(
            "SELECT agent, dispatches, input_tokens, output_tokens, "
            "total_tokens, cost_usd FROM agent_token_rollup ORDER BY agent"
        ).fetchall()
    finally:
        conn.close()

    by_agent = {row[0]: row for row in rows}
    assert by_agent["ai-build"][1] == 2
    assert by_agent["ai-build"][2] == 600
    assert by_agent["ai-build"][3] == 300
    assert by_agent["ai-build"][4] == 900
    assert by_agent["ai-build"][5] == pytest.approx(0.006)
    assert by_agent["ai-explore"][1] == 1
    assert by_agent["ai-explore"][4] == 280


def test_session_token_rollup_view(project_root: Path) -> None:
    """``session_token_rollup`` groups by ``session_id`` with min/max ts."""
    events = [
        _make_event(
            index=0,
            kind="skill_invoked",
            session_id="session-X",
            detail=_genai_detail(input_tokens=50, output_tokens=25, total_tokens=75),
        ),
        _make_event(
            index=1,
            kind="skill_invoked",
            session_id="session-X",
            detail=_genai_detail(input_tokens=70, output_tokens=35, total_tokens=105),
        ),
        _make_event(
            index=10,
            kind="skill_invoked",
            session_id="session-Y",
            detail=_genai_detail(input_tokens=200, output_tokens=100, total_tokens=300),
        ),
        # A session-less event: must NOT be counted in the rollup.
        _make_event(
            index=20,
            kind="skill_invoked",
            session_id=None,
            detail=_genai_detail(input_tokens=999, output_tokens=999, total_tokens=999),
        ),
    ]
    _write_ndjson(_ndjson_target(project_root), events)
    build_index(project_root)

    conn = open_index_readonly(project_root)
    try:
        rows = conn.execute(
            "SELECT session_id, events, input_tokens, output_tokens, "
            "total_tokens, started_at, ended_at FROM session_token_rollup "
            "ORDER BY session_id"
        ).fetchall()
    finally:
        conn.close()

    sessions = {row[0]: row for row in rows}
    assert set(sessions.keys()) == {"session-X", "session-Y"}
    assert sessions["session-X"][1] == 2
    assert sessions["session-X"][2] == 120
    assert sessions["session-X"][3] == 60
    assert sessions["session-X"][4] == 180
    # min/max timestamps preserved as strings; lexical compare matches
    # chronological order for canonical ISO-8601 Z form.
    assert sessions["session-X"][5] <= sessions["session-X"][6]
    assert sessions["session-Y"][1] == 1
    assert sessions["session-Y"][4] == 300


# ---------------------------------------------------------------------------
# genai column nullability
# ---------------------------------------------------------------------------


def test_genai_columns_null_when_absent(project_root: Path) -> None:
    """Events without a ``detail.genai`` block leave genai columns NULL."""
    events = [
        _make_event(index=0, kind="ide_hook", component="hook.foo", detail={"hook_kind": "stop"}),
        _make_event(
            index=1, kind="git_hook", component="hook.bar", detail={"hook_kind": "pre-commit"}
        ),
    ]
    _write_ndjson(_ndjson_target(project_root), events)
    build_index(project_root)

    conn = open_index_readonly(project_root)
    try:
        rows = conn.execute(
            "SELECT genai_system, genai_model, input_tokens, output_tokens, "
            "total_tokens, cost_usd FROM events"
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 2
    for row in rows:
        assert all(value is None for value in row)


def test_genai_columns_populated_when_present(project_root: Path) -> None:
    """Events with a populated ``genai`` block surface the LLM columns."""
    events = [
        _make_event(
            index=0,
            kind="skill_invoked",
            detail=_genai_detail(
                input_tokens=42,
                output_tokens=7,
                total_tokens=49,
                cost_usd=0.0001,
                system="anthropic",
                model="claude-sonnet-4-5",
            ),
        )
    ]
    _write_ndjson(_ndjson_target(project_root), events)
    build_index(project_root)

    conn = open_index_readonly(project_root)
    try:
        row = conn.execute(
            "SELECT genai_system, genai_model, input_tokens, output_tokens, "
            "total_tokens, cost_usd FROM events"
        ).fetchone()
    finally:
        conn.close()

    assert row == ("anthropic", "claude-sonnet-4-5", 42, 7, 49, 0.0001)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_malformed_json_lines_skipped(
    project_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A corrupt line in the middle is skipped; surrounding rows land."""
    good_a = _make_event(index=0)
    good_b = _make_event(index=1)
    good_c = _make_event(index=2)
    target = _ndjson_target(project_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(good_a, sort_keys=True, separators=(",", ":")) + "\n")
        fh.write("{not-valid-json,,\n")
        fh.write(json.dumps(good_b, sort_keys=True, separators=(",", ":")) + "\n")
        fh.write("[1, 2, 3]\n")  # valid JSON but not a dict
        fh.write(json.dumps(good_c, sort_keys=True, separators=(",", ":")) + "\n")

    result = build_index(project_root)
    assert result.rows_indexed == 3
    assert result.rows_total == 3

    captured = capsys.readouterr()
    assert "audit_index:" in captured.err
    assert "malformed JSON" in captured.err or "non-dict" in captured.err

    conn = open_index_readonly(project_root)
    try:
        kinds = [row[0] for row in conn.execute("SELECT kind FROM events")]
    finally:
        conn.close()
    assert kinds.count("skill_invoked") == 3


def test_blank_trailing_lines_tolerated(project_root: Path) -> None:
    """Blank lines do not bump the row counter and do not raise."""
    target = _ndjson_target(project_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    event = _make_event(index=0)
    with target.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        fh.write("\n\n")  # blank tail
    result = build_index(project_root)
    assert result.rows_indexed == 1
    assert result.rows_total == 1


def test_legacy_event_with_missing_required_fields_still_indexes(
    project_root: Path,
) -> None:
    """Legacy event without ``engine`` / ``component`` / ``outcome`` /
    ``correlationId`` still produces a row with placeholder values.

    spec-123 D-123-22: the projection target is now state.db owned by
    migration 0003. Defaults align with that migration -- ``unknown`` for
    engine/kind/component, ``success`` for outcome (audit-chain still
    captures the missing-fields condition via ``degraded_reason``).
    correlation_id is now nullable in state.db so legacy events no longer
    need a synthesised placeholder.
    """
    minimal: dict[str, Any] = {
        "kind": "framework_operation",
        "timestamp": "",
        "detail": {},
    }
    _write_ndjson(_ndjson_target(project_root), [minimal])

    result = build_index(project_root)
    assert result.rows_indexed == 1

    conn = open_index_readonly(project_root)
    try:
        row = conn.execute(
            "SELECT engine, component, outcome, correlation_id, ts_unix_ms FROM events"
        ).fetchone()
    finally:
        conn.close()

    assert row[0] == "unknown"
    assert row[1] == "unknown"
    # Migration 0003 keeps the schema NOT NULL contract by defaulting
    # missing outcome to 'success' (degraded conditions are surfaced via
    # detail.degraded_reason, not the column).
    assert row[2] == "success"
    # correlation_id is now nullable; missing input -> NULL.
    assert row[3] is None
    # ts_unix_ms is GENERATED on state.db -- empty timestamp yields NULL.
    assert row[4] is None


def test_camelcase_prev_event_hash_alias(project_root: Path) -> None:
    """``prevEventHash`` (Pydantic alias) is read into ``prev_event_hash``."""
    event = _make_event(index=0)
    event.pop("prev_event_hash", None)
    event["prevEventHash"] = "abc123"
    _write_ndjson(_ndjson_target(project_root), [event])

    build_index(project_root)
    conn = open_index_readonly(project_root)
    try:
        row = conn.execute("SELECT prev_event_hash FROM events").fetchone()
    finally:
        conn.close()
    assert row[0] == "abc123"


def test_unparseable_timestamp_falls_back_to_zero(project_root: Path) -> None:
    """A garbage ``timestamp`` value preserves the raw text.

    spec-123 D-123-22: ``ts_unix_ms`` is a SQLite GENERATED column on
    state.db, so an unparseable timestamp yields NULL (not 0). The raw
    text is still preserved in the ``timestamp`` column for forensics.
    """
    event = _make_event(index=0, timestamp="not-an-iso-string")
    _write_ndjson(_ndjson_target(project_root), [event])
    build_index(project_root)
    conn = open_index_readonly(project_root)
    try:
        row = conn.execute("SELECT timestamp, ts_unix_ms FROM events").fetchone()
    finally:
        conn.close()
    assert row[0] == "not-an-iso-string"
    assert row[1] is None


def test_float_token_value_coerced_to_int(project_root: Path) -> None:
    """A token count emitted as ``150.0`` is normalised to ``150``."""
    detail = {
        "skill": "ai-brainstorm",
        "genai": {
            "system": "anthropic",
            "request": {"model": "claude-sonnet-4-5"},
            "usage": {
                "input_tokens": 100.0,  # float that is integral
                "output_tokens": "not-a-number",  # garbage -> NULL
                "total_tokens": 150,
                "cost_usd": "free",  # garbage -> NULL
            },
        },
    }
    event = _make_event(index=0, detail=detail)
    _write_ndjson(_ndjson_target(project_root), [event])
    build_index(project_root)
    conn = open_index_readonly(project_root)
    try:
        row = conn.execute(
            "SELECT input_tokens, output_tokens, total_tokens, cost_usd FROM events"
        ).fetchone()
    finally:
        conn.close()
    assert row == (100, None, 150, None)


# ---------------------------------------------------------------------------
# Read-only connection
# ---------------------------------------------------------------------------


def test_open_readonly_refuses_writes(project_root: Path) -> None:
    """``open_index_readonly`` rejects INSERT / UPDATE / DELETE."""
    events = [_make_event(index=i) for i in range(3)]
    _write_ndjson(_ndjson_target(project_root), events)
    build_index(project_root)

    conn = open_index_readonly(project_root)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO events (span_id, correlation_id, timestamp, ts_unix_ms, "
                "engine, kind, component, outcome, detail_json) VALUES "
                "('x','y','',0,'claude_code','skill_invoked','c','success','{}')"
            )
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("UPDATE events SET outcome = 'failure'")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM events")
        # Reads must still succeed.
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert count == 3
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# IndexResult ergonomics
# ---------------------------------------------------------------------------


def test_index_result_is_frozen_dataclass() -> None:
    """``IndexResult`` is a frozen dataclass (defensive contract).

    ``dataclasses.FrozenInstanceError`` is a subclass of
    ``AttributeError`` per stdlib, so we assert against the more
    informative concrete type rather than a blind ``Exception``.
    """
    from dataclasses import FrozenInstanceError

    result = IndexResult(rows_indexed=1, rows_total=1, last_offset=10, elapsed_ms=5, rebuilt=False)
    with pytest.raises(FrozenInstanceError):
        result.rows_indexed = 99  # type: ignore[misc]
