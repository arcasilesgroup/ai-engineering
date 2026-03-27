"""CLI regression tests for the spec-082 observability reset."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


class TestLegacyCommandsRemoved:
    def test_help_no_longer_lists_observe_or_signals(self) -> None:
        result = runner.invoke(create_app(), [])
        assert result.exit_code == 0
        assert "observe" not in result.output
        assert "signals" not in result.output

    def test_json_root_command_list_excludes_legacy_observability_commands(self) -> None:
        result = runner.invoke(create_app(), ["--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        commands = payload["result"]["commands"]
        assert "observe" not in commands
        assert "signals" not in commands

    def test_observe_command_is_unknown(self) -> None:
        result = runner.invoke(create_app(), ["observe"])
        assert result.exit_code != 0
        assert "No such command 'observe'" in result.output

    def test_signals_command_is_unknown(self) -> None:
        result = runner.invoke(create_app(), ["signals"])
        assert result.exit_code != 0
        assert "No such command 'signals'" in result.output
