"""spec-118 T-1.6 -- SQLite store for the memory layer.

Owns connection management, schema bootstrap, and the optional sqlite-vec
extension load. The schema is idempotent (`CREATE TABLE IF NOT EXISTS`) and
versioned via `PRAGMA user_version`.

Design notes:
    * `memory.db` lives at `.ai-engineering/state/memory.db` (gitignored).
    * `vec0` virtual table is created on first call to `ensure_vector_table()`
      so the rest of the module is usable on systems where sqlite-vec is not
      installed yet (Phase 1 needs the schema; Phase 3 turns on embeddings).
    * Every `connect()` opens a fresh connection in WAL journal mode with
      foreign keys enforced.
    * The module is stdlib-only.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MEMORY_DB_REL = Path(".ai-engineering") / "state" / "memory.db"
SCHEMA_VERSION = 1
DEFAULT_EMBEDDING_DIM = 384

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA foreign_keys = ON",
    f"PRAGMA user_version = {SCHEMA_VERSION}",
    """
    CREATE TABLE IF NOT EXISTS episodes (
        episode_id        TEXT PRIMARY KEY,
        session_id        TEXT NOT NULL,
        started_at        TEXT NOT NULL,
        ended_at          TEXT NOT NULL,
        duration_sec      INTEGER NOT NULL CHECK (duration_sec >= 0),
        plane        TEXT,
        active_specs      TEXT NOT NULL DEFAULT '[]',
        tools_used        TEXT NOT NULL DEFAULT '{}',
        skill_invocations TEXT NOT NULL DEFAULT '[]',
        agents_dispatched TEXT NOT NULL DEFAULT '[]',
        files_touched     TEXT NOT NULL DEFAULT '[]',
        outcomes          TEXT NOT NULL DEFAULT '{}',
        summary           TEXT NOT NULL,
        importance        REAL NOT NULL DEFAULT 0.5,
        last_seen_at      TEXT NOT NULL,
        retrieval_count   INTEGER NOT NULL DEFAULT 0,
        embedding_status  TEXT NOT NULL DEFAULT 'pending'
            CHECK (embedding_status IN ('pending', 'complete', 'failed')),
        schema_version    TEXT NOT NULL DEFAULT '1.0'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_episodes_started ON episodes(started_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_episodes_plane ON episodes(plane)",
    """
    CREATE TABLE IF NOT EXISTS knowledge_objects (
        ko_hash         TEXT PRIMARY KEY,
        canonical_text  TEXT NOT NULL,
        kind            TEXT NOT NULL CHECK (kind IN
                          ('lesson','decision','correction','recovery','workflow','spec_delta','custom')),
        source_path     TEXT NOT NULL,
        source_anchor   TEXT,
        metadata        TEXT NOT NULL DEFAULT '{}',
        importance      REAL NOT NULL DEFAULT 0.5
            CHECK (importance >= 0 AND importance <= 1),
        created_at      TEXT NOT NULL,
        last_seen_at    TEXT NOT NULL,
        retrieval_count INTEGER NOT NULL DEFAULT 0,
        superseded_by   TEXT REFERENCES knowledge_objects(ko_hash) ON DELETE SET NULL,
        archived        INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0,1)),
        schema_version  TEXT NOT NULL DEFAULT '1.0'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ko_kind ON knowledge_objects(kind) WHERE archived = 0",
    "CREATE INDEX IF NOT EXISTS idx_ko_importance ON knowledge_objects(importance DESC) WHERE archived = 0",
    "CREATE INDEX IF NOT EXISTS idx_ko_source ON knowledge_objects(source_path)",
    "CREATE INDEX IF NOT EXISTS idx_ko_superseded ON knowledge_objects(superseded_by) WHERE superseded_by IS NOT NULL",
    """
    CREATE TABLE IF NOT EXISTS vector_map (
        rowid           INTEGER PRIMARY KEY AUTOINCREMENT,
        target_kind     TEXT NOT NULL CHECK (target_kind IN ('episode','knowledge_object')),
        target_id       TEXT NOT NULL,
        embedding_model TEXT NOT NULL,
        embedding_dim   INTEGER NOT NULL CHECK (embedding_dim > 0),
        created_at      TEXT NOT NULL,
        -- (model, dim) are coupled: rebuild-vectors must replace both. Without
        -- this, INSERT OR IGNORE keeps the old row when an operator hand-changes
        -- the dim, and the vec0 virtual table (created with the old dim) silently
        -- truncates / zero-pads new vectors depending on the sqlite-vec version.
        UNIQUE (target_kind, target_id, embedding_model)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_vmap_target ON vector_map(target_kind, target_id)",
    """
    CREATE TABLE IF NOT EXISTS retrieval_log (
        retrieval_id   TEXT PRIMARY KEY,
        query_text     TEXT NOT NULL,
        query_hash     TEXT NOT NULL,
        session_id     TEXT,
        requested_at   TEXT NOT NULL,
        top_k          INTEGER NOT NULL,
        kind_filter    TEXT,
        since_filter   TEXT,
        results        TEXT NOT NULL,
        duration_ms    INTEGER NOT NULL,
        schema_version TEXT NOT NULL DEFAULT '1.0'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_retrieval_session ON retrieval_log(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_retrieval_time ON retrieval_log(requested_at DESC)",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def db_path(project_root: Path) -> Path:
    """Resolve the canonical memory.db path."""
    return project_root / MEMORY_DB_REL


def _try_load_vec0(conn: sqlite3.Connection) -> bool:
    """Best-effort load of the sqlite-vec extension.

    Returns True if vec0 is available, False otherwise. Callers that need vec0
    must check the return value; the bootstrap path keeps working without it.

    Defense-in-depth: after vec0 loads we install a SQL authorizer that
    refuses any further `load_extension` calls on the connection. Even if a
    future code path were to inject SQL containing `SELECT load_extension(...)`,
    the authorizer denies it and the connection raises rather than picking up
    an attacker-controlled shared object via LD_LIBRARY_PATH.
    """
    try:
        conn.enable_load_extension(True)
    except sqlite3.NotSupportedError:
        return False
    loaded = False
    try:
        import sqlite_vec  # type: ignore[import-not-found]

        sqlite_vec.load(conn)
        loaded = True
    except Exception:
        loaded = False
    finally:
        try:
            conn.enable_load_extension(False)
        except sqlite3.NotSupportedError:
            pass
    if loaded:
        try:
            conn.set_authorizer(_deny_further_load_extension)
        except (sqlite3.NotSupportedError, AttributeError):
            pass
    return loaded


def _deny_further_load_extension(action_code, arg1, arg2, db_name, trigger_name):
    """SQL authorizer that denies any further extension loading on this conn."""
    if action_code == sqlite3.SQLITE_FUNCTION and arg2 in {
        "load_extension",
        "sqlite3_load_extension",
    }:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def ensure_vector_table(conn: sqlite3.Connection, *, dim: int = DEFAULT_EMBEDDING_DIM) -> bool:
    """Create the `memory_vectors` virtual table when vec0 is available.

    The vector dimension is recorded in `vector_map.embedding_dim`; callers
    must invoke this once per dim. Re-creating with a different dim is the
    operator's responsibility (D-118-06: refuse-to-start on dim mismatch).
    """
    if not _try_load_vec0(conn):
        return False
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0("
        f"rowid INTEGER PRIMARY KEY, embedding FLOAT[{dim}])"
    )
    return True


def bootstrap(project_root: Path) -> Path:
    """Ensure `memory.db` exists with the canonical schema.

    Idempotent: re-running on an already-bootstrapped database is safe.
    Returns the absolute path to the database file.
    """
    path = db_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(project_root) as conn:
        for stmt in _SCHEMA_STATEMENTS:
            conn.execute(stmt)
        conn.commit()
    return path


@contextmanager
def connect(project_root: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection in WAL mode with foreign keys enforced."""
    path = db_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        conn.close()


def schema_version(conn: sqlite3.Connection) -> int:
    """Return the current `PRAGMA user_version`."""
    cur = conn.execute("PRAGMA user_version")
    row = cur.fetchone()
    return int(row[0]) if row else 0
