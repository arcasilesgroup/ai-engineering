"""Unit tests for ai_engineering.cli_commands.decisions_cmd module.

Tests the decision list and expire-check CLI commands using the
Typer CLI runner with temporary state files.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


def _make_decision_store(root: Path, decisions: list[dict]) -> None:
    """Write a decision-store.json file under the .ai-engineering/state dir."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {"schemaVersion": "1.1", "decisions": decisions}
    (state_dir / "decision-store.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_decision(**overrides: object) -> dict:
    """Return a minimal valid decision dict with optional overrides."""
    base = {
        "id": "DEC-001",
        "context": "Some context for the decision that might be rather long",
        "decision": "We decided to accept this risk for now",
        "decidedAt": "2025-01-01T00:00:00Z",
        "spec": "spec-001",
        "severity": "medium",
        "status": "active",
    }
    base.update(overrides)
    return base


class TestDecisionList:
    """Tests for `ai-eng decision list`."""

    def test_empty_store_no_file(self, tmp_path: Path) -> None:
        """When no decision-store.json exists, report empty."""
        # Arrange
        (tmp_path / ".ai-engineering").mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_empty_decisions_list(self, tmp_path: Path) -> None:
        """When decisions list is empty, report empty."""
        # Arrange
        _make_decision_store(tmp_path, [])

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_lists_single_decision(self, tmp_path: Path) -> None:
        """A single decision is printed with ID, status, severity, and expiry."""
        # Arrange
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt="2026-06-01T00:00:00Z")],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "DEC-001" in result.output
        assert "active" in result.output
        assert "medium" in result.output
        assert "2026-06-01" in result.output
        assert "1 total" in result.output

    def test_lists_multiple_decisions(self, tmp_path: Path) -> None:
        """Multiple decisions are all printed."""
        # Arrange
        _make_decision_store(
            tmp_path,
            [
                _base_decision(id="DEC-001"),
                _base_decision(id="DEC-002", severity="high", status="expired"),
            ],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "DEC-001" in result.output
        assert "DEC-002" in result.output
        assert "2 total" in result.output

    def test_decision_no_expiry(self, tmp_path: Path) -> None:
        """Decision without expiresAt shows 'no expiry'."""
        # Arrange
        _make_decision_store(tmp_path, [_base_decision()])

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "no expiry" in result.output

    def test_decision_no_severity(self, tmp_path: Path) -> None:
        """Decision without severity shows '?'."""
        # Arrange
        dec = _base_decision()
        del dec["severity"]
        _make_decision_store(tmp_path, [dec])

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "?" in result.output

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        """Corrupt decision-store.json is treated as empty."""
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "decision-store.json").write_text("NOT JSON", encoding="utf-8")

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        # Assert
        assert result.exit_code == 0
        assert "empty" in result.output.lower()


class TestDecisionExpireCheck:
    """Tests for `ai-eng decision expire-check`."""

    def test_no_decisions_to_check(self, tmp_path: Path) -> None:
        """When no decision-store.json exists, report nothing to check."""
        # Arrange
        (tmp_path / ".ai-engineering").mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "No decisions to check" in result.output

    def test_all_active_within_validity(self, tmp_path: Path) -> None:
        """Active decisions with far-future expiry are fine."""
        # Arrange
        future = (datetime.now(tz=UTC) + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt=future)],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_expired_decision_detected(self, tmp_path: Path) -> None:
        """A decision with expiry in the past is flagged as EXPIRED."""
        # Arrange
        past = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt=past)],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "EXPIRED" in result.output
        assert "DEC-001" in result.output

    def test_expiring_soon_detected(self, tmp_path: Path) -> None:
        """A decision expiring within 7 days is flagged as EXPIRING SOON."""
        # Arrange
        soon = (datetime.now(tz=UTC) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt=soon)],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "EXPIRING SOON" in result.output
        assert "DEC-001" in result.output

    def test_non_active_decisions_skipped(self, tmp_path: Path) -> None:
        """Decisions with status != 'active' are not checked for expiry."""
        # Arrange
        past = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(status="expired", expiresAt=past)],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_active_no_expiry_skipped(self, tmp_path: Path) -> None:
        """Active decisions without expiresAt are skipped in expire-check."""
        # Arrange
        _make_decision_store(
            tmp_path,
            [_base_decision()],  # no expiresAt
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_mixed_expired_and_expiring(self, tmp_path: Path) -> None:
        """Both EXPIRED and EXPIRING SOON sections appear when applicable."""
        # Arrange
        past = (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        soon = (datetime.now(tz=UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [
                _base_decision(id="DEC-001", expiresAt=past),
                _base_decision(id="DEC-002", expiresAt=soon),
            ],
        )

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        # Assert
        assert result.exit_code == 0
        assert "EXPIRED" in result.output
        assert "DEC-001" in result.output
        assert "EXPIRING SOON" in result.output
        assert "DEC-002" in result.output


class TestDecisionRecord:
    """Tests for `ai-eng decision record`."""

    def test_record_creates_new_decision(self, tmp_path: Path) -> None:
        """Record creates decision-store.json with the new entry."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-001",
                    "--context",
                    "test context",
                    "--decision",
                    "test decision",
                    "--spec",
                    "spec-034",
                ],
            )

        # Assert
        assert result.exit_code == 0
        assert "Recorded" in result.output
        assert "d-test-001" in result.output
        store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
        assert store_path.exists()
        data = json.loads(store_path.read_text())
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["id"] == "d-test-001"
        assert data["decisions"][0]["status"] == "active"

    def test_record_appends_to_existing_store(self, tmp_path: Path) -> None:
        """Record appends to an existing store without losing entries."""
        # Arrange
        _make_decision_store(tmp_path, [_base_decision(id="DEC-001")])

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-002",
                    "--context",
                    "new context",
                    "--decision",
                    "new decision",
                ],
            )

        # Assert
        assert result.exit_code == 0
        data = json.loads(
            (tmp_path / ".ai-engineering" / "state" / "decision-store.json").read_text()
        )
        assert len(data["decisions"]) == 2

    def test_record_rejects_duplicate_id(self, tmp_path: Path) -> None:
        """Record fails when the ID already exists."""
        # Arrange
        _make_decision_store(tmp_path, [_base_decision(id="DEC-001")])

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "DEC-001",
                    "--context",
                    "dup",
                    "--decision",
                    "dup",
                ],
            )

        # Assert
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_record_with_severity_and_category(self, tmp_path: Path) -> None:
        """Record stores optional severity and category."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-003",
                    "--context",
                    "risk ctx",
                    "--decision",
                    "accept risk",
                    "--severity",
                    "high",
                    "--category",
                    "risk-acceptance",
                ],
            )

        # Assert
        assert result.exit_code == 0
        data = json.loads(
            (tmp_path / ".ai-engineering" / "state" / "decision-store.json").read_text()
        )
        entry = data["decisions"][0]
        assert entry["severity"] == "high"
        assert entry["riskCategory"] == "risk-acceptance"

    def test_record_with_expires(self, tmp_path: Path) -> None:
        """Record stores expiry date."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-004",
                    "--context",
                    "ctx",
                    "--decision",
                    "dec",
                    "--expires",
                    "2026-01-15",
                ],
            )

        # Assert
        assert result.exit_code == 0
        data = json.loads(
            (tmp_path / ".ai-engineering" / "state" / "decision-store.json").read_text()
        )
        assert "2026-01-15" in data["decisions"][0]["expiresAt"]

    def test_record_emits_audit_signal(self, tmp_path: Path) -> None:
        """Record writes an audit-log entry (dual-write)."""
        # Arrange
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-005",
                    "--context",
                    "ctx",
                    "--decision",
                    "dec",
                ],
            )

        # Assert
        audit_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        assert audit_path.exists()
        line = audit_path.read_text().strip()
        audit = json.loads(line)
        assert audit["event"] == "decision_recorded"
        assert "d-test-005" in audit["detail"]["message"]
