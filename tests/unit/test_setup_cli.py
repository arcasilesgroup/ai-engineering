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
    _read_sonar_property,
    _state_dir,
    setup_app,
)
from ai_engineering.cli_output import set_json_mode
from ai_engineering.credentials.models import PlatformKind

runner = CliRunner()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project root with `.ai-engineering/state/`."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    return tmp_path


@pytest.fixture(autouse=True)
def reset_json_mode() -> None:
    """Isolate setup CLI tests from leaked global JSON mode state."""
    set_json_mode(False)
    try:
        yield
    finally:
        set_json_mode(False)


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
        assert _read_sonar_property(tmp_path, "sonar.host.url") == "https://sonarcloud.io"

    def test_read_url_missing_file(self, tmp_path: Path) -> None:
        assert _read_sonar_property(tmp_path, "sonar.host.url") is None

    def test_read_url_no_host_key(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-proj\n", encoding="utf-8")
        assert _read_sonar_property(tmp_path, "sonar.host.url") is None

    def test_read_project_key(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.projectKey=my-proj\n", encoding="utf-8")
        assert _read_sonar_property(tmp_path, "sonar.projectKey") == "my-proj"

    def test_read_project_key_missing_file(self, tmp_path: Path) -> None:
        assert _read_sonar_property(tmp_path, "sonar.projectKey") is None

    def test_read_organization(self, tmp_path: Path) -> None:
        props = tmp_path / "sonar-project.properties"
        props.write_text("sonar.organization=my-org\n", encoding="utf-8")
        assert _read_sonar_property(tmp_path, "sonar.organization") == "my-org"

    def test_read_organization_missing_file(self, tmp_path: Path) -> None:
        assert _read_sonar_property(tmp_path, "sonar.organization") is None


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


# ---------------------------------------------------------------
# JSON mode paths
# ---------------------------------------------------------------


class TestJsonModePaths:
    """Tests for JSON mode output branches."""

    @patch("ai_engineering.cli_commands.setup.is_json_mode", return_value=True)
    @patch("ai_engineering.cli_commands.setup.detect_platforms", return_value=[])
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_platforms_json_mode(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        mock_json: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        result = runner.invoke(setup_app, ["platforms"])
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.setup.is_json_mode", return_value=True)
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_json_mode(
        self,
        mock_resolve: MagicMock,
        mock_json: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        mock_gh = MagicMock()
        mock_gh.is_cli_installed.return_value = False
        with patch(
            "ai_engineering.platforms.github.GitHubSetup",
            mock_gh,
        ):
            result = runner.invoke(setup_app, ["github"])
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.setup.is_json_mode", return_value=True)
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_sonar_json_mode_returns_error(
        self,
        mock_resolve: MagicMock,
        mock_json: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        result = runner.invoke(setup_app, ["sonar"])
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.setup.is_json_mode", return_value=True)
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_azure_devops_json_mode_returns_error(
        self,
        mock_resolve: MagicMock,
        mock_json: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        result = runner.invoke(setup_app, ["azure-devops"])
        assert result.exit_code == 0

    @patch("ai_engineering.cli_commands.setup.is_json_mode", return_value=True)
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_sonarlint_json_mode_returns_error(
        self,
        mock_resolve: MagicMock,
        mock_json: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        result = runner.invoke(setup_app, ["sonarlint"])
        assert result.exit_code == 0


# ---------------------------------------------------------------
# Internal setup flows
# ---------------------------------------------------------------


class TestRunGitHubSetup:
    """Tests for the _run_github_setup internal function."""

    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_cli_not_installed(
        self,
        mock_resolve: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        mock_gh = MagicMock()
        mock_gh.is_cli_installed.return_value = False
        with patch(
            "ai_engineering.platforms.github.GitHubSetup",
            mock_gh,
        ):
            from ai_engineering.cli_commands.setup import _run_github_setup

            _run_github_setup(project_root)

    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_not_authenticated(
        self,
        mock_resolve: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        mock_gh = MagicMock()
        mock_gh.is_cli_installed.return_value = True
        status = MagicMock()
        status.authenticated = False
        mock_gh.check_scopes.return_value = status
        mock_gh.get_login_instructions.return_value = "Run: gh auth login"
        with patch(
            "ai_engineering.platforms.github.GitHubSetup",
            mock_gh,
        ):
            from ai_engineering.cli_commands.setup import _run_github_setup

            _run_github_setup(project_root)

    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_authenticated_missing_scopes(
        self,
        mock_resolve: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        mock_gh = MagicMock()
        mock_gh.is_cli_installed.return_value = True
        status = MagicMock()
        status.authenticated = True
        status.username = "testuser"
        status.missing_scopes = ["repo"]
        status.scopes = ["read:org"]
        mock_gh.check_scopes.return_value = status
        mock_gh.get_login_command.return_value = ["gh", "auth", "login"]
        with patch(
            "ai_engineering.platforms.github.GitHubSetup",
            mock_gh,
        ):
            from ai_engineering.cli_commands.setup import _run_github_setup

            _run_github_setup(project_root)

    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_authenticated_all_scopes(
        self,
        mock_resolve: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        mock_gh = MagicMock()
        mock_gh.is_cli_installed.return_value = True
        status = MagicMock()
        status.authenticated = True
        status.username = "testuser"
        status.missing_scopes = []
        status.scopes = ["repo", "read:org"]
        mock_gh.check_scopes.return_value = status
        with patch(
            "ai_engineering.platforms.github.GitHubSetup",
            mock_gh,
        ):
            from ai_engineering.cli_commands.setup import _run_github_setup

            _run_github_setup(project_root)


class TestRunSonarSetup:
    """Tests for the _run_sonar_setup internal function."""

    def test_sonar_setup_valid_token(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        mock_cred.load_tools_state.return_value = MagicMock()
        mock_cred.service_name.return_value = "ai-engineering/sonar"
        mock_sonar = MagicMock()
        result_obj = MagicMock()
        result_obj.valid = True
        mock_sonar.validate_token.return_value = result_obj
        mock_sonar_cls = MagicMock(return_value=mock_sonar)
        mock_sonar_cls.get_token_url.return_value = "https://sonar/tokens"

        with (
            patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred),
            patch("ai_engineering.platforms.sonar.SonarSetup", mock_sonar_cls),
            patch("ai_engineering.cli_commands.setup.typer.prompt", return_value="squ_token"),
        ):
            from ai_engineering.cli_commands.setup import _run_sonar_setup

            _run_sonar_setup(
                project_root,
                url_override="https://sonarcloud.io",
                project_key_override="my-proj",
                organization_override="my-org",
            )

    def test_sonar_setup_invalid_token(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        mock_sonar = MagicMock()
        result_obj = MagicMock()
        result_obj.valid = False
        result_obj.error = "Unauthorized"
        mock_sonar.validate_token.return_value = result_obj
        mock_sonar_cls = MagicMock(return_value=mock_sonar)
        mock_sonar_cls.get_token_url.return_value = "https://sonar/tokens"

        with (
            patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred),
            patch("ai_engineering.platforms.sonar.SonarSetup", mock_sonar_cls),
            patch("ai_engineering.cli_commands.setup.typer.prompt", return_value="bad_token"),
        ):
            from ai_engineering.cli_commands.setup import _run_sonar_setup

            _run_sonar_setup(project_root, url_override="https://sonar.io")


class TestRunAzureDevOpsSetup:
    """Tests for the _run_azure_devops_setup internal function."""

    def test_azdo_setup_valid_pat(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        mock_cred.load_tools_state.return_value = MagicMock()
        mock_cred.service_name.return_value = "ai-engineering/azure_devops"
        mock_azdo = MagicMock()
        result_obj = MagicMock()
        result_obj.valid = True
        mock_azdo.validate_pat.return_value = result_obj
        mock_azdo_cls = MagicMock(return_value=mock_azdo)
        mock_azdo_cls.get_token_url.return_value = "https://dev.azure.com/_usersSettings/tokens"

        with (
            patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred),
            patch("ai_engineering.platforms.azure_devops.AzureDevOpsSetup", mock_azdo_cls),
            patch("ai_engineering.cli_commands.setup.typer.prompt", return_value="pat_token"),
        ):
            from ai_engineering.cli_commands.setup import _run_azure_devops_setup

            _run_azure_devops_setup(project_root, org_url_override="https://dev.azure.com/my-org")

    def test_azdo_setup_invalid_pat(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        mock_azdo = MagicMock()
        result_obj = MagicMock()
        result_obj.valid = False
        result_obj.error = "Unauthorized"
        mock_azdo.validate_pat.return_value = result_obj
        mock_azdo_cls = MagicMock(return_value=mock_azdo)
        mock_azdo_cls.get_token_url.return_value = "https://dev.azure.com/_usersSettings/tokens"

        with (
            patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred),
            patch("ai_engineering.platforms.azure_devops.AzureDevOpsSetup", mock_azdo_cls),
            patch("ai_engineering.cli_commands.setup.typer.prompt", return_value="bad_pat"),
        ):
            from ai_engineering.cli_commands.setup import _run_azure_devops_setup

            _run_azure_devops_setup(project_root, org_url_override="https://dev.azure.com/org")


class TestRunSonarLintSetup:
    """Tests for the _run_sonarlint_setup internal function."""

    def test_sonarlint_no_sonar_url(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        state = MagicMock()
        state.sonar.url = ""
        mock_cred.load_tools_state.return_value = state
        with patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred):
            from ai_engineering.cli_commands.setup import _run_sonarlint_setup

            _run_sonarlint_setup(project_root)

    def test_sonarlint_no_project_key(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        state = MagicMock()
        state.sonar.url = "https://sonarcloud.io"
        state.sonar.project_key = ""
        mock_cred.load_tools_state.return_value = state
        with patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred):
            from ai_engineering.cli_commands.setup import _run_sonarlint_setup

            _run_sonarlint_setup(project_root)

    def test_sonarlint_with_detected_ides(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        state = MagicMock()
        state.sonar.url = "https://sonarcloud.io"
        state.sonar.project_key = "my-proj"
        mock_cred.load_tools_state.return_value = state

        from ai_engineering.platforms.sonarlint import IDEFamily

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.ide_family = "vscode"
        mock_result.files_written = [".vscode/settings.json"]
        mock_summary = MagicMock()
        mock_summary.results = [mock_result]
        mock_summary.any_success = True

        with (
            patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred),
            patch(
                "ai_engineering.platforms.sonarlint.detect_ide_families",
                return_value=[IDEFamily.VSCODE],
            ),
            patch(
                "ai_engineering.platforms.sonarlint.configure_all_ides",
                return_value=mock_summary,
            ),
        ):
            from ai_engineering.cli_commands.setup import _run_sonarlint_setup

            _run_sonarlint_setup(project_root)

    def test_sonarlint_no_ides_detected(self, project_root: Path) -> None:
        mock_cred = MagicMock()
        state = MagicMock()
        state.sonar.url = "https://sonarcloud.io"
        state.sonar.project_key = "my-proj"
        mock_cred.load_tools_state.return_value = state

        with (
            patch("ai_engineering.cli_commands.setup.CredentialService", return_value=mock_cred),
            patch(
                "ai_engineering.platforms.sonarlint.detect_ide_families",
                return_value=[],
            ),
            patch("ai_engineering.cli_commands.setup.typer.confirm", return_value=False),
        ):
            from ai_engineering.cli_commands.setup import _run_sonarlint_setup

            _run_sonarlint_setup(project_root)


# ---------------------------------------------------------------
# Sonar/AzDO detected in platforms command
# ---------------------------------------------------------------


class TestSetupPlatformsAllDetected:
    """Tests for platforms command with all platforms detected."""

    @patch("ai_engineering.cli_commands.setup._run_azure_devops_setup")
    @patch("ai_engineering.cli_commands.setup._run_sonar_setup")
    @patch("ai_engineering.cli_commands.setup._run_github_setup")
    @patch(
        "ai_engineering.cli_commands.setup.detect_platforms",
        return_value=[PlatformKind.GITHUB, PlatformKind.SONAR, PlatformKind.AZURE_DEVOPS],
    )
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_all_platforms_detected(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        mock_github: MagicMock,
        mock_sonar: MagicMock,
        mock_azdo: MagicMock,
        project_root: Path,
    ) -> None:
        mock_resolve.return_value = project_root
        runner.invoke(setup_app, ["platforms"])
        mock_github.assert_called_once()
        mock_sonar.assert_called_once()
        mock_azdo.assert_called_once()


class TestVcsFactoryAzdoAlias:
    """Tests that the factory _PROVIDERS map includes the 'azdo' alias."""

    def test_azdo_key_maps_to_azure_devops_provider(self) -> None:
        from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
        from ai_engineering.vcs.factory import _PROVIDERS

        assert "azdo" in _PROVIDERS
        assert _PROVIDERS["azdo"] is AzureDevOpsProvider

    def test_azdo_in_valid_providers_list(self) -> None:
        from ai_engineering.cli_commands.vcs import _VALID_PROVIDERS

        assert "azdo" in _VALID_PROVIDERS


# ---------------------------------------------------------------
# Fix 2: Clean output — no guide_text block in install output
# ---------------------------------------------------------------


class TestInstallCleanOutput:
    """Tests that install output omits the branch policy guide text block."""

    @patch("ai_engineering.cli_commands.core.check_uv_prereq", return_value=None)
    @patch("ai_engineering.cli_commands.core.is_json_mode", return_value=False)
    @patch("ai_engineering.cli_commands.core.install_with_pipeline")
    @patch("ai_engineering.cli_commands.core.resolve_project_root")
    def test_guide_text_not_printed_as_block(
        self,
        mock_resolve: MagicMock,
        mock_install: MagicMock,
        mock_json: MagicMock,
        mock_uv: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When guide_text is present, only warnings are shown — not the full text block."""
        mock_resolve.return_value = tmp_path
        (tmp_path / ".git").mkdir(exist_ok=True)
        result_obj = MagicMock()
        result_obj.governance_files.created = ["a"]
        result_obj.project_files.created = ["b"]
        result_obj.state_files = ["c"]
        result_obj.readiness_status = "ready"
        result_obj.already_installed = False
        result_obj.manual_steps = []
        result_obj.total_created = 3
        result_obj.guide_text = "Step 1: Go to settings\nStep 2: Enable protection"
        summary_obj = MagicMock()
        summary_obj.results = []
        summary_obj.verdicts = []
        summary_obj.completed_phases = []
        summary_obj.failed_phase = None
        mock_install.return_value = (result_obj, summary_obj)

        import typer
        from typer.testing import CliRunner as _Runner

        from ai_engineering.cli_commands.core import install_cmd

        app = typer.Typer()
        app.command()(install_cmd)
        _runner = _Runner()
        # Provide all flags to skip wizard
        res = _runner.invoke(
            app,
            [
                str(tmp_path),
                "--vcs",
                "github",
                "--stack",
                "python",
                "--provider",
                "claude_code",
                "--ide",
                "terminal",
            ],
        )

        # The guide text body should NOT appear in output
        assert "Step 1: Go to settings" not in res.output
        assert "Step 2: Enable protection" not in res.output
        # But warnings about manual branch policy SHOULD appear
        out = res.output.lower()
        assert "branch" in out or "policy" in out or "manual" in out


# ---------------------------------------------------------------
# Fix 3a: Platform filtering by vcs_provider
# ---------------------------------------------------------------


class TestSetupPlatformsFiltering:
    """Tests that setup_platforms_cmd filters undetected platforms based on vcs_provider."""

    @patch("ai_engineering.cli_commands.setup.CredentialService")
    @patch("ai_engineering.cli_commands.setup.typer.confirm", return_value=False)
    @patch("ai_engineering.cli_commands.setup._run_sonar_setup")
    @patch(
        "ai_engineering.cli_commands.setup.detect_platforms",
        return_value=[PlatformKind.SONAR],
    )
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_github_vcs_hides_azure_devops(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        mock_sonar: MagicMock,
        mock_confirm: MagicMock,
        mock_cred: MagicMock,
        project_root: Path,
    ) -> None:
        """When vcs_provider='github', AZURE_DEVOPS is not offered as undetected."""
        mock_resolve.return_value = project_root
        mock_state = MagicMock()
        mock_state.sonar.configured = False
        mock_state.sonar.url = ""
        mock_cred.return_value.load_tools_state.return_value = mock_state

        from ai_engineering.cli_commands.setup import setup_platforms_cmd

        setup_platforms_cmd(project_root, vcs_provider="github")

        # Confirm calls should NOT include azure_devops
        for call in mock_confirm.call_args_list:
            prompt_text = call[0][0] if call[0] else call[1].get("text", "")
            assert "azure_devops" not in prompt_text.lower()

    @patch("ai_engineering.cli_commands.setup.CredentialService")
    @patch("ai_engineering.cli_commands.setup.typer.confirm", return_value=False)
    @patch("ai_engineering.cli_commands.setup._run_sonar_setup")
    @patch(
        "ai_engineering.cli_commands.setup.detect_platforms",
        return_value=[PlatformKind.SONAR],
    )
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_azure_devops_vcs_hides_github(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        mock_sonar: MagicMock,
        mock_confirm: MagicMock,
        mock_cred: MagicMock,
        project_root: Path,
    ) -> None:
        """When vcs_provider='azure_devops', GITHUB is not offered as undetected."""
        mock_resolve.return_value = project_root
        mock_state = MagicMock()
        mock_state.sonar.configured = False
        mock_state.sonar.url = ""
        mock_cred.return_value.load_tools_state.return_value = mock_state

        from ai_engineering.cli_commands.setup import setup_platforms_cmd

        setup_platforms_cmd(project_root, vcs_provider="azure_devops")

        # Confirm calls should NOT include github
        for call in mock_confirm.call_args_list:
            prompt_text = call[0][0] if call[0] else call[1].get("text", "")
            assert "github" not in prompt_text.lower()

    @patch("ai_engineering.cli_commands.setup.CredentialService")
    @patch("ai_engineering.cli_commands.setup.typer.confirm", return_value=False)
    @patch(
        "ai_engineering.cli_commands.setup.detect_platforms",
        return_value=[],
    )
    @patch("ai_engineering.cli_commands.setup.resolve_project_root")
    def test_no_vcs_provider_offers_all(
        self,
        mock_resolve: MagicMock,
        mock_detect: MagicMock,
        mock_confirm: MagicMock,
        mock_cred: MagicMock,
        project_root: Path,
    ) -> None:
        """When vcs_provider=None, all platforms are offered."""
        mock_resolve.return_value = project_root
        mock_state = MagicMock()
        mock_state.sonar.configured = False
        mock_state.sonar.url = ""
        mock_cred.return_value.load_tools_state.return_value = mock_state

        from ai_engineering.cli_commands.setup import setup_platforms_cmd

        setup_platforms_cmd(project_root, vcs_provider=None)

        # All three platform kinds should have been offered via confirm
        confirm_texts = " ".join(
            str(call[0][0]) if call[0] else "" for call in mock_confirm.call_args_list
        )
        assert "github" in confirm_texts.lower()
        assert "azure_devops" in confirm_texts.lower()
        assert "sonar" in confirm_texts.lower()


# ---------------------------------------------------------------
# Fix 3b: Sonar URL normalization
# ---------------------------------------------------------------


class TestSonarUrlNormalization:
    """Tests that SonarSetup.validate_token normalizes URLs with paths."""

    def _make_mock_httpx(self, mock_response: MagicMock) -> MagicMock:
        """Create a fake httpx module with a mock get() function."""
        import types

        mock_httpx = types.ModuleType("httpx")
        mock_httpx.get = MagicMock(return_value=mock_response)  # type: ignore[attr-defined]
        return mock_httpx

    def test_url_with_path_is_normalized(self) -> None:
        """URL like https://sonarcloud.io/organizations/foo/projects is normalized."""
        import sys

        from ai_engineering.platforms.sonar import SonarSetup

        mock_cred = MagicMock()
        sonar = SonarSetup(mock_cred)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True}

        mock_httpx = self._make_mock_httpx(mock_response)
        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = sonar.validate_token(
                "https://sonarcloud.io/organizations/my-org/projects", "squ_token"
            )

        assert result.valid is True
        # The API call should use the base URL, not the full path
        called_url = mock_httpx.get.call_args[0][0]
        assert called_url == "https://sonarcloud.io/api/authentication/validate"

    def test_base_url_unchanged(self) -> None:
        """A base URL like https://sonarcloud.io is used as-is."""
        import sys

        from ai_engineering.platforms.sonar import SonarSetup

        mock_cred = MagicMock()
        sonar = SonarSetup(mock_cred)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True}

        mock_httpx = self._make_mock_httpx(mock_response)
        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = sonar.validate_token("https://sonarcloud.io", "squ_token")

        assert result.valid is True
        called_url = mock_httpx.get.call_args[0][0]
        assert called_url == "https://sonarcloud.io/api/authentication/validate"

    def test_json_parse_error_gives_helpful_message(self) -> None:
        """When response is not valid JSON, a helpful message is returned."""
        import json as _json
        import sys

        from ai_engineering.platforms.sonar import SonarSetup

        mock_cred = MagicMock()
        sonar = SonarSetup(mock_cred)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = _json.JSONDecodeError("msg", "doc", 0)

        mock_httpx = self._make_mock_httpx(mock_response)
        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = sonar.validate_token("https://sonarcloud.io", "squ_token")

        assert result.valid is False
        assert "base URL" in result.error
