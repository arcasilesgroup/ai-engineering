"""Unit tests for the CLI setup subcommands.

All platform interactions and keyring operations are mocked.
Tests verify CLI flow logic, user prompts, and state persistence.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands.setup import (
    _read_sonar_organization,
    _read_sonar_project_key,
    _read_sonar_url_from_properties,
    _state_dir,
    setup_app,
)
from ai_engineering.credentials.models import PlatformKind

runner = CliRunner()
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project root with `.ai-engineering/state/`."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------
# state_dir helper
# ---------------------------------------------------------------


class TestStateDir:
    """Tests for the _state_dir helper."""

    def test_returns_state_path(self, tmp_path: Path) -> None:
        result = _state_dir(tmp_path)
        assert result == tmp_path / ".ai-engineering" / "state"


# ---------------------------------------------------------------
# sonar-project.properties readers
# ---------------------------------------------------------------


class TestSonarPropertiesReaders:
    """Tests for reading sonar-project.properties."""

    def test_read_url_from_properties(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.host.url=https://sonarcloud.io\n", encoding="utf-8")
        assert _read_sonar_url_from_properties(tmp_path) == "https://sonarcloud.io"

    def test_read_url_missing_file(self, tmp_path: Path) -> None:
        assert _read_sonar_url_from_properties(tmp_path) == ""

    def test_read_url_no_host_key(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-proj\n", encoding="utf-8")
        assert _read_sonar_url_from_properties(tmp_path) == ""

    def test_read_project_key(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-proj\n", encoding="utf-8")
        assert _read_sonar_project_key(tmp_path) == "my-proj"

    def test_read_project_key_missing_file(self, tmp_path: Path) -> None:
        assert _read_sonar_project_key(tmp_path) == ""

    def test_read_organization(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.organization=my-org\n", encoding="utf-8")
        assert _read_sonar_organization(tmp_path) == "my-org"

    def test_read_organization_missing_file(self, tmp_path: Path) -> None:
        assert _read_sonar_organization(tmp_path) == ""


# ---------------------------------------------------------------
# setup platforms command
# ---------------------------------------------------------------


class TestSetupPlatforms:
    """Tests for the `platforms` subcommand."""

    @patch("ai_engineering.cli_commands.setup.detect_platforms", return_value=[])
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_no_platforms_detected(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path
        result = runner.invoke(setup_app, ["platforms"])
        assert "No platform markers auto-detected" in result.output

    @patch("ai_engineering.cli_commands.setup._run_github_setup")
    @patch(
        "ai_engineering.cli_commands.setup.detect_platforms",
        return_value=[PlatformKind.GITHUB],
    )
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_detected_calls_setup(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        mock_github: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path
        runner.invoke(setup_app, ["platforms"])
        mock_github.assert_called_once_with(tmp_path)


# ---------------------------------------------------------------
# setup github command
# ---------------------------------------------------------------


class TestSetupGitHub:
    """Tests for the `github` subcommand."""

    @patch("ai_engineering.cli_commands.setup._run_github_setup")
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_invokes_github_setup(
        self,
        mock_resolve: MagicMock,
        mock_github: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path
        runner.invoke(setup_app, ["github"])
        mock_github.assert_called_once_with(tmp_path)


# ---------------------------------------------------------------
# setup sonar command
# ---------------------------------------------------------------


class TestSetupSonar:
    """Tests for the `sonar` subcommand."""

    @patch("ai_engineering.cli_commands.setup._run_sonar_setup")
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_invokes_sonar_setup(
        self,
        mock_resolve: MagicMock,
        mock_sonar: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path
        runner.invoke(setup_app, ["sonar"])
        mock_sonar.assert_called_once()

    @patch("ai_engineering.cli_commands.setup._run_sonar_setup")
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_passes_organization_option(
        self,
        mock_resolve: MagicMock,
        mock_sonar: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path
        runner.invoke(setup_app, ["sonar", "--organization", "my-org"])
        mock_sonar.assert_called_once_with(
            tmp_path,
            url_override=None,
            project_key_override=None,
            organization_override="my-org",
        )


# ---------------------------------------------------------------
# setup azure-devops command
# ---------------------------------------------------------------


class TestSetupAzureDevOps:
    """Tests for the `azure-devops` subcommand."""

    @patch("ai_engineering.cli_commands.setup._run_azure_devops_setup")
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_invokes_azure_devops_setup(
        self,
        mock_resolve: MagicMock,
        mock_azdo: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path
        runner.invoke(setup_app, ["azure-devops"])
        mock_azdo.assert_called_once()
