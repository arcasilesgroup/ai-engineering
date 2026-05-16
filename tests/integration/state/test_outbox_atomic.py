"""Transactional outbox tests (spec-122-b T-2.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ai_engineering.state.outbox import (
    OutboxReentrantError,
    projection_write,
)
from ai_engineering.state.state_db import connect


@pytest.fixture
def state_root(tmp_path):
    """Bootstrap state.db with the initial schema applied."""
    conn = connect(tmp_path, apply_migrations=True)
    conn.close()
    return tmp_path


def _capture_emitter(captured: list[tuple[str, dict[str, Any]]]):
    def emitter(project_root: Path, kind: str, payload: dict[str, Any]) -> None:
        captured.append((kind, dict(payload)))

    return emitter


def test_success_path_commits_and_emits(state_root):
    """Clean exit commits SQL and emits buffered NDJSON events."""
    captured: list[tuple[str, dict[str, Any]]] = []
    with projection_write(state_root, emitter=_capture_emitter(captured)) as (conn, outbox):
        conn.execute(
            "INSERT INTO ownership_map (path_pattern, owners_json, updated_at) VALUES (?, ?, ?)",
            ("src/foo/**", '["@alice"]', "2026-05-05T00:00:00Z"),
        )
        outbox.queue("ownership_updated", {"path_pattern": "src/foo/**"})

    # SQL row is committed.
    verify = connect(state_root, read_only=True)
    try:
        rows = verify.execute("SELECT path_pattern FROM ownership_map").fetchall()
        assert len(rows) == 1
        assert rows[0]["path_pattern"] == "src/foo/**"
    finally:
        verify.close()

    # Event was emitted.
    assert len(captured) == 1
    assert captured[0][0] == "ownership_updated"


def test_sql_failure_rolls_back_and_skips_emit(state_root):
    """An exception inside the body rolls back SQL and discards events."""
    captured: list[tuple[str, dict[str, Any]]] = []
    with pytest.raises(RuntimeError, match="boom"):  # noqa: SIM117
        with projection_write(state_root, emitter=_capture_emitter(captured)) as (
            conn,
            outbox,
        ):
            conn.execute(
                "INSERT INTO ownership_map (path_pattern, owners_json, updated_at) "
                "VALUES (?, ?, ?)",
                ("src/bar/**", '["@bob"]', "2026-05-05T00:00:00Z"),
            )
            outbox.queue("ownership_updated", {"path_pattern": "src/bar/**"})
            raise RuntimeError("boom")

    verify = connect(state_root, read_only=True)
    try:
        count = verify.execute(
            "SELECT COUNT(*) FROM ownership_map WHERE path_pattern = ?",
            ("src/bar/**",),
        ).fetchone()[0]
        assert count == 0
    finally:
        verify.close()
    assert captured == [], "rollback path must skip NDJSON emit"


def test_emit_failure_after_commit_raises_but_row_persists(state_root):
    """A post-commit emitter failure surfaces but does not undo the SQL."""

    def failing_emitter(project_root: Path, kind: str, payload: dict[str, Any]) -> None:
        raise RuntimeError("emit failed")

    with pytest.raises(RuntimeError, match="emit failed"):  # noqa: SIM117
        with projection_write(state_root, emitter=failing_emitter) as (conn, outbox):
            conn.execute(
                "INSERT INTO ownership_map (path_pattern, owners_json, updated_at) "
                "VALUES (?, ?, ?)",
                ("src/baz/**", '["@carol"]', "2026-05-05T00:00:00Z"),
            )
            outbox.queue("ownership_updated", {"path_pattern": "src/baz/**"})

    # SQL row IS committed (at-least-once after commit).
    verify = connect(state_root, read_only=True)
    try:
        count = verify.execute(
            "SELECT COUNT(*) FROM ownership_map WHERE path_pattern = ?",
            ("src/baz/**",),
        ).fetchone()[0]
        assert count == 1
    finally:
        verify.close()


def test_reentrant_call_raises(state_root):
    """Calling projection_write inside another active call raises immediately."""
    captured: list[tuple[str, dict[str, Any]]] = []

    with pytest.raises(OutboxReentrantError):  # noqa: SIM117
        with projection_write(state_root, emitter=_capture_emitter(captured)):
            with projection_write(state_root, emitter=_capture_emitter(captured)):
                pass
