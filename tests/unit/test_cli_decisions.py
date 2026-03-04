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
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_empty_decisions_list(self, tmp_path: Path) -> None:
        """When decisions list is empty, report empty."""
        _make_decision_store(tmp_path, [])
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_lists_single_decision(self, tmp_path: Path) -> None:
        """A single decision is printed with ID, status, severity, and expiry."""
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt="2026-06-01T00:00:00Z")],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "DEC-001" in result.output
        assert "active" in result.output
        assert "medium" in result.output
        assert "2026-06-01" in result.output
        assert "1 total" in result.output

    def test_lists_multiple_decisions(self, tmp_path: Path) -> None:
        """Multiple decisions are all printed."""
        _make_decision_store(
            tmp_path,
            [
                _base_decision(id="DEC-001"),
                _base_decision(id="DEC-002", severity="high", status="expired"),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "DEC-001" in result.output
        assert "DEC-002" in result.output
        assert "2 total" in result.output

    def test_decision_no_expiry(self, tmp_path: Path) -> None:
        """Decision without expiresAt shows 'no expiry'."""
        _make_decision_store(tmp_path, [_base_decision()])
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "no expiry" in result.output

    def test_decision_no_severity(self, tmp_path: Path) -> None:
        """Decision without severity shows '?'."""
        dec = _base_decision()
        del dec["severity"]
        _make_decision_store(tmp_path, [dec])
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "?" in result.output

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        """Corrupt decision-store.json is treated as empty."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "decision-store.json").write_text("NOT JSON", encoding="utf-8")
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()


class TestDecisionExpireCheck:
    """Tests for `ai-eng decision expire-check`."""

    def test_no_decisions_to_check(self, tmp_path: Path) -> None:
        """When no decision-store.json exists, report nothing to check."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "No decisions to check" in result.output

    def test_all_active_within_validity(self, tmp_path: Path) -> None:
        """Active decisions with far-future expiry are fine."""
        future = (datetime.now(tz=UTC) + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt=future)],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_expired_decision_detected(self, tmp_path: Path) -> None:
        """A decision with expiry in the past is flagged as EXPIRED."""
        past = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt=past)],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "EXPIRED" in result.output
        assert "DEC-001" in result.output

    def test_expiring_soon_detected(self, tmp_path: Path) -> None:
        """A decision expiring within 7 days is flagged as EXPIRING SOON."""
        soon = (datetime.now(tz=UTC) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(expiresAt=soon)],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "EXPIRING SOON" in result.output
        assert "DEC-001" in result.output

    def test_non_active_decisions_skipped(self, tmp_path: Path) -> None:
        """Decisions with status != 'active' are not checked for expiry."""
        past = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [_base_decision(status="expired", expiresAt=past)],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_active_no_expiry_skipped(self, tmp_path: Path) -> None:
        """Active decisions without expiresAt are skipped in expire-check."""
        _make_decision_store(
            tmp_path,
            [_base_decision()],  # no expiresAt
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_mixed_expired_and_expiring(self, tmp_path: Path) -> None:
        """Both EXPIRED and EXPIRING SOON sections appear when applicable."""
        past = (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        soon = (datetime.now(tz=UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _make_decision_store(
            tmp_path,
            [
                _base_decision(id="DEC-001", expiresAt=past),
                _base_decision(id="DEC-002", expiresAt=soon),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.decisions_cmd._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])
        assert result.exit_code == 0
        assert "EXPIRED" in result.output
        assert "DEC-001" in result.output
        assert "EXPIRING SOON" in result.output
        assert "DEC-002" in result.output
