"""Unit tests for provider CLI commands (add, remove, list).

Refactored from 32 @patch decorators to a single mocked_provider_ops fixture.
Tests behavior (exit codes, output), not implementation (mock call counts).

TDD-ready: AAA pattern, centralized fakes, behavior-focused assertions.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.installer.operations import InstallerError

pytestmark = pytest.mark.unit

runner = CliRunner()

# ── Fixture: centralized provider-ops patching ────────────────────────────

_PROVIDER_OPS = {
    "resolve": "ai_engineering.cli_commands.provider.resolve_project_root",
    "add": "ai_engineering.cli_commands.provider.add_provider",
    "remove": "ai_engineering.cli_commands.provider.remove_provider",
    "list": "ai_engineering.cli_commands.provider.list_status",
    "json_mode": "ai_engineering.cli_commands.provider.is_json_mode",
}


class _AiProviderConfig:
    """Lightweight mock for the ai_providers attribute used by provider CLI."""

    def __init__(self, primary: str, enabled: list[str]) -> None:
        self.primary = primary
        self.enabled = enabled


class _FakeManifest:
    """Minimal mock that satisfies provider CLI's `manifest.ai_providers` access."""

    def __init__(self, *providers: str, primary: str = "claude_code") -> None:
        self.ai_providers = _AiProviderConfig(primary=primary, enabled=list(providers))


def _manifest(*providers: str, primary: str = "claude_code") -> _FakeManifest:
    """Build a minimal mock manifest with the given enabled providers."""
    return _FakeManifest(*providers, primary=primary)


@pytest.fixture()
def mocked_provider_ops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> dict[str, MagicMock]:
    """Patch all 5 provider-ops at once. Returns dict of mocks by name.

    Default wiring: resolve -> tmp_path, json_mode -> False.
    Tests override only the mock they care about.
    """
    mocks: dict[str, MagicMock] = {}
    for name, module_path in _PROVIDER_OPS.items():
        mock = MagicMock()
        monkeypatch.setattr(module_path, mock)
        mocks[name] = mock

    mocks["resolve"].return_value = tmp_path
    mocks["json_mode"].return_value = False
    mocks["tmp_path"] = tmp_path  # type: ignore[assignment]
    return mocks


# ── Provider Add ──────────────────────────────────────────────────────────


class TestProviderAddCli:
    """Tests for 'ai-eng provider add' CLI command."""

    def test_add_success(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["add"].return_value = _manifest("claude_code", "github_copilot")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["provider", "add", "github_copilot", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 0
        ops["add"].assert_called_once_with(ops["tmp_path"], "github_copilot")

    def test_add_error(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["add"].side_effect = InstallerError("already enabled")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["provider", "add", "claude_code", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code != 0

    def test_add_json_mode(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["json_mode"].return_value = True
        ops["add"].return_value = _manifest("claude_code", "gemini")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["--json", "provider", "add", "gemini", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 0
        assert "gemini" in result.output

    def test_add_error_json_mode(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["json_mode"].return_value = True
        ops["add"].side_effect = InstallerError("Unknown provider")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["--json", "provider", "add", "unknown", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code != 0


# ── Provider Remove ───────────────────────────────────────────────────────


class TestProviderRemoveCli:
    """Tests for 'ai-eng provider remove' CLI command."""

    def test_remove_success(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["remove"].return_value = _manifest("claude_code")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["provider", "remove", "github_copilot", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 0
        ops["remove"].assert_called_once_with(ops["tmp_path"], "github_copilot")

    def test_remove_last_error(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["remove"].side_effect = InstallerError("Cannot remove the last")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["provider", "remove", "claude_code", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code != 0

    def test_remove_json_mode(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["json_mode"].return_value = True
        ops["remove"].return_value = _manifest("claude_code")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["--json", "provider", "remove", "gemini", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 0

    def test_remove_error_json_mode(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["json_mode"].return_value = True
        ops["remove"].side_effect = InstallerError("not enabled")
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["--json", "provider", "remove", "gemini", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code != 0


# ── Provider List ─────────────────────────────────────────────────────────


class TestProviderListCli:
    """Tests for 'ai-eng provider list' CLI command."""

    def test_list_shows_providers(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["list"].return_value = _manifest("claude_code", "gemini")
        app = create_app()

        # Act
        result = runner.invoke(app, ["provider", "list", "--target", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code == 0

    def test_list_empty(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["list"].return_value = _manifest(primary="")
        app = create_app()

        # Act
        result = runner.invoke(app, ["provider", "list", "--target", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code == 0

    def test_list_not_installed(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["list"].side_effect = InstallerError("Framework not installed")
        app = create_app()

        # Act
        result = runner.invoke(app, ["provider", "list", "--target", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code != 0

    def test_list_json_mode(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["json_mode"].return_value = True
        ops["list"].return_value = _manifest("claude_code")
        app = create_app()

        # Act
        result = runner.invoke(
            app, ["--json", "provider", "list", "--target", str(ops["tmp_path"])]
        )

        # Assert
        assert result.exit_code == 0
        assert "claude_code" in result.output

    def test_list_error_json_mode(self, mocked_provider_ops):
        # Arrange
        ops = mocked_provider_ops
        ops["json_mode"].return_value = True
        ops["list"].side_effect = InstallerError("Framework not installed")
        app = create_app()

        # Act
        result = runner.invoke(
            app, ["--json", "provider", "list", "--target", str(ops["tmp_path"])]
        )

        # Assert
        assert result.exit_code != 0
