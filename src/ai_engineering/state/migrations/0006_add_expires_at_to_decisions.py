"""Add ``expires_at`` column to the ``decisions`` table.

Restores the expiry-aware behaviour the legacy Pydantic ``Decision``
model carried. ``decision expire-check`` queries this column directly;
risk acceptances, gate-policy enforcement, and the installer's "active
acceptance for finding" lookups all read it via the canonical
projection.

The column is nullable (TEXT) so existing rows are valid post-migration
without backfill. Callers that need an "any expiry" semantics use
``expires_at IS NOT NULL``.

Idempotent contract
-------------------
* The migration is wrapped in a ``CREATE TABLE IF NOT EXISTS`` no-op +
  ``PRAGMA table_info`` introspection. If ``expires_at`` already exists
  on the table (re-run, manual ALTER, schema dump replay) the migration
  is a no-op.
"""

from __future__ import annotations

import sqlite3

BODY_SHA256 = "6795aa4da985ca5536a8272e5173918f5078eca1fb7dcdef8ea50079d402ed3e"


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return ``True`` iff ``column`` is present on ``table``."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def apply(conn: sqlite3.Connection) -> None:
    """Add ``expires_at TEXT`` to ``decisions`` when absent."""
    if _column_exists(conn, "decisions", "expires_at"):
        return
    conn.execute("ALTER TABLE decisions ADD COLUMN expires_at TEXT")


__all__ = ["BODY_SHA256", "apply"]
