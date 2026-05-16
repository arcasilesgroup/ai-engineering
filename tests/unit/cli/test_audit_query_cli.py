"""Unit tests for ``ai-eng audit query`` (spec-120 T-B3).

Covers:

* SELECT queries succeed and produce tabular human output
* Non-SELECT statements (DROP, UPDATE, DELETE, INSERT) exit code 2
* ``--json`` emits a JSON array of dicts
* The index is auto-built when missing or stale
* The default ``LIMIT 1000`` cap is appended when the user omits LIMIT
* The user's explicit LIMIT is preserved (not double-capped)

Each test pins ``cwd`` to a fresh ``tmp_path`` so the project's real
``framework-events.ndjson`` is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.audit_index import NDJSON_REL, index_path

runner = CliRunner()


def _seed_ndjson(project_root: Path, events: list[dict]) -> None:
    """Drop a tiny synthetic NDJSON under ``project_root``."""
    target = project_root / NDJSON_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    target.write_text(body, encoding="utf-8")


def _event(
    *,
    skill: str = "ai-brainstorm",
    kind: str = "skill_invoked",
    span_id: str = "abcdef0123456789",
) -> dict:
    """Tiny synthetic event with a usage block; suitable for COUNT/GROUP BY."""
    return {
        "kind": kind,
        "engine": "claude_code",
        "timestamp": "2026-05-04T01:00:00Z",
        "component": "hook.telemetry-skill",
        "outcome": "success",
        "correlationId": f"corr-{span_id}",
        "schemaVersion": "1.0",
        "project": "test-120",
        "spanId": span_id,
        "sessionId": "session-test-120",
        "detail": {
            "skill": skill,
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-sonnet-4-5"},
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "cost_usd": 0.001,
                },
            },
        },
    }


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Anchor cwd at ``tmp_path`` so the audit CLI sees a fresh root."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _seed_indexed_events(project_root: Path, events: list[dict]) -> None:
    """Seed the NDJSON and force a fresh build of the SQLite index."""
    _seed_ndjson(project_root, events)
    # Pre-build via the CLI so the test mirrors a real warm cache run.
    runner.invoke(create_app(), ["audit", "index"])


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_query_select_count(project_root: Path) -> None:
    """COUNT(*) returns the number of seeded rows in tabular form."""
    _seed_indexed_events(
        project_root,
        [_event(span_id=f"span-{i:016d}") for i in range(5)],
    )

    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT COUNT(*) AS n FROM events"],
    )
    assert result.exit_code == 0, result.output
    assert "n" in result.output  # column header
    assert "5" in result.output


def test_query_json_mode(project_root: Path) -> None:
    """``--json`` emits a JSON array of dicts keyed by column name."""
    _seed_indexed_events(
        project_root,
        [_event(skill="ai-brainstorm", span_id=f"span-{i:016d}") for i in range(3)],
    )
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT kind, COUNT(*) AS n FROM events GROUP BY kind", "--json"],
    )
    assert result.exit_code == 0, result.output
    # Find the JSON array in the output (banners + suppressed output above it).
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    parsed = json.loads(last_json)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["kind"] == "skill_invoked"
    assert parsed[0]["n"] == 3


def test_query_auto_builds_index_when_missing(project_root: Path) -> None:
    """Running ``audit query`` without a prior index build still works."""
    _seed_ndjson(project_root, [_event(span_id="span-aaaaaaaaaaaaaaaa")])
    # NB: we deliberately did NOT pre-call ``audit index``.
    assert not index_path(project_root).exists()

    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT COUNT(*) AS n FROM events"],
    )
    assert result.exit_code == 0, result.output
    assert "1" in result.output
    assert index_path(project_root).exists()


# ---------------------------------------------------------------------------
# SELECT-only enforcement
# ---------------------------------------------------------------------------


def test_query_rejects_non_select(project_root: Path) -> None:
    """``DROP TABLE events`` exits with code 2 and an explanatory error."""
    _seed_indexed_events(project_root, [_event()])
    result = runner.invoke(
        create_app(),
        ["audit", "query", "DROP TABLE events"],
    )
    assert result.exit_code == 2, result.output
    # Error message is on stderr; CliRunner merges by default.
    assert "SELECT" in result.output


def test_query_rejects_update(project_root: Path) -> None:
    """``UPDATE events SET ...`` exits with code 2."""
    _seed_indexed_events(project_root, [_event()])
    result = runner.invoke(
        create_app(),
        ["audit", "query", "UPDATE events SET kind='owned'"],
    )
    assert result.exit_code == 2, result.output


def test_query_rejects_delete(project_root: Path) -> None:
    """``DELETE FROM events`` exits with code 2."""
    _seed_indexed_events(project_root, [_event()])
    result = runner.invoke(
        create_app(),
        ["audit", "query", "DELETE FROM events"],
    )
    assert result.exit_code == 2, result.output


# ---------------------------------------------------------------------------
# LIMIT injection
# ---------------------------------------------------------------------------


def test_query_respects_default_limit(project_root: Path) -> None:
    """Default LIMIT 1000 is appended when the user omits LIMIT."""
    # 5 rows, default limit 1000 -> all 5 returned.
    _seed_indexed_events(
        project_root,
        [_event(span_id=f"span-{i:016d}") for i in range(5)],
    )
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT span_id FROM events", "--json"],
    )
    assert result.exit_code == 0, result.output
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    rows = json.loads(last_json)
    assert len(rows) == 5


def test_query_respects_explicit_limit(project_root: Path) -> None:
    """When the user supplies LIMIT, it is preserved (not overridden)."""
    _seed_indexed_events(
        project_root,
        [_event(span_id=f"span-{i:016d}") for i in range(5)],
    )
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT span_id FROM events LIMIT 2", "--json"],
    )
    assert result.exit_code == 0, result.output
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    rows = json.loads(last_json)
    assert len(rows) == 2


def test_query_caps_default_limit_to_flag_value(project_root: Path) -> None:
    """``--limit 2`` overrides the 1000 default when no LIMIT is in the query."""
    _seed_indexed_events(
        project_root,
        [_event(span_id=f"span-{i:016d}") for i in range(5)],
    )
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT span_id FROM events", "--json", "--limit", "2"],
    )
    assert result.exit_code == 0, result.output
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    rows = json.loads(last_json)
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------


def test_query_no_rows_human(project_root: Path) -> None:
    """A query with no matches prints ``(no rows)`` in human mode."""
    _seed_indexed_events(project_root, [_event(skill="ai-x", span_id="span-aaaaaaaaaaaaaaaa")])
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT * FROM events WHERE kind='nonexistent'"],
    )
    assert result.exit_code == 0, result.output
    assert "(no rows)" in result.output


def test_query_missing_index_returns_empty(project_root: Path) -> None:
    """No NDJSON + no SQLite -> ``(no rows)`` (or ``[]`` in JSON)."""
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT 1"],
    )
    assert result.exit_code == 0, result.output
    assert "(no rows)" in result.output


def test_query_sql_error_exits_one(project_root: Path) -> None:
    """A SELECT against a missing table surfaces the SQLite error."""
    _seed_indexed_events(project_root, [_event()])
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT * FROM does_not_exist"],
    )
    assert result.exit_code == 1, result.output
    assert "no such table" in result.output.lower()


def test_query_missing_index_returns_empty_json(project_root: Path) -> None:
    """No NDJSON + no SQLite + ``--json`` -> ``[]`` array on stdout."""
    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT 1", "--json"],
    )
    assert result.exit_code == 0, result.output
    last_line = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    assert last_line.strip() == "[]"


def test_query_rejects_empty_string(project_root: Path) -> None:
    """An entirely blank SQL argument exits with code 2."""
    _seed_indexed_events(project_root, [_event()])
    result = runner.invoke(
        create_app(),
        ["audit", "query", "   "],
    )
    assert result.exit_code == 2, result.output


def test_query_accepts_select_with_leading_comment(project_root: Path) -> None:
    """``-- comment\\nSELECT ...`` is accepted (comments stripped first).

    The ``--`` separator below tells Typer/Click "stop parsing options" so
    the SQL string -- which itself begins with ``--`` -- is captured as a
    positional argument rather than interpreted as a CLI flag.
    """
    _seed_indexed_events(project_root, [_event()])
    result = runner.invoke(
        create_app(),
        [
            "audit",
            "query",
            "--",
            "-- audit log query for kind counts\nSELECT COUNT(*) AS n FROM events",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1" in result.output


def test_query_skips_rebuild_when_index_fresh(project_root: Path) -> None:
    """Pre-built index newer than NDJSON is reused (no rebuild)."""
    import time

    _seed_indexed_events(project_root, [_event()])
    # Touch the SQLite to make sure its mtime is strictly greater than the
    # NDJSON mtime, exercising the "fresh -> skip build" branch.
    time.sleep(0.01)
    sqlite_path = index_path(project_root)
    sqlite_path.touch()

    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT COUNT(*) AS n FROM events"],
    )
    assert result.exit_code == 0, result.output
    assert "1" in result.output


def test_query_succeeds_when_ndjson_disappears_after_index(project_root: Path) -> None:
    """Index built earlier still serves queries after NDJSON is removed.

    Exercises the ``_index_is_stale`` ``ndjson missing -> not stale``
    branch -- the CLI must not blow up if the source NDJSON is later
    deleted or rotated.
    """
    _seed_indexed_events(project_root, [_event()])
    (project_root / NDJSON_REL).unlink()

    result = runner.invoke(
        create_app(),
        ["audit", "query", "SELECT COUNT(*) AS n FROM events"],
    )
    assert result.exit_code == 0, result.output
    assert "1" in result.output
