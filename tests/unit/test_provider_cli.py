"""Unit tests for provider CLI commands (add, remove, list).

Tests the CLI layer using CliRunner with mocked operations.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.installer.operations import InstallerError
from ai_engineering.state.models import AiProviderConfig, InstallManifest

pytestmark = pytest.mark.unit

runner = CliRunner()


def _make_manifest(**overrides: object) -> InstallManifest:
    """Build a minimal InstallManifest with provider config."""
    defaults = {
        "ai_providers": AiProviderConfig(primary="claude_code", enabled=["claude_code"]),
    }
    defaults.update(overrides)
    return InstallManifest(**defaults)  # type: ignore[arg-type]


class TestProviderAddCli:
    """Tests for 'ai-eng provider add' CLI command."""

    @patch("ai_engineering.cli_commands.provider.add_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_add_success(self, mock_resolve, mock_add, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_add.return_value = _make_manifest(
            ai_providers=AiProviderConfig(
                primary="claude_code",
                enabled=["claude_code", "github_copilot"],
            ),
        )
        app = create_app()
        result = runner.invoke(
            app, ["provider", "add", "github_copilot", "--target", str(tmp_path)]
        )
        assert result.exit_code == 0
        mock_add.assert_called_once_with(tmp_path, "github_copilot")

    @patch("ai_engineering.cli_commands.provider.add_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_add_error(self, mock_resolve, mock_add, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_add.side_effect = InstallerError("already enabled")
        app = create_app()
        result = runner.invoke(app, ["provider", "add", "claude_code", "--target", str(tmp_path)])
        assert result.exit_code != 0

    @patch("ai_engineering.cli_commands.provider.add_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    @patch("ai_engineering.cli_commands.provider.is_json_mode", return_value=True)
    def test_add_json_mode(self, _mock_json, mock_resolve, mock_add, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_add.return_value = _make_manifest(
            ai_providers=AiProviderConfig(
                primary="claude_code",
                enabled=["claude_code", "gemini"],
            ),
        )
        app = create_app()
        result = runner.invoke(
            app, ["--json", "provider", "add", "gemini", "--target", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "gemini" in result.output

    @patch("ai_engineering.cli_commands.provider.add_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    @patch("ai_engineering.cli_commands.provider.is_json_mode", return_value=True)
    def test_add_error_json_mode(self, _mock_json, mock_resolve, mock_add, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_add.side_effect = InstallerError("Unknown provider")
        app = create_app()
        result = runner.invoke(
            app,
            ["--json", "provider", "add", "unknown", "--target", str(tmp_path)],
        )
        assert result.exit_code != 0


class TestProviderRemoveCli:
    """Tests for 'ai-eng provider remove' CLI command."""

    @patch("ai_engineering.cli_commands.provider.remove_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_remove_success(self, mock_resolve, mock_remove, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_remove.return_value = _make_manifest(
            ai_providers=AiProviderConfig(
                primary="claude_code",
                enabled=["claude_code"],
            ),
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["provider", "remove", "github_copilot", "--target", str(tmp_path)],
        )
        assert result.exit_code == 0
        mock_remove.assert_called_once_with(tmp_path, "github_copilot")

    @patch("ai_engineering.cli_commands.provider.remove_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_remove_last_error(self, mock_resolve, mock_remove, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_remove.side_effect = InstallerError("Cannot remove the last")
        app = create_app()
        result = runner.invoke(
            app,
            ["provider", "remove", "claude_code", "--target", str(tmp_path)],
        )
        assert result.exit_code != 0

    @patch("ai_engineering.cli_commands.provider.remove_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    @patch("ai_engineering.cli_commands.provider.is_json_mode", return_value=True)
    def test_remove_json_mode(self, _mock_json, mock_resolve, mock_remove, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_remove.return_value = _make_manifest(
            ai_providers=AiProviderConfig(
                primary="claude_code",
                enabled=["claude_code"],
            ),
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["--json", "provider", "remove", "gemini", "--target", str(tmp_path)],
        )
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.provider.remove_provider")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    @patch("ai_engineering.cli_commands.provider.is_json_mode", return_value=True)
    def test_remove_error_json_mode(self, _mock_json, mock_resolve, mock_remove, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_remove.side_effect = InstallerError("not enabled")
        app = create_app()
        result = runner.invoke(
            app,
            ["--json", "provider", "remove", "gemini", "--target", str(tmp_path)],
        )
        assert result.exit_code != 0


class TestProviderListCli:
    """Tests for 'ai-eng provider list' CLI command."""

    @patch("ai_engineering.cli_commands.provider.list_status")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_list_shows_providers(self, mock_resolve, mock_list, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_list.return_value = _make_manifest(
            ai_providers=AiProviderConfig(
                primary="claude_code",
                enabled=["claude_code", "gemini"],
            ),
        )
        app = create_app()
        result = runner.invoke(app, ["provider", "list", "--target", str(tmp_path)])
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.provider.list_status")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_list_empty(self, mock_resolve, mock_list, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_list.return_value = _make_manifest(
            ai_providers=AiProviderConfig(primary="", enabled=[]),
        )
        app = create_app()
        result = runner.invoke(app, ["provider", "list", "--target", str(tmp_path)])
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.provider.list_status")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    def test_list_not_installed(self, mock_resolve, mock_list, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_list.side_effect = InstallerError("Framework not installed")
        app = create_app()
        result = runner.invoke(app, ["provider", "list", "--target", str(tmp_path)])
        assert result.exit_code != 0

    @patch("ai_engineering.cli_commands.provider.list_status")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    @patch("ai_engineering.cli_commands.provider.is_json_mode", return_value=True)
    def test_list_json_mode(self, _mock_json, mock_resolve, mock_list, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_list.return_value = _make_manifest(
            ai_providers=AiProviderConfig(
                primary="claude_code",
                enabled=["claude_code"],
            ),
        )
        app = create_app()
        result = runner.invoke(app, ["--json", "provider", "list", "--target", str(tmp_path)])
        assert result.exit_code == 0
        assert "claude_code" in result.output

    @patch("ai_engineering.cli_commands.provider.list_status")
    @patch("ai_engineering.cli_commands.provider.resolve_project_root")
    @patch("ai_engineering.cli_commands.provider.is_json_mode", return_value=True)
    def test_list_error_json_mode(self, _mock_json, mock_resolve, mock_list, tmp_path):
        mock_resolve.return_value = tmp_path
        mock_list.side_effect = InstallerError("Framework not installed")
        app = create_app()
        result = runner.invoke(app, ["--json", "provider", "list", "--target", str(tmp_path)])
        assert result.exit_code != 0
