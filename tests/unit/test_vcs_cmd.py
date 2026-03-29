"""Unit tests for VCS CLI commands (status, set-primary).

Follows the test_provider_cli.py pattern: CliRunner + monkeypatch fixture.
Tests behavior (exit codes, output), not implementation.

TDD-ready: AAA pattern, centralized fakes, behavior-focused assertions.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()

# -- Fixture: centralized VCS-ops patching ------------------------------------

_VCS_OPS = {
    "resolve": "ai_engineering.cli_commands.vcs.resolve_project_root",
    "load_manifest": "ai_engineering.cli_commands.vcs.load_manifest_config",
    "get_provider": "ai_engineering.cli_commands.vcs.get_provider",
    "update_field": "ai_engineering.cli_commands.vcs.update_manifest_field",
    "json_mode": "ai_engineering.cli_commands.vcs.is_json_mode",
}


class _FakeProviders:
    """Minimal mock for ManifestConfig.providers."""

    def __init__(self, vcs: str = "github") -> None:
        self.vcs = vcs


class _FakeManifest:
    """Minimal mock that satisfies VCS CLI's ManifestConfig access."""

    def __init__(self, vcs: str = "github") -> None:
        self.providers = _FakeProviders(vcs=vcs)


def _make_provider_mock(name: str = "github", available: bool = True) -> MagicMock:
    """Build a MagicMock that satisfies the VCS provider interface."""
    mock = MagicMock()
    mock.provider_name.return_value = name
    mock.is_available.return_value = available
    return mock


@pytest.fixture()
def mocked_vcs_ops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> dict[str, MagicMock]:
    """Patch all VCS-ops at once. Returns dict of mocks by name.

    Default wiring: resolve -> tmp_path, json_mode -> False,
    load_manifest -> _FakeManifest(), get_provider -> github/available.
    Tests override only the mock they care about.
    """
    mocks: dict[str, MagicMock] = {}
    for name, module_path in _VCS_OPS.items():
        mock = MagicMock()
        monkeypatch.setattr(module_path, mock)
        mocks[name] = mock

    mocks["resolve"].return_value = tmp_path
    mocks["json_mode"].return_value = False
    mocks["load_manifest"].return_value = _FakeManifest()
    mocks["get_provider"].return_value = _make_provider_mock()
    mocks["tmp_path"] = tmp_path  # type: ignore[assignment]
    return mocks


# -- VCS Status ---------------------------------------------------------------


class TestVcsStatusCli:
    """Tests for 'ai-eng vcs status' CLI command."""

    def test_status_success_human_mode(self, mocked_vcs_ops):
        # Arrange
        ops = mocked_vcs_ops
        (ops["tmp_path"] / ".ai-engineering").mkdir()
        app = create_app()

        # Act
        result = runner.invoke(app, ["vcs", "status", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code == 0

    def test_status_no_framework_exits_1(self, mocked_vcs_ops):
        # Arrange -- no .ai-engineering dir
        ops = mocked_vcs_ops
        app = create_app()

        # Act
        result = runner.invoke(app, ["vcs", "status", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code == 1

    def test_status_json_mode_success(self, mocked_vcs_ops):
        # Arrange
        ops = mocked_vcs_ops
        ops["json_mode"].return_value = True
        (ops["tmp_path"] / ".ai-engineering").mkdir()
        app = create_app()

        # Act
        result = runner.invoke(app, ["--json", "vcs", "status", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code == 0
        assert "primary_provider" in result.output

    def test_status_no_framework_json(self, mocked_vcs_ops):
        # Arrange -- no .ai-engineering dir, JSON mode
        ops = mocked_vcs_ops
        ops["json_mode"].return_value = True
        app = create_app()

        # Act
        result = runner.invoke(app, ["--json", "vcs", "status", str(ops["tmp_path"])])

        # Assert
        assert result.exit_code == 1
        assert "NO_FRAMEWORK" in result.output


# -- VCS Set-Primary ----------------------------------------------------------


class TestVcsSetPrimaryCli:
    """Tests for 'ai-eng vcs set-primary' CLI command."""

    def test_set_primary_success(self, mocked_vcs_ops):
        # Arrange
        ops = mocked_vcs_ops
        (ops["tmp_path"] / ".ai-engineering").mkdir()
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["vcs", "set-primary", "github", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 0
        ops["update_field"].assert_called_once_with(ops["tmp_path"], "providers.vcs", "github")

    def test_set_primary_azdo_alias(self, mocked_vcs_ops):
        # Arrange
        ops = mocked_vcs_ops
        (ops["tmp_path"] / ".ai-engineering").mkdir()
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["vcs", "set-primary", "azdo", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 0
        ops["update_field"].assert_called_once_with(
            ops["tmp_path"], "providers.vcs", "azure_devops"
        )

    def test_set_primary_invalid_exits_1(self, mocked_vcs_ops):
        # Arrange
        ops = mocked_vcs_ops
        (ops["tmp_path"] / ".ai-engineering").mkdir()
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["vcs", "set-primary", "bitbucket", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 1

    def test_set_primary_no_framework_exits_1(self, mocked_vcs_ops):
        # Arrange -- no .ai-engineering dir
        ops = mocked_vcs_ops
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            ["vcs", "set-primary", "github", "--target", str(ops["tmp_path"])],
        )

        # Assert
        assert result.exit_code == 1

    def test_set_primary_json_mode(self, mocked_vcs_ops):
        # Arrange
        ops = mocked_vcs_ops
        ops["json_mode"].return_value = True
        (ops["tmp_path"] / ".ai-engineering").mkdir()
        app = create_app()

        # Act
        result = runner.invoke(
            app,
            [
                "--json",
                "vcs",
                "set-primary",
                "github",
                "--target",
                str(ops["tmp_path"]),
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "provider" in result.output
