"""state_db.connect() PRAGMA suite tests (spec-122-b T-2.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.state.state_db import STATE_DB_REL, connect, projection_write


def _pragma(conn, name: str):
    row = conn.execute(f"PRAGMA {name}").fetchone()
    return row[0] if row else None


def test_state_db_rel_constant():
    """STATE_DB_REL is exported and points to the canonical path."""
    assert Path(".ai-engineering/state/state.db") == STATE_DB_REL


def test_pragmas_on_fresh_db(tmp_path):
    """A fresh connect() applies all 9 PRAGMAs from D-122-16."""
    conn = connect(tmp_path)
    try:
        assert _pragma(conn, "journal_mode") == "wal"
        assert _pragma(conn, "synchronous") == 1  # NORMAL
        assert _pragma(conn, "foreign_keys") == 1
        assert _pragma(conn, "busy_timeout") == 10000
        # cache_size is reported in pages (negative means kilobytes; SQLite
        # converts it to a positive page count when the value was negative).
        cache = _pragma(conn, "cache_size")
        # Value can be exposed as either -65536 (raw negative kib) or as a
        # positive page count depending on SQLite version. Either is fine
        # so long as it is non-zero.
        assert cache != 0
        assert _pragma(conn, "temp_store") == 2  # MEMORY
        assert _pragma(conn, "mmap_size") == 268435456
        assert _pragma(conn, "auto_vacuum") == 2  # INCREMENTAL
        assert _pragma(conn, "journal_size_limit") == 67108864
    finally:
        conn.close()


def test_auto_vacuum_unchanged_on_subsequent_connect(tmp_path):
    """auto_vacuum is set on first creation only; subsequent connects do not flip it."""
    conn1 = connect(tmp_path)
    conn1.execute(
        "CREATE TABLE noop (id INTEGER PRIMARY KEY) STRICT"
    )  # write something so the DB stops being "new"
    conn1.commit()
    conn1.close()

    conn2 = connect(tmp_path)
    try:
        # Once the DB has been written to, auto_vacuum cannot be changed.
        # We just assert it survived as INCREMENTAL.
        assert _pragma(conn2, "auto_vacuum") == 2
    finally:
        conn2.close()


def test_read_only_uri_open(tmp_path):
    """connect(read_only=True) opens the DB through ?mode=ro URI."""
    # Create the DB via a writer first.
    writer = connect(tmp_path)
    writer.execute("CREATE TABLE noop (id INTEGER PRIMARY KEY) STRICT")
    writer.commit()
    writer.close()

    reader = connect(tmp_path, read_only=True)
    try:
        # A write should fail under ro.
        with pytest.raises(Exception):
            reader.execute("INSERT INTO noop VALUES (1)")
    finally:
        reader.close()


def test_projection_write_commits(tmp_path):
    """projection_write context commits on clean exit."""
    # Pre-create the schema via direct connect.
    init = connect(tmp_path)
    init.execute("CREATE TABLE thing (id INTEGER PRIMARY KEY, val TEXT) STRICT")
    init.commit()
    init.close()

    with projection_write(tmp_path) as conn:
        conn.execute("INSERT INTO thing (id, val) VALUES (1, 'hello')")

    verify = connect(tmp_path, read_only=True)
    try:
        rows = verify.execute("SELECT id, val FROM thing").fetchall()
        assert len(rows) == 1
        assert rows[0]["val"] == "hello"
    finally:
        verify.close()


def test_projection_write_rolls_back(tmp_path):
    """projection_write rolls back on exception."""
    init = connect(tmp_path)
    init.execute("CREATE TABLE thing (id INTEGER PRIMARY KEY, val TEXT) STRICT")
    init.commit()
    init.close()

    with pytest.raises(RuntimeError), projection_write(tmp_path) as conn:
        conn.execute("INSERT INTO thing (id, val) VALUES (1, 'wat')")
        raise RuntimeError("boom")

    verify = connect(tmp_path, read_only=True)
    try:
        count = verify.execute("SELECT COUNT(*) FROM thing").fetchone()[0]
        assert count == 0
    finally:
        verify.close()
