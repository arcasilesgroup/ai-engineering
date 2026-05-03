"""spec-118 T-2.6 -- store.py schema bootstrap and idempotency."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.memory


def test_bootstrap_creates_db(memory_project):
    from memory import store

    path = store.bootstrap(memory_project)
    assert path.exists()
    assert path == store.db_path(memory_project)


def test_bootstrap_is_idempotent(memory_project):
    from memory import store

    store.bootstrap(memory_project)
    store.bootstrap(memory_project)  # second call must not raise
    with store.connect(memory_project) as conn:
        assert store.schema_version(conn) == 1


def test_schema_version_pragma(memory_project):
    from memory import store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        assert store.schema_version(conn) == store.SCHEMA_VERSION


def test_episodes_table_exists(memory_project):
    from memory import store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cur.fetchall()}
    expected = {"episodes", "knowledge_objects", "vector_map", "retrieval_log"}
    assert expected.issubset(tables)


def test_foreign_keys_enabled(memory_project):
    from memory import store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn:
        cur = conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1


def test_ko_kind_check_rejects_unknown(memory_project):
    """The CHECK constraint on knowledge_objects.kind must reject novel kinds."""
    import sqlite3

    from memory import store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
                INSERT INTO knowledge_objects
                    (ko_hash, canonical_text, kind, source_path, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
            (
                "a" * 64,
                "x",
                "UNKNOWN_KIND",
                "p",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )


def test_episode_duration_check_rejects_negative(memory_project):
    import sqlite3

    from memory import store

    store.bootstrap(memory_project)
    with store.connect(memory_project) as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
                INSERT INTO episodes
                    (episode_id, session_id, started_at, ended_at, duration_sec,
                     summary, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
            (
                "e1",
                "s1",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
                -1,
                "x",
                "2026-01-01T00:00:00Z",
            ),
        )
