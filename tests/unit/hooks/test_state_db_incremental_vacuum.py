"""Unit tests for ``runtime-session-end.py`` ``state.db incremental_vacuum``.

spec-139 M6.T5 (third test). Asserts that the ``_incremental_vacuum_if_needed``
helper in ``runtime-session-end.py``:

1. Runs ``PRAGMA incremental_vacuum`` when ``freelist_count > 1000``.
2. Returns ``None`` (no-op) when ``freelist_count <= 1000``.
3. Returns ``None`` (no-op) when the DB file is absent.
4. Returns ``None`` (no-op) when the DB file is corrupt / unreadable.

We exercise the helper directly with a tmp_path SQLite DB seeded with a
synthetic freelist. ``auto_vacuum = INCREMENTAL`` is set at creation so
the subsequent ``DELETE`` populates the freelist (otherwise SQLite would
free the pages eagerly).
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / ".ai-engineering" / "scripts" / "hooks"


def _load_session_end():
    sys.path.insert(0, str(HOOKS))
    sys.modules.pop("aieng_runtime_session_end_vacuum", None)
    spec = importlib.util.spec_from_file_location(
        "aieng_runtime_session_end_vacuum",
        HOOKS / "runtime-session-end.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def session_end_mod():
    return _load_session_end()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _build_db_with_freelist(db_path: Path, *, target_pages: int) -> int:
    """Create a state.db at ``db_path`` whose freelist exceeds ``target_pages``.

    Returns the actual ``freelist_count`` after build so tests can sanity
    check the fixture before exercising the helper.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        # Mode 2 = INCREMENTAL. MUST be set BEFORE any tables are created
        # (auto_vacuum is sticky after the first page is written).
        conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("CREATE TABLE big (id INTEGER PRIMARY KEY, blob BLOB)")
        # Each row carries ~3 KB of data; with 4 KB pages this means roughly
        # one page per row. We insert generously so a subsequent DELETE
        # populates a freelist that exceeds the requested target.
        payload = b"x" * 3072
        rows = max(target_pages * 2, 50)
        conn.executemany(
            "INSERT INTO big (blob) VALUES (?)",
            [(payload,) for _ in range(rows)],
        )
        # DELETE all rows so the pages move to the freelist (INCREMENTAL
        # mode keeps them around until PRAGMA incremental_vacuum is run).
        conn.execute("DELETE FROM big")
        # Force a checkpoint so the freelist count reflects post-DELETE state.
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        row = conn.execute("PRAGMA freelist_count").fetchone()
        return int(row[0] or 0) if row else 0
    finally:
        conn.close()


def test_vacuum_runs_when_freelist_exceeds_threshold(session_end_mod, project: Path) -> None:
    """freelist_count > 1000 → PRAGMA incremental_vacuum executes and reclaims pages."""
    db_path = project / ".ai-engineering" / "state" / "state.db"
    actual_freelist = _build_db_with_freelist(db_path, target_pages=1100)
    # Fixture sanity check — if the seed builder did not produce > 1000
    # pages, the assertion below is meaningless. Skip rather than mask the
    # real bug.
    if actual_freelist <= 1000:
        pytest.skip(f"fixture produced freelist={actual_freelist}, need >1000 to exercise the gate")

    result = session_end_mod._incremental_vacuum_if_needed(project)

    assert result is not None, "vacuum should have run when freelist > 1000"
    # SQLite version drift caveat: the freelist count seen by the fixture
    # (``PRAGMA freelist_count`` AFTER ``PRAGMA wal_checkpoint(FULL)`` in
    # ``_build_db_with_freelist``) and the count seen by the helper after
    # re-opening the DB on a fresh connection can differ by a small
    # bookkeeping margin on macOS 3.12/3.13 (SQLite 3.45+). The contract
    # the test is asserting is "the helper observed > 1000 freelist pages
    # and ran the vacuum"; pinning equality to the fixture's snapshot
    # over-constrains the assertion and produces host-dependent flakes.
    threshold = session_end_mod._VACUUM_FREELIST_THRESHOLD
    assert result["before"] > threshold, (
        f"helper should have observed freelist > {threshold}; "
        f"got before={result['before']} (fixture saw {actual_freelist})"
    )
    assert result["after"] < result["before"], "freelist should shrink after vacuum"
    assert result["reclaimed"] == result["before"] - result["after"]
    assert result["reclaimed"] > 0


def test_vacuum_skips_when_freelist_below_threshold(session_end_mod, project: Path) -> None:
    """freelist_count <= 1000 → helper returns None (no-op)."""
    db_path = project / ".ai-engineering" / "state" / "state.db"
    # Small DB whose freelist will stay under 1000 even after the seed
    # DELETE. Five rows of ~1 page each -> freelist ~5 pages, well under
    # the 1000 threshold.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("CREATE TABLE small (id INTEGER PRIMARY KEY, blob BLOB)")
        conn.executemany(
            "INSERT INTO small (blob) VALUES (?)",
            [(b"x" * 256,) for _ in range(5)],
        )
        conn.execute("DELETE FROM small")
        row = conn.execute("PRAGMA freelist_count").fetchone()
        freelist_before = int(row[0] or 0) if row else 0
    finally:
        conn.close()
    assert freelist_before <= 1000, (
        f"fixture sanity: expected freelist <=1000, got {freelist_before}"
    )

    result = session_end_mod._incremental_vacuum_if_needed(project)

    assert result is None, "vacuum should have skipped when freelist <= 1000"


def test_vacuum_skips_when_db_absent(session_end_mod, project: Path) -> None:
    """Missing ``state.db`` → helper returns None (no-op, no traceback)."""
    db_path = project / ".ai-engineering" / "state" / "state.db"
    assert not db_path.exists(), "fixture sanity: tmp_path should not have a state.db"

    result = session_end_mod._incremental_vacuum_if_needed(project)

    assert result is None


def test_vacuum_skips_on_corrupt_db(session_end_mod, project: Path) -> None:
    """Corrupt ``state.db`` → helper returns None without raising."""
    db_path = project / ".ai-engineering" / "state" / "state.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Random bytes that decidedly do NOT form a valid SQLite header.
    db_path.write_bytes(b"not a sqlite database, just garbage" * 16)

    result = session_end_mod._incremental_vacuum_if_needed(project)

    assert result is None
