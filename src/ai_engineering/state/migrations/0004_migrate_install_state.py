"""Migrate install-state.json to the install_state state.db table (spec-125 T-1.3).

Creates a STRICT singleton table keyed by ``id = 1`` that stores the
canonical :class:`ai_engineering.state.models.InstallState` payload as
JSON in the ``state_json`` column. Frequently-queried scalar fields
(``schema_version``, ``vcs_provider``, ``installed_at``,
``operational_status``) are mirrored as columns for indexing without
requiring SQLite JSON1.

Idempotent contract
-------------------
* ``CREATE TABLE IF NOT EXISTS`` ensures schema creation is safe to
  re-run.
* The singleton row uses ``INSERT INTO install_state (id, ...) VALUES
  (1, ...) ON CONFLICT(id) DO UPDATE`` so re-applying the migration
  with the same source JSON yields exactly one row (no duplicates).
* When ``install-state.json`` is absent, a default ``InstallState`` is
  ingested so downstream readers always find a valid singleton row.

Source-JSON contract
--------------------
* When ``install-state.json`` is missing, the migration writes a fresh
  ``InstallState()`` payload.
* When the JSON exists but is structurally legacy (per
  ``state.service._is_legacy_install_state``), we still ingest the raw
  payload as JSON; downstream readers route through the
  migration-preserving service path.

Per spec-125 D-125-02, the JSON file is **left in place** by this
migration. Deletion is the responsibility of T-1.21 once the readers
are refactored and verification passes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

BODY_SHA256 = "70bbc5967741aba8bd32b5b0a1b9d67ccac8a6081c3cb6fae74797a96a3579e8"

_STATE_REL = Path(".ai-engineering") / "state"
_INSTALL_STATE_FILENAME = "install-state.json"


def _now_iso() -> str:
    """Return an ISO-8601 UTC timestamp suitable for the updated_at column."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _project_root_from_db(conn: sqlite3.Connection) -> Path:
    """Recover the project root from the connection's main DB path.

    state.db lives at ``<root>/.ai-engineering/state/state.db``; walking
    three parents up yields the project root. Falls back to ``cwd``
    when the connection is in-memory (parts of the test suite use
    ``:memory:``-style connections that do not surface a file path).
    """
    row = conn.execute("PRAGMA database_list").fetchone()
    if row is None or not row[2]:
        return Path.cwd()
    db_path = Path(row[2])
    return db_path.parent.parent.parent


def _load_install_state_payload(state_dir: Path) -> dict:
    """Return the install-state JSON payload, falling back to defaults.

    When ``install-state.json`` is absent or unparseable, return the
    JSON-mode dump of a fresh :class:`InstallState`. The lazy import
    avoids circular references with ``state.models``.
    """
    from ai_engineering.state.models import InstallState

    path = state_dir / _INSTALL_STATE_FILENAME
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            # Fall through to the default payload; readers will surface
            # the issue once the refactor lands the doctor probes.
            pass
    return InstallState().model_dump(mode="json")


def _ingest_payload(conn: sqlite3.Connection, payload: dict) -> None:
    """UPSERT the singleton install_state row from *payload*."""
    schema_version = str(payload.get("schema_version", "2.0"))
    vcs_provider = payload.get("vcs_provider")
    installed_at = payload.get("installed_at")

    operational = payload.get("operational_readiness") or {}
    operational_status = (
        operational.get("status") if isinstance(operational, dict) else None
    ) or "pending"

    state_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    updated_at = _now_iso()

    conn.execute(
        """
        INSERT INTO install_state
          (id, schema_version, vcs_provider, installed_at,
           operational_status, state_json, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          schema_version    = excluded.schema_version,
          vcs_provider      = excluded.vcs_provider,
          installed_at      = excluded.installed_at,
          operational_status = excluded.operational_status,
          state_json        = excluded.state_json,
          updated_at        = excluded.updated_at
        """,
        (
            schema_version,
            vcs_provider,
            installed_at,
            operational_status,
            state_json,
            updated_at,
        ),
    )


def apply(conn: sqlite3.Connection) -> None:
    """Create the install_state table and seed the singleton row."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS install_state (
          id                  INTEGER PRIMARY KEY CHECK (id = 1),
          schema_version      TEXT NOT NULL,
          vcs_provider        TEXT,
          installed_at        TEXT,
          operational_status  TEXT NOT NULL,
          state_json          TEXT NOT NULL,
          updated_at          TEXT NOT NULL
        ) STRICT
        """
    )

    project_root = _project_root_from_db(conn)
    state_dir = project_root / _STATE_REL
    payload = _load_install_state_payload(state_dir)
    _ingest_payload(conn, payload)


__all__ = ["BODY_SHA256", "apply"]
