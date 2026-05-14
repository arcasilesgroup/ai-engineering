"""Add ``details_json`` blob column to the ``decisions`` table.

The canonical state.db ``decisions`` table mirrors the scalar fields
(decision_id, spec_id, status, title, rationale, context, consequences,
superseded_by, expires_at, created_at, updated_at). The legacy Pydantic
``Decision`` model carries additional fields that callers in
``risk_cmd``, ``gate``, ``maintenance``, ``policy.orchestrator`` and the
installer still rely on: ``risk_category``, ``severity``, ``accepted_by``,
``follow_up_action``, ``renewed_from``, ``renewal_count``, ``finding_id``,
``batch_id``, ``prev_event_hash``, ``context_hash``, ``source``,
``decided_at``.

Rather than expanding the scalar surface with eleven additional columns
that only the legacy view-model consumes, this migration adds a single
``details_json TEXT`` column that stores the full Pydantic payload.

``DurableStateRepository.save_decisions`` writes the canonical scalars
through :func:`upsert_decision_rows` and the full payload into
``details_json``. ``load_decisions`` projects from the table back into
the ``DecisionStore`` view-model.

Idempotent contract
-------------------
``PRAGMA table_info`` is used to skip the ALTER when the column already
exists -- safe to re-run.
"""

from __future__ import annotations

import sqlite3

BODY_SHA256 = "6c07044a58d4b230b0c5a66bd7ebf22f34ae57360a8eacf8400d3ea17d7bf8b2"


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return ``True`` iff ``column`` is present on ``table``."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def apply(conn: sqlite3.Connection) -> None:
    """Add ``details_json TEXT`` to ``decisions`` when absent."""
    if _column_exists(conn, "decisions", "details_json"):
        return
    conn.execute("ALTER TABLE decisions ADD COLUMN details_json TEXT")


__all__ = ["BODY_SHA256", "apply"]
