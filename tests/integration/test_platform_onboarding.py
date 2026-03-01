"""Integration tests for full platform onboarding flow.

Tests the end-to-end onboarding flow with mocked APIs and real
filesystem. Validates that:
- Platform detection works with real repo layouts.
- Credential service correctly persists state to tools.json.
- Doctor check_platforms function reports correct status.
- Setup CLI commands complete full flow with mocked APIs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.credentials.models import (
    AzureDevOpsConfig,
    CredentialRef,
    GitHubConfig,
    PlatformKind,
    SonarConfig,
    ToolsState,
)
from ai_engineering.credentials.service import CredentialService
from ai_engineering.doctor.service import CheckStatus, DoctorReport, check_platforms
from ai_engineering.platforms.detector import detect_platforms

# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a full project layout with platform markers."""
    # .ai-engineering/state directory.
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)

    # GitHub marker.
    (tmp_path / ".github").mkdir()

    # Sonar marker with properties.
    props = tmp_path / "sonar-project.properties"
    props.write_text(
        "sonar.projectKey=my-org_my-project\nsonar.host.url=https://sonarcloud.io\n",
        encoding="utf-8",
    )

    # Azure DevOps marker.
    (tmp_path / "azure-pipelines.yml").touch()

    return tmp_path


@pytest.fixture()
def mock_backend() -> MagicMock:
    """Return a mock keyring backend."""
    backend = MagicMock()
    backend.get_password.return_value = None
    return backend


# ---------------------------------------------------------------
# Platform detection + state round-trip
# ---------------------------------------------------------------


class TestPlatformDetectionIntegration:
    """Tests for platform detection in realistic repo layouts."""

    def test_all_platforms_detected(self, project_root: Path) -> None:
        detected = detect_platforms(project_root)
        assert PlatformKind.GITHUB in detected
        assert PlatformKind.SONAR in detected
        assert PlatformKind.AZURE_DEVOPS in detected
        assert len(detected) == 3

    def test_state_persists_after_setup(self, project_root: Path, mock_backend: MagicMock) -> None:
        """tools.json round-trips correctly after platform setup."""
        svc = CredentialService(backend=mock_backend)
        state_dir = project_root / ".ai-engineering" / "state"

        # Simulate setup by saving state.
        state = ToolsState(
            github=GitHubConfig(
                configured=True,
                cli_authenticated=True,
                scopes=["repo", "workflow", "read:org"],
            ),
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
                project_key="my-org_my-project",
                credential_ref=CredentialRef(
                    service_name="ai-engineering/sonar",
                    username="token",
                    configured=True,
                ),
            ),
            azure_devops=AzureDevOpsConfig(
                configured=True,
                org_url="https://dev.azure.com/my-org",
                credential_ref=CredentialRef(
                    service_name="ai-engineering/azure_devops",
                    username="pat",
                    configured=True,
                ),
            ),
        )
        svc.save_tools_state(state_dir, state)

        # Verify file exists and round-trips.
        tools_path = state_dir / "tools.json"
        assert tools_path.exists()

        loaded = svc.load_tools_state(state_dir)
        assert loaded.github.configured is True
        assert loaded.github.scopes == ["repo", "workflow", "read:org"]
        assert loaded.sonar.url == "https://sonarcloud.io"
        assert loaded.azure_devops.org_url == "https://dev.azure.com/my-org"


# ---------------------------------------------------------------
# Doctor check_platforms integration
# ---------------------------------------------------------------


class TestDoctorCheckPlatforms:
    """Tests for doctor check_platforms function."""

    def test_unconfigured_platforms_warn(self, project_root: Path) -> None:
        """All platforms unconfigured → all WARN."""
        state_dir = project_root / ".ai-engineering" / "state"
        CredentialService.save_tools_state(state_dir, ToolsState())

        report = DoctorReport()
        check_platforms(project_root, report)

        # Should have 3 warn checks (one per platform).
        platform_checks = [c for c in report.checks if c.name.startswith("platform:")]
        assert len(platform_checks) == 3
        assert all(c.status == CheckStatus.WARN for c in platform_checks)

    def test_github_configured_and_authed(self, project_root: Path) -> None:
        """GitHub configured with mocked gh CLI auth → OK."""
        state_dir = project_root / ".ai-engineering" / "state"
        state = ToolsState(github=GitHubConfig(configured=True, cli_authenticated=True))
        CredentialService.save_tools_state(state_dir, state)

        mock_status = MagicMock()
        mock_status.authenticated = True
        mock_status.username = "testuser"

        report = DoctorReport()
        with patch(
            "ai_engineering.platforms.github.GitHubSetup.check_auth_status",
            return_value=mock_status,
        ):
            check_platforms(project_root, report)

        gh_check = next(c for c in report.checks if c.name == "platform:github")
        assert gh_check.status == CheckStatus.OK
        assert "testuser" in gh_check.message

    def test_sonar_configured_token_valid(
        self, project_root: Path, mock_backend: MagicMock
    ) -> None:
        """Sonar configured with valid token → OK."""
        state_dir = project_root / ".ai-engineering" / "state"
        state = ToolsState(
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
                credential_ref=CredentialRef(
                    service_name="ai-engineering/sonar",
                    username="token",
                    configured=True,
                ),
            )
        )
        CredentialService.save_tools_state(state_dir, state)

        # Mock keyring to return a token.
        mock_backend.get_password.return_value = "squ_test_token"

        report = DoctorReport()
        mock_validation = MagicMock()
        mock_validation.valid = True

        with (
            patch(
                "ai_engineering.credentials.service.CredentialService._get_keyring",
                return_value=mock_backend,
            ),
            patch(
                "ai_engineering.platforms.sonar.SonarSetup.validate_token",
                return_value=mock_validation,
            ),
        ):
            check_platforms(project_root, report)

        sonar_check = next(c for c in report.checks if c.name == "platform:sonar")
        assert sonar_check.status == CheckStatus.OK

    def test_sonar_configured_token_missing(
        self, project_root: Path, mock_backend: MagicMock
    ) -> None:
        """Sonar configured but token missing from keyring → FAIL."""
        state_dir = project_root / ".ai-engineering" / "state"
        state = ToolsState(
            sonar=SonarConfig(
                configured=True,
                url="https://sonarcloud.io",
            )
        )
        CredentialService.save_tools_state(state_dir, state)

        report = DoctorReport()
        with patch(
            "ai_engineering.credentials.service.CredentialService._get_keyring",
            return_value=mock_backend,
        ):
            check_platforms(project_root, report)

        sonar_check = next(c for c in report.checks if c.name == "platform:sonar")
        assert sonar_check.status == CheckStatus.FAIL
        assert "missing" in sonar_check.message.lower()


# ---------------------------------------------------------------
# Sonar properties file integration
# ---------------------------------------------------------------


class TestSonarPropertiesIntegration:
    """Tests for reading sonar-project.properties in setup flow."""

    def test_project_key_read_from_properties(self, project_root: Path) -> None:
        from ai_engineering.cli_commands.setup import _read_sonar_project_key

        key = _read_sonar_project_key(project_root)
        assert key == "my-org_my-project"

    def test_host_url_read_from_properties(self, project_root: Path) -> None:
        from ai_engineering.cli_commands.setup import _read_sonar_url_from_properties

        url = _read_sonar_url_from_properties(project_root)
        assert url == "https://sonarcloud.io"
