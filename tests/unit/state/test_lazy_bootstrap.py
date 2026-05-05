"""Tests for lazy ``state_db.connect()`` bootstrap (spec-123 T-3.1 / T-3.2).

When ``state.db`` is missing under ``<project_root>/.ai-engineering/state/``,
the first ``state_db.connect(project_root)`` call must:

1. Create the database file (via :func:`sqlite3.connect`).
2. Apply every pending migration (so all 7 STRICT business tables exist
   plus the ``_migrations`` ledger). The 3 currently-shipped migrations
   are ``0001_initial_schema``, ``0002_seed_from_json``, and
   ``0003_replay_ndjson`` — the ledger should record exactly these IDs.
3. Replay any existing ``framework-events.ndjson`` lines into the
   ``events`` table (by virtue of migration ``0003``).

Subsequent ``connect()`` calls must be cheap no-ops (DB exists, migrations
already in the ledger, no duplicate inserts thanks to ``ON CONFLICT DO
NOTHING`` in the seed/replay migrations).

The bootstrap is therefore both *eager* (first call does the work) and
*idempotent* (re-runs are safe + side-effect-free).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ai_engineering.state import state_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Tmp project root with the state directory present but no state.db."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _expected_migration_ids() -> set[str]:
    """The migration IDs the bootstrap must apply on first connect."""
    return {
        "0001_initial_schema",
        "0002_seed_from_json",
        "0003_replay_ndjson",
    }


# ---------------------------------------------------------------------------
# T-3.1 — RED: lazy bootstrap on first connect
# ---------------------------------------------------------------------------


class TestLazyBootstrap:
    """First ``connect()`` on a missing DB applies all migrations."""

    def test_db_file_is_created(self, project_root: Path) -> None:
        """connect() materialises state.db on disk on the first call."""
        db_path = state_db.state_db_path(project_root)
        # ``state.db`` may be a 0-byte placeholder from the parent
        # repository (touched by some earlier installer step). Treat that
        # as 'missing' for the purposes of the bootstrap test.
        if db_path.exists():
            db_path.unlink()
        assert not db_path.exists()

        conn = state_db.connect(project_root)
        try:
            assert db_path.exists(), "connect() did not create state.db"
            assert db_path.stat().st_size > 0, "state.db should not be 0 bytes"
        finally:
            conn.close()

    def test_all_migrations_recorded(self, project_root: Path) -> None:
        """First connect() applies every pending migration."""
        db_path = state_db.state_db_path(project_root)
        if db_path.exists():
            db_path.unlink()

        conn = state_db.connect(project_root)
        try:
            rows = conn.execute("SELECT id FROM _migrations ORDER BY id").fetchall()
        finally:
            conn.close()

        applied_ids = {row[0] for row in rows}
        assert applied_ids == _expected_migration_ids(), (
            f"expected {_expected_migration_ids()}, got {applied_ids}"
        )

    def test_seven_business_tables_exist(self, project_root: Path) -> None:
        """All 7 STRICT business tables exist after bootstrap."""
        db_path = state_db.state_db_path(project_root)
        if db_path.exists():
            db_path.unlink()

        conn = state_db.connect(project_root)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()

        expected = {
            "events",
            "decisions",
            "risk_acceptances",
            "gate_findings",
            "hooks_integrity",
            "ownership_map",
            "install_steps",
            "_migrations",
        }
        missing = expected - tables
        assert not missing, f"missing tables after bootstrap: {missing}"

    def test_ndjson_replayed_into_events(self, project_root: Path) -> None:
        """Pre-existing NDJSON lines populate the events table on bootstrap."""
        # Stage a tiny NDJSON file with two events.
        ndjson_path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
        events = [
            {
                "timestamp": "2026-04-01T00:00:00Z",
                "engine": "claude_code",
                "kind": "tool_invoked",
                "component": "test.bootstrap",
                "outcome": "success",
                "session_id": "sess-1",
                "trace_id": "trace-1",
                "span_id": "span-1",
                "detail": {"hello": "world"},
            },
            {
                "timestamp": "2026-04-01T00:00:01Z",
                "engine": "claude_code",
                "kind": "framework_operation",
                "component": "test.bootstrap",
                "outcome": "success",
                "session_id": "sess-1",
                "trace_id": "trace-1",
                "span_id": "span-2",
                "detail": {"step": 2},
            },
        ]
        with ndjson_path.open("w", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event) + "\n")

        # Ensure no pre-existing DB.
        db_path = state_db.state_db_path(project_root)
        if db_path.exists():
            db_path.unlink()

        conn = state_db.connect(project_root)
        try:
            count = conn.execute("SELECT count(*) FROM events").fetchone()[0]
        finally:
            conn.close()

        assert count == 2, f"expected 2 events replayed, got {count}"

    def test_subsequent_connects_are_idempotent(self, project_root: Path) -> None:
        """Re-running connect() does not duplicate ledger rows or events."""
        # Stage one event so we can also verify the events table doesn't double up.
        ndjson_path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
        ndjson_path.write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-01T00:00:00Z",
                    "engine": "claude_code",
                    "kind": "framework_operation",
                    "component": "test.bootstrap",
                    "outcome": "success",
                    "session_id": "sess-x",
                    "span_id": "span-x",
                    "detail": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        db_path = state_db.state_db_path(project_root)
        if db_path.exists():
            db_path.unlink()

        # First connect bootstraps.
        conn = state_db.connect(project_root)
        try:
            first_ledger = conn.execute("SELECT count(*) FROM _migrations").fetchone()[0]
            first_events = conn.execute("SELECT count(*) FROM events").fetchone()[0]
        finally:
            conn.close()

        # Second connect must NOT re-run migrations or duplicate events.
        conn = state_db.connect(project_root)
        try:
            second_ledger = conn.execute("SELECT count(*) FROM _migrations").fetchone()[0]
            second_events = conn.execute("SELECT count(*) FROM events").fetchone()[0]
        finally:
            conn.close()

        assert first_ledger == second_ledger == 3
        assert first_events == 1
        assert second_events == 1

    def test_zero_byte_db_triggers_bootstrap(self, project_root: Path) -> None:
        """A 0-byte state.db placeholder is treated as 'missing' and bootstrapped.

        The installer historically ``touch``ed state.db; the bootstrap must
        recognise such placeholders and apply migrations rather than
        crashing on the first ``CREATE TABLE``.
        """
        db_path = state_db.state_db_path(project_root)
        if db_path.exists():
            db_path.unlink()
        # Touch the file (0 bytes).
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        assert db_path.stat().st_size == 0

        conn = state_db.connect(project_root)
        try:
            rows = conn.execute("SELECT id FROM _migrations ORDER BY id").fetchall()
        finally:
            conn.close()

        applied_ids = {row[0] for row in rows}
        assert applied_ids == _expected_migration_ids()

    def test_read_only_does_not_bootstrap(self, project_root: Path) -> None:
        """``read_only=True`` must not trigger migrations; the DB stays empty.

        Read-only callers expect an existing DB; if the file is missing,
        SQLite raises ``sqlite3.OperationalError``. The bootstrap path is
        a writer-side responsibility.
        """
        db_path = state_db.state_db_path(project_root)
        if db_path.exists():
            db_path.unlink()

        with pytest.raises(sqlite3.OperationalError):
            # ``mode=ro`` URI on a missing file -> OperationalError.
            state_db.connect(project_root, read_only=True)
