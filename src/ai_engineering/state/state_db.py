"""Unified ``state.db`` connection manager (spec-122-b D-122-06, D-122-16).

The framework's persistence is consolidated into a single SQLite database at
``.ai-engineering/state/state.db``. Seven STRICT tables (events, decisions,
risk_acceptances, gate_findings, hooks_integrity, ownership_map,
install_steps) plus a ``_migrations`` ledger live here. The NDJSON
``framework-events.ndjson`` file remains the immutable Article-III
source-of-truth (CQRS read-model split); this DB is a derived projection
that can be rebuilt by replay.

Key contract
------------
* ``connect(project_root, *, read_only=False)`` -- opens (or creates) the
  database with the nine PRAGMAs listed in D-122-16. ``auto_vacuum`` is
  set to ``INCREMENTAL`` (mode 2) only on first creation; subsequent
  connects leave it alone (PRAGMA writes for ``auto_vacuum`` after the
  first page is written are silently ignored, but we explicitly skip
  the no-op for clarity).
* ``projection_write(project_root)`` -- context manager wrapping a
  ``BEGIN IMMEDIATE`` transaction. Commits on clean exit, rolls back
  on exception. Use this for any state-mutating CLI flow.

PRAGMA list (D-122-16)
----------------------
| PRAGMA              | Value      | Rationale                              |
|---------------------|------------|----------------------------------------|
| journal_mode        | WAL        | Concurrent reads + crash-safe writes   |
| synchronous         | NORMAL     | Durable across power loss with WAL     |
| foreign_keys        | ON         | Enforce referential integrity          |
| busy_timeout        | 10000 (ms) | Tolerate ~10s of contention            |
| cache_size          | -65536     | 64 MB negative = KiB                   |
| temp_store          | MEMORY     | RAM-only temp tables                   |
| mmap_size           | 268435456  | 256 MB memory-mapped I/O               |
| auto_vacuum         | INCREMENTAL| Reclaim space without rebuild          |
| journal_size_limit  | 67108864   | 64 MB cap on WAL                       |
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Canonical relative path. Callers compose with their ``project_root``.
STATE_DB_REL = Path(".ai-engineering") / "state" / "state.db"


def state_db_path(project_root: Path) -> Path:
    """Return the absolute ``state.db`` path under ``project_root``."""
    return project_root / STATE_DB_REL


def _apply_pragmas(conn: sqlite3.Connection, *, fresh_db: bool) -> None:
    """Apply the D-122-16 PRAGMA suite. Some are one-shot (auto_vacuum)."""
    cur = conn.cursor()
    # ``auto_vacuum`` only takes effect on a fresh DB (before the first
    # page is written). We set it before any other writes happen.
    if fresh_db:
        cur.execute("PRAGMA auto_vacuum = INCREMENTAL")
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA busy_timeout = 10000")
    cur.execute("PRAGMA cache_size = -65536")
    cur.execute("PRAGMA temp_store = MEMORY")
    cur.execute("PRAGMA mmap_size = 268435456")
    cur.execute("PRAGMA journal_size_limit = 67108864")


def _is_bootstrapped(conn: sqlite3.Connection) -> bool:
    """Return ``True`` when ``state.db`` already carries the migration ledger.

    Idempotency hinges on detecting whether a previous boot already ran
    the migration runner. We check for the ``_migrations`` ledger table
    (created by :func:`ai_engineering.state.migrations._runner._ensure_ledger`)
    rather than any business table so the check stays decoupled from the
    specific schema migrations (additions and re-orderings of business
    tables remain safe).
    """
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='_migrations' LIMIT 1"
    )
    return cur.fetchone() is not None


def connect(
    project_root: Path,
    *,
    read_only: bool = False,
    apply_migrations: bool | None = None,
) -> sqlite3.Connection:
    """Open a connection to ``state.db`` with the D-122-16 PRAGMA suite.

    Lazy bootstrap (spec-123 D-123-13)
    ----------------------------------
    On the first writer call against a missing or empty ``state.db``, the
    connection helper transparently runs the migration runner so the
    seven STRICT business tables, the ``_migrations`` ledger, and the
    NDJSON replay all land before the connection is returned. Subsequent
    calls observe the ledger and skip the runner.

    Args:
        project_root: Project root holding ``.ai-engineering/``.
        read_only: When ``True``, opens the DB via ``mode=ro`` URI so
            concurrent writers cannot accidentally corrupt the read side.
            Read-only mode never triggers the bootstrap; callers expect
            an existing DB.
        apply_migrations: Force-on (``True``) or force-off (``False``) the
            migration runner. Default ``None`` opts into the lazy
            bootstrap: run migrations only when the ledger is missing.

    Returns:
        A configured :class:`sqlite3.Connection`.
    """
    db_path = state_db_path(project_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Treat both 'file missing' and 'file present but 0 bytes' (e.g.
    # touched-by-installer placeholder) as 'fresh DB' so the bootstrap
    # branch fires and PRAGMA auto_vacuum can still take effect before
    # the first write.
    fresh_db = (not db_path.exists()) or db_path.stat().st_size == 0

    if read_only:
        # Use URI form so SQLite honours the read-only flag. Read-only
        # callers never bootstrap; they expect an existing DB.
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    else:
        conn = sqlite3.connect(db_path, timeout=10.0)

    _apply_pragmas(conn, fresh_db=fresh_db and not read_only)
    conn.row_factory = sqlite3.Row

    if read_only:
        return conn

    # Decide whether to invoke the migration runner.
    #
    # * ``apply_migrations=True``  -> always run (legacy callers).
    # * ``apply_migrations=False`` -> never run (tests / explicit skip).
    # * ``apply_migrations=None``  -> lazy: run iff ledger missing.
    if apply_migrations is None:
        should_run = not _is_bootstrapped(conn)
    else:
        should_run = bool(apply_migrations)

    if should_run:
        from ai_engineering.state.migrations import run_pending

        run_pending(conn)
    return conn


@contextmanager
def projection_write(project_root: Path) -> Iterator[sqlite3.Connection]:
    """Context manager opening a write transaction on ``state.db``.

    Begins ``BEGIN IMMEDIATE`` so the writer claims the lock up-front,
    avoiding read-write contention surprises mid-transaction. Commits on
    clean exit, rolls back on exception. Connection is closed at the end.
    """
    conn = connect(project_root, read_only=False, apply_migrations=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


__all__ = [
    "STATE_DB_REL",
    "connect",
    "projection_write",
    "state_db_path",
]
