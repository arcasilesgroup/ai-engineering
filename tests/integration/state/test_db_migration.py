"""End-to-end migration tests (spec-122-b T-2.5 + T-2.6)."""

from __future__ import annotations

import json

import pytest

from ai_engineering.state.state_db import connect


@pytest.fixture
def project_root_with_state(tmp_path):
    """Create a project layout with the four JSON state files."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)

    (state / "decision-store.json").write_text(
        json.dumps(
            {
                "active_decisions": [
                    {
                        "id": "D-001",
                        "spec_id": "spec-001",
                        "status": "active",
                        "title": "Use STRICT tables",
                        "rationale": "Type safety",
                    },
                ],
                "superseded": [],
                "version": "v1",
            }
        ),
        encoding="utf-8",
    )
    (state / "gate-findings.json").write_text(
        json.dumps(
            {
                "schema": "ai-engineering/gate-findings/v1",
                "session_id": "test-session",
                "findings": [
                    {
                        "finding_id": "F-001",
                        "rule_id": "ruff/E501",
                        "severity": "warning",
                        "status": "open",
                        "file_path": "src/foo.py",
                        "line_start": 12,
                        "line_end": 12,
                        "message": "line too long",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (state / "ownership-map.json").write_text(
        json.dumps(
            {
                "paths": [
                    {
                        "pattern": "src/auth/**",
                        "owner": "@security",
                        "frameworkUpdate": "deny",
                    },
                    {
                        "pattern": "docs/**",
                        "owner": "@docs",
                        "frameworkUpdate": "allow",
                    },
                ],
                "schemaVersion": "1.0",
                "updateMetadata": {"updatedAt": "2026-05-05T00:00:00Z"},
            }
        ),
        encoding="utf-8",
    )
    (state / "install-state.json").write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "tooling": {
                    "uv": {"installed": True, "authenticated": True},
                    "ruff": {"installed": True, "authenticated": False},
                    "git_hooks": {
                        "installed": True,
                        "authenticated": True,
                        "scopes": ["pre-commit"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    # NDJSON with two synthetic events.
    ndjson_path = state / "framework-events.ndjson"
    ndjson_path.write_text(
        json.dumps(
            {
                "kind": "framework_operation",
                "engine": "ai_engineering",
                "component": "test",
                "outcome": "success",
                "timestamp": "2026-05-05T00:00:00Z",
                "detail": {"hello": "world"},
            }
        )
        + "\n"
        + json.dumps(
            {
                "kind": "skill_invoked",
                "engine": "ai_engineering",
                "component": "test",
                "outcome": "success",
                "timestamp": "2026-05-05T00:01:00Z",
                "detail": {"skill": "ai-plan"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_round_trip_each_json_file(project_root_with_state):
    """Each JSON file's records show up in the corresponding STRICT table."""
    conn = connect(project_root_with_state, apply_migrations=True)
    try:
        decisions = conn.execute("SELECT decision_id, title FROM decisions").fetchall()
        assert len(decisions) == 1
        assert decisions[0]["decision_id"] == "D-001"

        findings = conn.execute("SELECT finding_id, rule_id FROM gate_findings").fetchall()
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "ruff/E501"

        owners = conn.execute(
            "SELECT path_pattern FROM ownership_map ORDER BY path_pattern"
        ).fetchall()
        assert {row["path_pattern"] for row in owners} == {"src/auth/**", "docs/**"}

        steps = conn.execute(
            "SELECT step_id, status FROM install_steps ORDER BY step_id"
        ).fetchall()
        assert {row["step_id"] for row in steps} == {"git_hooks", "ruff", "uv"}

        events = conn.execute(
            "SELECT span_id, kind, archive_month, ts_unix_ms FROM events ORDER BY ts_unix_ms"
        ).fetchall()
        assert len(events) == 2
        # Generated columns should be populated.
        for row in events:
            assert row["archive_month"] == "2026-05"
            assert row["ts_unix_ms"] > 0
            assert row["span_id"].startswith("synthetic:")
    finally:
        conn.close()


def test_replay_idempotent(project_root_with_state):
    """Re-running migrations produces zero net inserts (idempotency)."""
    conn = connect(project_root_with_state, apply_migrations=True)
    try:
        first_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()

    # Re-run by opening a new connection that goes through run_pending.
    # The migrations are already in _migrations, so run_pending will skip
    # them. To exercise the idempotency contract of the SQL itself, we
    # call apply() directly.
    from ai_engineering.state.migrations import _runner

    conn2 = connect(project_root_with_state)
    try:
        for migration_id, path in _runner._enumerate_migration_files():
            module = _runner._load_module(path)
            apply_fn = module.apply
            try:
                conn2.execute("BEGIN IMMEDIATE")
                apply_fn(conn2)
                conn2.commit()
            except Exception:
                conn2.rollback()
                raise
        second_count = conn2.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn2.close()

    assert first_count == second_count, "ON CONFLICT(span_id) DO NOTHING violated"


def test_event_count_matches_ndjson(project_root_with_state):
    """events row count == NDJSON line count after replay."""
    ndjson = project_root_with_state / ".ai-engineering" / "state" / "framework-events.ndjson"
    expected = len([line for line in ndjson.read_text().splitlines() if line.strip()])

    conn = connect(project_root_with_state, apply_migrations=True)
    try:
        actual = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()
    assert actual == expected
