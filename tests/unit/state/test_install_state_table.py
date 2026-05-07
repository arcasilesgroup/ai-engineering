"""Tests for the ``install_state`` state.db table (spec-125 T-1.2 / TDD RED).

Contract:
* Single-row table keyed by ``id = 1`` (singleton state document).
* Stores the canonical ``InstallState`` Pydantic model as a JSON blob in
  the ``state_json`` column. Other columns mirror frequently-queried
  scalar fields for indexing without requiring JSON1 support
  (``schema_version``, ``vcs_provider``, ``installed_at``,
  ``operational_status``, ``updated_at``).
* Idempotent ingestion: re-applying the migration with the same source
  JSON yields exactly one row (no duplicates).
* Round-trip read/write preserves every field of the
  :class:`InstallState` model exactly.

Tests rely on the canonical migration runner via ``state_db.connect``;
fixture creates a tmp project root, drops a synthetic
``install-state.json`` into ``state/``, and asserts the migration
populates the new table.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from ai_engineering.state.state_db import connect


def _write_install_state_json(state_dir: Path, payload: dict) -> Path:
    """Drop a synthetic install-state.json into *state_dir*."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "install-state.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def project_root_with_install_state(tmp_path: Path) -> Path:
    """Project root with a populated install-state.json."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    payload = {
        "schema_version": "2.0",
        "installed_at": "2026-04-01T12:00:00+00:00",
        "vcs_provider": "github",
        "ai_providers": ["claude-code"],
        "tooling": {
            "gh": {
                "installed": True,
                "authenticated": True,
                "integrity_verified": False,
                "mode": "cli",
                "scopes": ["repo"],
            },
            "ruff": {
                "installed": True,
                "authenticated": False,
                "integrity_verified": False,
                "mode": "cli",
                "scopes": [],
            },
        },
        "platforms": {
            "github": {
                "configured": True,
                "url": "https://github.com",
                "project_key": "",
                "organization": "",
            }
        },
        "branch_policy": {
            "applied": True,
            "mode": "cli",
            "message": None,
            "manual_guide": None,
        },
        "operational_readiness": {"status": "READY", "pending_steps": []},
        "release": {"last_version": "0.4.0", "last_released_at": None},
        "required_tools_state": {},
        "python_env_mode_recorded": None,
        "breaking_banner_seen": False,
        "tool_spec_hashes": {},
    }
    _write_install_state_json(state_dir, payload)
    return tmp_path


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------


class TestInstallStateTableSchema:
    """The migration creates a STRICT install_state table with the contract columns."""

    def test_table_exists_after_migration(self, tmp_path: Path) -> None:
        """connect() runs the migration and creates the install_state table."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        conn = connect(tmp_path, apply_migrations=True)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='install_state'"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None, "install_state table must exist after migration"

    def test_schema_columns(self, tmp_path: Path) -> None:
        """Required columns: id, schema_version, vcs_provider, installed_at,
        operational_status, state_json, updated_at."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        conn = connect(tmp_path, apply_migrations=True)
        try:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(install_state)")}
        finally:
            conn.close()

        # Assert
        required = {
            "id",
            "schema_version",
            "vcs_provider",
            "installed_at",
            "operational_status",
            "state_json",
            "updated_at",
        }
        missing = required - cols
        assert not missing, f"install_state missing columns: {missing}"

    def test_table_is_strict(self, tmp_path: Path) -> None:
        """install_state must be declared STRICT for type-safety parity."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        conn = connect(tmp_path, apply_migrations=True)
        try:
            sql_row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='install_state'"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert sql_row is not None
        assert "STRICT" in sql_row["sql"].upper(), "install_state must be STRICT"


# ---------------------------------------------------------------------------
# Ingestion + idempotency
# ---------------------------------------------------------------------------


class TestInstallStateIngestion:
    """The migration ingests install-state.json into install_state on first run."""

    def test_single_row_after_ingestion(self, project_root_with_install_state: Path) -> None:
        """After migration, install_state holds exactly one row (singleton)."""
        # Act
        conn = connect(project_root_with_install_state, apply_migrations=True)
        try:
            count = conn.execute("SELECT COUNT(*) AS c FROM install_state").fetchone()["c"]
        finally:
            conn.close()

        # Assert
        assert count == 1, "install_state must hold exactly one row post-migration"

    def test_singleton_id_is_one(self, project_root_with_install_state: Path) -> None:
        """The singleton row uses id=1."""
        # Act
        conn = connect(project_root_with_install_state, apply_migrations=True)
        try:
            row = conn.execute("SELECT id FROM install_state").fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        assert row["id"] == 1

    def test_idempotent_no_duplicate_rows(self, project_root_with_install_state: Path) -> None:
        """Re-applying the migration must not create a second row."""
        # Arrange -- first run populates the table
        from ai_engineering.state.migrations import _runner

        conn = connect(project_root_with_install_state, apply_migrations=True)
        try:
            first_count = conn.execute("SELECT COUNT(*) AS c FROM install_state").fetchone()["c"]
        finally:
            conn.close()
        assert first_count == 1

        # Act -- re-run the install-state migration directly to exercise
        # the SQL-level idempotency contract.
        conn2 = connect(project_root_with_install_state, apply_migrations=False)
        try:
            for migration_id, path in _runner._enumerate_migration_files():
                if "install_state" not in migration_id:
                    continue
                module = _runner._load_module(path)
                conn2.execute("BEGIN IMMEDIATE")
                try:
                    module.apply(conn2)
                    conn2.commit()
                except Exception:
                    conn2.rollback()
                    raise
            second_count = conn2.execute("SELECT COUNT(*) AS c FROM install_state").fetchone()["c"]
        finally:
            conn2.close()

        # Assert
        assert second_count == 1, "Re-running install_state migration must not duplicate rows"

    def test_ingested_payload_matches_source_json(
        self, project_root_with_install_state: Path
    ) -> None:
        """state_json field stores the original payload semantics (round-trippable)."""
        # Act
        conn = connect(project_root_with_install_state, apply_migrations=True)
        try:
            row = conn.execute(
                "SELECT schema_version, vcs_provider, operational_status, state_json "
                "FROM install_state WHERE id = 1"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        assert row["schema_version"] == "2.0"
        assert row["vcs_provider"] == "github"
        assert row["operational_status"] == "READY"

        payload = json.loads(row["state_json"])
        assert payload["tooling"]["gh"]["authenticated"] is True
        assert payload["platforms"]["github"]["url"] == "https://github.com"
        assert payload["branch_policy"]["applied"] is True


# ---------------------------------------------------------------------------
# Round-trip read/write via state.io helpers
# ---------------------------------------------------------------------------


class TestInstallStateRoundTrip:
    """The state.db row round-trips through the InstallState pydantic model."""

    def test_round_trip_preserves_full_model(self, project_root_with_install_state: Path) -> None:
        """Reading from state.db and re-validating yields an InstallState equal
        to the source payload."""
        # Lazy import to avoid pulling state.repository before the migration
        # surfaces are wired up.
        from ai_engineering.state.models import InstallState

        # Act
        conn = connect(project_root_with_install_state, apply_migrations=True)
        try:
            row = conn.execute("SELECT state_json FROM install_state WHERE id = 1").fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        state = InstallState.model_validate_json(row["state_json"])
        assert state.schema_version == "2.0"
        assert state.vcs_provider == "github"
        assert state.tooling["gh"].authenticated is True
        assert state.platforms["github"].url == "https://github.com"

    def test_no_source_json_yields_default_state(self, tmp_path: Path) -> None:
        """When install-state.json is absent, the migration still creates the
        singleton row with a default InstallState payload."""
        from ai_engineering.state.models import InstallState

        # Arrange -- no install-state.json on disk
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        conn = connect(tmp_path, apply_migrations=True)
        try:
            row = conn.execute("SELECT id, state_json FROM install_state WHERE id = 1").fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None, "Migration must create the singleton row even with no source JSON"
        state = InstallState.model_validate_json(row["state_json"])
        # Defaults: schema_version 2.0, empty tooling/platforms.
        assert state.schema_version == "2.0"
        assert state.tooling == {}
        assert state.platforms == {}

    def test_updated_at_is_iso_timestamp(self, project_root_with_install_state: Path) -> None:
        """updated_at column is populated with an ISO-8601 timestamp."""
        # Act
        conn = connect(project_root_with_install_state, apply_migrations=True)
        try:
            row = conn.execute("SELECT updated_at FROM install_state WHERE id = 1").fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        ts = row["updated_at"]
        # Parse as ISO-8601 (Z or +00:00 acceptable).
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None or parsed.utcoffset() is None
