"""Unit tests for platform detection and platform setup classes.

Tests use ``tmp_path`` to create various repo layouts and verify
that ``detect_platforms`` returns the correct platforms. Platform
setup classes are tested with mocks for subprocess/HTTP calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.credentials.models import PlatformKind
from ai_engineering.platforms.detector import detect_platforms

pytestmark = pytest.mark.unit


class TestDetectPlatforms:
    """Tests for detect_platforms()."""

    def test_empty_repo_returns_nothing(self, tmp_path: Path) -> None:
        assert detect_platforms(tmp_path) == []

    def test_github_directory_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        result = detect_platforms(tmp_path)
        assert PlatformKind.GITHUB in result

    def test_azure_pipelines_yml_detected(self, tmp_path: Path) -> None:
        (tmp_path / "azure-pipelines.yml").touch()
        result = detect_platforms(tmp_path)
        assert PlatformKind.AZURE_DEVOPS in result

    def test_azuredevops_directory_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".azuredevops").mkdir()
        result = detect_platforms(tmp_path)
        assert PlatformKind.AZURE_DEVOPS in result

    def test_sonar_properties_detected(self, tmp_path: Path) -> None:
        (tmp_path / "sonar-project.properties").touch()
        result = detect_platforms(tmp_path)
        assert PlatformKind.SONAR in result

    def test_multiple_platforms_detected(self, tmp_path: Path) -> None:
        # Arrange
        (tmp_path / ".github").mkdir()
        (tmp_path / "azure-pipelines.yml").touch()
        (tmp_path / "sonar-project.properties").touch()

        # Act
        result = detect_platforms(tmp_path)

        # Assert
        assert len(result) == 3
        assert PlatformKind.GITHUB in result
        assert PlatformKind.AZURE_DEVOPS in result
        assert PlatformKind.SONAR in result

    def test_azure_devops_only_counts_once(self, tmp_path: Path) -> None:
        """Both azure-pipelines.yml and .azuredevops/ → single detection."""
        # Arrange
        (tmp_path / "azure-pipelines.yml").touch()
        (tmp_path / ".azuredevops").mkdir()

        # Act
        result = detect_platforms(tmp_path)

        # Assert
        azdo_count = sum(1 for p in result if p == PlatformKind.AZURE_DEVOPS)
        assert azdo_count == 1

    def test_github_only(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        result = detect_platforms(tmp_path)
        assert result == [PlatformKind.GITHUB]

    def test_sonar_only(self, tmp_path: Path) -> None:
        (tmp_path / "sonar-project.properties").touch()
        result = detect_platforms(tmp_path)
        assert result == [PlatformKind.SONAR]

    def test_nonexistent_root_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent root path raises no error, returns empty."""
        missing = tmp_path / "does-not-exist"
        result = detect_platforms(missing)
        assert result == []


# ---------------------------------------------------------------
# GitHubSetup
# ---------------------------------------------------------------


class TestGitHubSetup:
    """Tests for GitHubSetup class."""

    def test_is_cli_installed_true(self) -> None:
        from ai_engineering.platforms.github import GitHubSetup

        with patch("shutil.which", return_value="/usr/bin/gh"):
            assert GitHubSetup.is_cli_installed() is True

    def test_is_cli_installed_false(self) -> None:
        from ai_engineering.platforms.github import GitHubSetup

        with patch("shutil.which", return_value=None):
            assert GitHubSetup.is_cli_installed() is False

    def test_check_auth_status_not_installed(self) -> None:
        from ai_engineering.platforms.github import GitHubSetup

        # Act
        with patch("shutil.which", return_value=None):
            status = GitHubSetup.check_auth_status()

        # Assert
        assert status.cli_installed is False
        assert status.authenticated is False
        assert "not installed" in status.error

    def test_check_auth_status_authenticated(self) -> None:
        # Arrange
        from ai_engineering.platforms.github import GitHubSetup

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Logged in to github.com account testuser (token)\n"
        mock_result.stderr = ""

        # Act
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", return_value=mock_result),
        ):
            status = GitHubSetup.check_auth_status()

        # Assert
        assert status.cli_installed is True
        assert status.authenticated is True
        assert status.username == "testuser"

    def test_check_auth_status_not_authenticated(self) -> None:
        # Arrange
        from ai_engineering.platforms.github import GitHubSetup

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "not logged in"

        # Act
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", return_value=mock_result),
        ):
            status = GitHubSetup.check_auth_status()

        # Assert
        assert status.authenticated is False

    def test_get_login_command_has_scopes(self) -> None:
        from ai_engineering.platforms.github import GitHubSetup

        cmd = GitHubSetup.get_login_command()
        assert "gh" in cmd
        assert "--scopes" in cmd

    def test_get_login_instructions_contains_command(self) -> None:
        from ai_engineering.platforms.github import GitHubSetup

        instructions = GitHubSetup.get_login_instructions()
        assert "gh auth login" in instructions


# ---------------------------------------------------------------
# SonarSetup
# ---------------------------------------------------------------


class TestSonarSetup:
    """Tests for SonarSetup class."""

    @pytest.fixture()
    def mock_creds(self) -> MagicMock:
        backend = MagicMock()
        backend.get_password.return_value = None
        from ai_engineering.credentials.service import CredentialService

        return CredentialService(backend=backend)

    def test_get_token_url_sonarcloud(self) -> None:
        from ai_engineering.platforms.sonar import SonarSetup

        url = SonarSetup.get_token_url("https://sonarcloud.io")
        assert url == "https://sonarcloud.io/account/security"

    def test_get_token_url_custom(self) -> None:
        from ai_engineering.platforms.sonar import SonarSetup

        url = SonarSetup.get_token_url("https://sonar.example.com")
        assert url == "https://sonar.example.com/account/security"

    def test_validate_token_success_urllib(self, mock_creds: MagicMock) -> None:
        # Arrange
        from ai_engineering.platforms.sonar import SonarSetup

        sonar = SonarSetup(mock_creds)

        # Act
        # Force stdlib fallback by making httpx import fail.
        with patch.dict("sys.modules", {"httpx": None}):
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"valid": true}'
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_resp

            with patch("http.client.HTTPSConnection", return_value=mock_conn):
                result = sonar.validate_token("https://sonarcloud.io", "test-token")

        # Assert
        assert result.valid is True

    def test_validate_token_invalid_urllib(self, mock_creds: MagicMock) -> None:
        # Arrange
        from ai_engineering.platforms.sonar import SonarSetup

        sonar = SonarSetup(mock_creds)

        # Act
        with patch.dict("sys.modules", {"httpx": None}):
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"valid": false}'
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_resp

            with patch("http.client.HTTPSConnection", return_value=mock_conn):
                result = sonar.validate_token("https://sonarcloud.io", "bad-token")

        # Assert
        assert result.valid is False

    def test_store_and_retrieve_token(self, mock_creds: MagicMock) -> None:
        from ai_engineering.platforms.sonar import SonarSetup

        sonar = SonarSetup(mock_creds)
        sonar.store_token("test-token")
        # Verify store was called on the underlying service.
        assert mock_creds._backend.set_password.called

    def test_is_configured_false(self, mock_creds: MagicMock) -> None:
        from ai_engineering.platforms.sonar import SonarSetup

        sonar = SonarSetup(mock_creds)
        assert sonar.is_configured() is False

    def test_get_setup_instructions(self) -> None:
        from ai_engineering.platforms.sonar import SonarSetup

        instructions = SonarSetup.get_setup_instructions()
        assert "sonarcloud.io" in instructions
        assert "keyring" in instructions.lower() or "secret store" in instructions.lower()


# ---------------------------------------------------------------
# AzureDevOpsSetup
# ---------------------------------------------------------------


class TestAzureDevOpsSetup:
    """Tests for AzureDevOpsSetup class."""

    @pytest.fixture()
    def mock_creds(self) -> MagicMock:
        backend = MagicMock()
        backend.get_password.return_value = None
        from ai_engineering.credentials.service import CredentialService

        return CredentialService(backend=backend)

    def test_get_token_url(self) -> None:
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        url = AzureDevOpsSetup.get_token_url("https://dev.azure.com/myorg")
        assert url == "https://dev.azure.com/myorg/_usersSettings/tokens"

    def test_validate_pat_success_urllib(self, mock_creds: MagicMock) -> None:
        # Arrange
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        azdo = AzureDevOpsSetup(mock_creds)

        # Act
        with patch.dict("sys.modules", {"httpx": None}):
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_resp

            with patch("http.client.HTTPSConnection", return_value=mock_conn):
                result = azdo.validate_pat("https://dev.azure.com/myorg", "test-pat")

        # Assert
        assert result.valid is True

    def test_validate_pat_connection_error(self, mock_creds: MagicMock) -> None:
        # Arrange
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        azdo = AzureDevOpsSetup(mock_creds)

        # Act
        with (
            patch.dict("sys.modules", {"httpx": None}),
            patch("http.client.HTTPSConnection", side_effect=OSError("timeout")),
        ):
            result = azdo.validate_pat("https://dev.azure.com/myorg", "test-pat")

        # Assert
        assert result.valid is False
        assert "Connection error" in result.error

    def test_store_and_exists(self, mock_creds: MagicMock) -> None:
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        azdo = AzureDevOpsSetup(mock_creds)
        azdo.store_pat("test-pat")
        assert mock_creds._backend.set_password.called

    def test_is_configured_false(self, mock_creds: MagicMock) -> None:
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        azdo = AzureDevOpsSetup(mock_creds)
        assert azdo.is_configured() is False

    def test_get_setup_instructions(self) -> None:
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        instructions = AzureDevOpsSetup.get_setup_instructions("https://dev.azure.com/myorg")
        assert "_usersSettings/tokens" in instructions
