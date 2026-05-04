"""Pin the v1.1 framework_event schema (P3.2 / 2026-05-04 gap closure).

ACI severity field added: ``detail.severity`` and ``detail.recovery_hint``.
Backward compat: events without these fields still parse (consumers
default severity to ``advisory``). The audit_index SQLite projection
gains two new columns; existing 1.0 events project as NULL.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
OBSERVABILITY_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "observability.py"


@pytest.fixture(scope="module")
def obs_mod():
    """Load _lib.observability via sys.path so its `from . import
    trace_context` succeeds (the relative import requires a package
    context, which spec_from_file_location does not provide)."""
    hooks_dir = REPO / ".ai-engineering" / "scripts" / "hooks"
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))
    # Force a fresh import so other tests' module caches don't leak.
    for name in list(sys.modules):
        if name.startswith("_lib"):
            del sys.modules[name]
    import _lib.observability as obs

    return obs


def test_schema_version_bumped_to_1_1(obs_mod) -> None:
    """The schema version constant must reflect the v1.1 fields."""
    assert obs_mod.FRAMEWORK_EVENT_SCHEMA_VERSION == "1.1"


def test_allowed_severity_set(obs_mod) -> None:
    """The three severity levels must be exposed as a frozen set."""
    assert frozenset({"recoverable", "terminal", "advisory"}) == obs_mod.ALLOWED_SEVERITY


def test_emit_framework_error_with_severity(obs_mod, tmp_path: Path) -> None:
    """When severity + recovery_hint are passed, both land in detail."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    entry = obs_mod.emit_framework_error(
        tmp_path,
        engine="claude_code",
        component="test.component",
        error_code="test_error",
        severity="recoverable",
        recovery_hint="retry with smaller batch size",
    )
    assert entry["detail"]["severity"] == "recoverable"
    assert entry["detail"]["recovery_hint"] == "retry with smaller batch size"
    assert entry["schemaVersion"] == "1.1"


def test_emit_framework_error_without_severity(obs_mod, tmp_path: Path) -> None:
    """Backward compat: omitting severity keeps detail clean (no key)."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    entry = obs_mod.emit_framework_error(
        tmp_path,
        engine="claude_code",
        component="test.component",
        error_code="test_error",
    )
    assert "severity" not in entry["detail"]
    assert "recovery_hint" not in entry["detail"]


def test_emit_framework_error_invalid_severity_coerces(obs_mod, tmp_path: Path) -> None:
    """Typo'd severity values fall back to ``advisory`` instead of crashing."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    entry = obs_mod.emit_framework_error(
        tmp_path,
        engine="claude_code",
        component="test.component",
        error_code="test_error",
        severity="not-a-valid-level",
    )
    assert entry["detail"]["severity"] == "advisory"


def test_audit_index_projects_severity_columns(tmp_path: Path) -> None:
    """The SQLite projection must surface severity + recovery_hint columns."""
    from ai_engineering.state.audit_index import build_index, index_path

    # Synthesize an NDJSON with a v1.1 framework_error event
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    ndjson = state / "framework-events.ndjson"
    event = {
        "schemaVersion": "1.1",
        "timestamp": "2026-05-04T10:00:00Z",
        "project": "synthetic",
        "engine": "claude_code",
        "kind": "framework_error",
        "outcome": "failure",
        "component": "test.severity",
        "correlationId": "abc123",
        "spanId": "span00000severity",
        "detail": {
            "error_code": "test",
            "severity": "terminal",
            "recovery_hint": "rotate the credentials",
        },
    }
    ndjson.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")

    result = build_index(tmp_path, rebuild=True)
    assert result.rows_indexed >= 1

    db_path = index_path(tmp_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("PRAGMA table_info(events)")
        cols = {row[1] for row in cur.fetchall()}
        assert "severity" in cols, f"missing severity column; got {cols}"
        assert "recovery_hint" in cols, f"missing recovery_hint column; got {cols}"

        cur = conn.execute(
            "SELECT severity, recovery_hint FROM events WHERE component = ?",
            ("test.severity",),
        )
        row = cur.fetchone()
        assert row == ("terminal", "rotate the credentials")
    finally:
        conn.close()


def test_audit_index_handles_legacy_v1_0_events(tmp_path: Path) -> None:
    """v1.0 events without the new fields must still parse (NULL projection)."""
    from ai_engineering.state.audit_index import build_index, index_path

    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    ndjson = state / "framework-events.ndjson"
    legacy_event = {
        "schemaVersion": "1.0",
        "timestamp": "2026-05-04T09:00:00Z",
        "project": "synthetic",
        "engine": "claude_code",
        "kind": "framework_error",
        "outcome": "failure",
        "component": "test.legacy",
        "correlationId": "legacy123",
        "spanId": "span00legacy0001",
        "detail": {
            "error_code": "old_error",
        },
    }
    ndjson.write_text(json.dumps(legacy_event, sort_keys=True) + "\n", encoding="utf-8")

    result = build_index(tmp_path, rebuild=True)
    assert result.rows_indexed >= 1

    conn = sqlite3.connect(str(index_path(tmp_path)))
    try:
        cur = conn.execute(
            "SELECT severity, recovery_hint FROM events WHERE component = ?",
            ("test.legacy",),
        )
        row = cur.fetchone()
        assert row == (None, None), "legacy events must project NULL for the v1.1 columns"
    finally:
        conn.close()
