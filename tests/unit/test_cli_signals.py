"""Unit tests for ai_engineering.cli_commands.signals_cmd module.

Tests the signals emit CLI command using the Typer CLI runner
with temporary audit log files.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


class TestSignalsEmit:
    """Tests for `ai-eng signals emit`."""

    def test_emit_basic_event(self, tmp_path: Path) -> None:
        """Emit a simple event and verify it was written to the audit log."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "scan_complete"],
            )
        assert result.exit_code == 0
        assert "Emitted: scan_complete by cli" in result.output

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8").strip()
        entry = json.loads(content)
        assert entry["event"] == "scan_complete"
        assert entry["actor"] == "cli"

    def test_emit_with_actor(self, tmp_path: Path) -> None:
        """Emit with custom --actor flag."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "gate_result", "--actor", "build-agent"],
            )
        assert result.exit_code == 0
        assert "Emitted: gate_result by build-agent" in result.output

    def test_emit_with_detail_json(self, tmp_path: Path) -> None:
        """Emit with --detail JSON payload."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        detail = json.dumps({"result": "pass", "score": 100})
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "gate_result", "--detail", detail],
            )
        assert result.exit_code == 0

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["detail"]["result"] == "pass"
        assert entry["detail"]["score"] == 100

    def test_emit_with_source(self, tmp_path: Path) -> None:
        """Emit with --source associates the event source."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "build_complete", "--source", "hook"],
            )
        assert result.exit_code == 0

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["source"] == "hook"

    def test_emit_invalid_detail_json(self, tmp_path: Path) -> None:
        """Invalid JSON in --detail produces exit code 1."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "scan_complete", "--detail", "NOT JSON"],
            )
        assert result.exit_code != 0

    def test_emit_empty_detail_becomes_none(self, tmp_path: Path) -> None:
        """Emit with empty detail JSON {} stores no detail (None)."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "scan_complete", "--detail", "{}"],
            )
        assert result.exit_code == 0

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        # detail is {} which is falsy, so model gets detail=None → excluded from dump
        assert "detail" not in entry
