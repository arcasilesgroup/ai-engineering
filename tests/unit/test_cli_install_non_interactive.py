"""Unit tests for --non-interactive flag on the install command.

RED phase: these tests define the expected behavior of --non-interactive
and MUST FAIL until the implementation is complete.

Tests verify:
1. The --non-interactive flag exists on install_cmd.
2. When passed, install completes without interactive prompts (defaults used).
3. _offer_platform_onboarding skips prompts in non-interactive mode.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()

_CORE = "ai_engineering.cli_commands.core"


# ---------------------------------------------------------------------------
# Test 1: --non-interactive flag exists on install_cmd
# ---------------------------------------------------------------------------


class TestNonInteractiveFlagExists:
    """The install command must accept a --non-interactive flag."""

    def test_help_shows_non_interactive_option(self) -> None:
        """ai-eng install --help must list --non-interactive in its output."""
        import re

        # Arrange
        app = create_app()

        # Act
        result = runner.invoke(app, ["install", "--help"])

        # Assert -- strip ANSI escape codes before checking
        clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert result.exit_code == 0
        assert "--non-interactive" in clean


# ---------------------------------------------------------------------------
# Test 2: --non-interactive skips all prompts
# ---------------------------------------------------------------------------


def _mock_install_with_pipeline() -> MagicMock:
    """Build a mock for install_with_pipeline that returns (InstallResult, PipelineSummary)."""
    from ai_engineering.installer.phases.pipeline import PipelineSummary

    mock_result = MagicMock(
        governance_files=MagicMock(created=[Path("a")]),
        project_files=MagicMock(created=[Path("b")]),
        state_files=[Path("c")],
        hooks=MagicMock(installed=[]),
        readiness_status="pending",
        already_installed=False,
        manual_steps=[],
        guide_text="",
        total_created=3,
    )
    mock_summary = PipelineSummary(dry_run=False)
    mock_fn = MagicMock(return_value=(mock_result, mock_summary))
    return mock_fn


class TestNonInteractiveSkipsPrompts:
    """When --non-interactive is passed, install must not call any prompt."""

    def test_install_completes_without_prompts(self, tmp_path: Path) -> None:
        """Install with --non-interactive must succeed using defaults only.

        Mocks the install service to isolate the CLI layer. Verifies that
        typer.prompt and typer.confirm are never called, proving all
        interactive paths were bypassed.
        """
        # Arrange
        app = create_app()
        mock_install = _mock_install_with_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.typer.prompt") as mock_prompt,
            patch(f"{_CORE}.typer.confirm") as mock_confirm,
            patch(f"{_CORE}.detect_platforms", return_value=[]),
        ):
            # Act
            result = runner.invoke(
                app,
                ["install", str(tmp_path), "--non-interactive", "--stack", "python"],
            )

            # Assert -- command must succeed
            assert result.exit_code == 0, (
                f"Expected exit 0, got {result.exit_code}: {result.output}"
            )

            # Assert -- no interactive prompts were called
            mock_prompt.assert_not_called()
            mock_confirm.assert_not_called()

    def test_non_interactive_uses_default_vcs_provider(self, tmp_path: Path) -> None:
        """In non-interactive mode without --vcs, the default 'github' must be used."""
        # Arrange
        app = create_app()
        mock_install = _mock_install_with_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch("ai_engineering.git.operations.run_git", return_value=(False, "")),
            patch(f"{_CORE}.detect_platforms", return_value=[]),
        ):
            # Act
            result = runner.invoke(
                app,
                ["install", str(tmp_path), "--non-interactive"],
            )

            # Assert
            assert result.exit_code == 0, f"Unexpected exit: {result.output}"
            # The install service should receive vcs_provider="github" (the default)
            call_kwargs = mock_install.call_args
            assert call_kwargs is not None
            assert call_kwargs.kwargs.get("vcs_provider") == "github" or (
                len(call_kwargs.args) > 0 and "github" in str(call_kwargs)
            )

    def test_non_interactive_uses_default_ai_providers(self, tmp_path: Path) -> None:
        """In non-interactive mode without --provider, default ['claude_code'] must be used."""
        # Arrange
        app = create_app()
        mock_install = _mock_install_with_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch("ai_engineering.git.operations.run_git", return_value=(False, "")),
            patch(f"{_CORE}.detect_platforms", return_value=[]),
        ):
            # Act
            result = runner.invoke(
                app,
                ["install", str(tmp_path), "--non-interactive"],
            )

            # Assert
            assert result.exit_code == 0, f"Unexpected exit: {result.output}"
            call_kwargs = mock_install.call_args
            assert call_kwargs is not None
            assert call_kwargs.kwargs.get("ai_providers") == ["claude_code"] or (
                len(call_kwargs.args) > 0 and "claude_code" in str(call_kwargs)
            )


# ---------------------------------------------------------------------------
# Test 3: _offer_platform_onboarding respects non-interactive
# ---------------------------------------------------------------------------


class TestOfferPlatformOnboardingNonInteractive:
    """_offer_platform_onboarding must skip prompts in non-interactive mode."""

    def test_skips_confirm_prompts(self, tmp_path: Path) -> None:
        """When non-interactive, _offer_platform_onboarding must not call
        typer.confirm and must not invoke setup_platforms_cmd.
        """
        from ai_engineering.cli_commands.core import _offer_platform_onboarding

        with (
            patch(f"{_CORE}.detect_platforms", return_value=[]),
            patch(f"{_CORE}.typer.confirm") as mock_confirm,
            patch(f"{_CORE}.typer.echo"),
        ):
            # Act -- call with non_interactive=True
            # This will fail until the function signature accepts the flag
            _offer_platform_onboarding(tmp_path, vcs_provider="github", non_interactive=True)

            # Assert -- no confirmation prompts
            mock_confirm.assert_not_called()

    def test_does_not_invoke_setup_platforms(self, tmp_path: Path) -> None:
        """When non-interactive, setup_platforms_cmd must never be called."""
        from ai_engineering.cli_commands.core import _offer_platform_onboarding

        with (
            patch(f"{_CORE}.detect_platforms", return_value=[]),
            patch(f"{_CORE}.typer.confirm", return_value=True) as mock_confirm,
            patch(f"{_CORE}.typer.echo"),
            patch("ai_engineering.cli_commands.setup.setup_platforms_cmd") as mock_setup,
        ):
            # Act
            _offer_platform_onboarding(tmp_path, vcs_provider="github", non_interactive=True)

            # Assert
            mock_confirm.assert_not_called()
            mock_setup.assert_not_called()
