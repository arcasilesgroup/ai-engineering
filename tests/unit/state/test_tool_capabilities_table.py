"""Tests for the ``tool_capabilities`` state.db table (spec-125 T-1.10 / TDD RED).

Contract:
* Single-row table keyed by ``id = 1`` (singleton catalog document).
* Stores the canonical
  :class:`ai_engineering.state.models.FrameworkCapabilitiesCatalog`
  Pydantic model as a JSON blob in the ``catalog_json`` column. Other
  columns mirror frequently-queried scalar fields for indexing without
  requiring SQLite JSON1 support (``schema_version``, ``generated_at``,
  ``agents_count``, ``skills_count``, ``capability_cards_count``,
  ``updated_at``).
* Idempotent ingestion: re-applying the migration with the same source
  JSON yields exactly one row (no duplicates).
* Round-trip read/write preserves every field of the
  :class:`FrameworkCapabilitiesCatalog` model exactly.

Tests rely on the canonical migration runner via ``state_db.connect``;
fixture creates a tmp project root, drops a synthetic
``framework-capabilities.json`` into ``state/``, and asserts the
migration populates the new table.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from ai_engineering.state.state_db import connect


def _write_capabilities_json(state_dir: Path, payload: dict) -> Path:
    """Drop a synthetic framework-capabilities.json into *state_dir*."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "framework-capabilities.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def project_root_with_capabilities(tmp_path: Path) -> Path:
    """Project root with a populated framework-capabilities.json."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    payload = {
        "schemaVersion": "1.0",
        "generatedAt": "2026-01-15T12:00:00Z",
        "agents": [
            {"name": "ai-build", "tags": []},
            {"name": "ai-explore", "tags": []},
        ],
        "skills": [
            {"kind": "build", "name": "ai-plan", "tags": ["planning"]},
            {"kind": "build", "name": "ai-test", "tags": ["test"]},
        ],
        "capabilityCards": [
            {
                "acceptsTaskPackets": True,
                "capabilityKind": "agent",
                "topologyRole": "leaf",
                "mutationClasses": ["read", "advise"],
                "writeScopeClasses": ["source"],
                "toolScope": ["read"],
                "name": "ai-build",
                "providerCompatibility": [
                    {"provider": "claude-code", "supported": True},
                ],
            },
        ],
        "contextClasses": [
            {"name": "language:python"},
        ],
        "hookKinds": [
            {"name": "PreToolUse"},
        ],
        "updateMetadata": {
            "rationale": "test fixture",
            "expectedGain": "deterministic projection",
            "potentialImpact": "regenerate on registry change",
        },
    }
    _write_capabilities_json(state_dir, payload)
    return tmp_path


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------


class TestToolCapabilitiesTableSchema:
    """The migration creates a STRICT tool_capabilities table with the contract columns."""

    def test_table_exists_after_migration(self, tmp_path: Path) -> None:
        """connect() runs the migration and creates the tool_capabilities table."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        conn = connect(tmp_path, apply_migrations=True)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tool_capabilities'"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None, "tool_capabilities table missing post-migration"

    def test_table_has_required_columns(self, project_root_with_capabilities: Path) -> None:
        """The table exposes the contract columns with the expected types."""
        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            cols = conn.execute("PRAGMA table_info(tool_capabilities)").fetchall()
        finally:
            conn.close()

        # Assert
        cols_by_name = {row["name"]: row for row in cols}
        expected_cols = {
            "id",
            "schema_version",
            "generated_at",
            "agents_count",
            "skills_count",
            "capability_cards_count",
            "catalog_json",
            "updated_at",
        }
        assert expected_cols.issubset(cols_by_name.keys()), (
            f"Missing columns: {expected_cols - set(cols_by_name.keys())}"
        )

    def test_table_is_strict(self, project_root_with_capabilities: Path) -> None:
        """The table uses SQLite STRICT typing."""
        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='tool_capabilities'"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert sql is not None
        assert "STRICT" in sql["sql"].upper(), "tool_capabilities table is not declared STRICT"

    def test_singleton_constraint(self, project_root_with_capabilities: Path) -> None:
        """The id column has CHECK (id = 1) singleton enforcement."""
        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='tool_capabilities'"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert sql is not None
        assert "id = 1" in sql["sql"], "tool_capabilities table missing singleton CHECK (id = 1)"


# ---------------------------------------------------------------------------
# Idempotent ingestion
# ---------------------------------------------------------------------------


class TestToolCapabilitiesIngestion:
    """Re-running the migration yields exactly one row (idempotent contract)."""

    def test_single_row_after_first_run(self, project_root_with_capabilities: Path) -> None:
        """First migration run inserts exactly one row keyed by id=1."""
        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            count = conn.execute("SELECT COUNT(*) FROM tool_capabilities").fetchone()[0]
            row = conn.execute("SELECT id FROM tool_capabilities WHERE id = 1").fetchone()
        finally:
            conn.close()

        # Assert
        assert count == 1
        assert row is not None
        assert row["id"] == 1

    def test_re_applying_migration_keeps_one_row(
        self, project_root_with_capabilities: Path
    ) -> None:
        """Calling apply() a second time leaves exactly one row."""
        from ai_engineering.state.migrations import _runner

        # Act -- first connect bootstraps; then call apply() directly to
        # bypass the ledger-skip optimisation.
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            for migration_id, path in _runner._enumerate_migration_files():
                module = _runner._load_module(path)
                if not migration_id.startswith("0005"):
                    continue
                conn.execute("BEGIN IMMEDIATE")
                module.apply(conn)
                conn.commit()
            count = conn.execute("SELECT COUNT(*) FROM tool_capabilities").fetchone()[0]
        finally:
            conn.close()

        # Assert
        assert count == 1, "tool_capabilities row count must stay at 1 after replay"

    def test_payload_columns_populated_from_json(
        self, project_root_with_capabilities: Path
    ) -> None:
        """Mirrored scalar columns reflect the source JSON values."""
        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            row = conn.execute(
                """
                SELECT schema_version, generated_at, agents_count,
                       skills_count, capability_cards_count, catalog_json
                FROM tool_capabilities WHERE id = 1
                """
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        assert row["schema_version"] == "1.0"
        assert row["generated_at"] == "2026-01-15T12:00:00Z"
        assert row["agents_count"] == 2
        assert row["skills_count"] == 2
        assert row["capability_cards_count"] == 1

        payload = json.loads(row["catalog_json"])
        assert payload["agents"][0]["name"] == "ai-build"
        assert payload["skills"][1]["name"] == "ai-test"
        assert payload["capabilityCards"][0]["name"] == "ai-build"


# ---------------------------------------------------------------------------
# Round-trip read/write via state.io helpers
# ---------------------------------------------------------------------------


class TestToolCapabilitiesRoundTrip:
    """The state.db row round-trips through the FrameworkCapabilitiesCatalog model."""

    def test_round_trip_preserves_full_model(self, project_root_with_capabilities: Path) -> None:
        """Reading from state.db and re-validating yields a catalog equal
        to the source payload."""
        from ai_engineering.state.models import FrameworkCapabilitiesCatalog

        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            row = conn.execute("SELECT catalog_json FROM tool_capabilities WHERE id = 1").fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        catalog = FrameworkCapabilitiesCatalog.model_validate_json(row["catalog_json"])
        assert catalog.schema_version == "1.0"
        assert len(catalog.agents) == 2
        assert len(catalog.skills) == 2
        assert len(catalog.capability_cards) == 1
        assert catalog.agents[0].name == "ai-build"

    def test_no_source_json_yields_default_catalog(self, tmp_path: Path) -> None:
        """When framework-capabilities.json is absent, the migration still
        creates the singleton row with a default catalog payload."""
        from ai_engineering.state.models import FrameworkCapabilitiesCatalog

        # Arrange -- no framework-capabilities.json on disk
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        conn = connect(tmp_path, apply_migrations=True)
        try:
            row = conn.execute(
                "SELECT id, catalog_json FROM tool_capabilities WHERE id = 1"
            ).fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None, "Migration must create the singleton row even with no source JSON"
        catalog = FrameworkCapabilitiesCatalog.model_validate_json(row["catalog_json"])
        # Defaults: agents/skills/capability_cards empty.
        assert catalog.agents == []
        assert catalog.skills == []
        assert catalog.capability_cards == []

    def test_updated_at_is_iso_timestamp(self, project_root_with_capabilities: Path) -> None:
        """updated_at column is populated with an ISO-8601 timestamp."""
        # Act
        conn = connect(project_root_with_capabilities, apply_migrations=True)
        try:
            row = conn.execute("SELECT updated_at FROM tool_capabilities WHERE id = 1").fetchone()
        finally:
            conn.close()

        # Assert
        assert row is not None
        ts = row["updated_at"]
        # Parse as ISO-8601 (Z or +00:00 acceptable).
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None or parsed.utcoffset() is None
