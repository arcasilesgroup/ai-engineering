"""Unit tests for project validation in install_cmd.

Tests verify that install_cmd validates the target directory contains at least
one "project signal" (.git, pyproject.toml, package.json, *.sln, go.mod,
Cargo.toml, tsconfig.json) before proceeding with installation.

- Interactive mode: warn and prompt for confirmation.
- Non-interactive mode: abort with error.
- When project signals are present: proceed without warning.

RED phase: these tests must FAIL against the current implementation because
install_cmd does not yet include this validation guard.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()

_CORE = "ai_engineering.cli_commands.core"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_install_with_pipeline() -> MagicMock:
    """Build a mock for install_with_pipeline returning (InstallResult, PipelineSummary)."""
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


# ---------------------------------------------------------------------------
# Test 1: Interactive mode warns on empty directory
# ---------------------------------------------------------------------------


class TestInstallCmdWarnsOnEmptyDirectory:
    """When target has no project signals and TTY is available, install should
    prompt the user for confirmation before proceeding."""

    def test_install_cmd_warns_on_empty_directory(self, tmp_path: Path) -> None:
        """An empty directory (no .git, no pyproject.toml, etc.) should trigger
        a confirmation prompt in interactive mode.

        We simulate the user declining the prompt, so install_with_pipeline
        must NOT be called.
        """
        # Arrange -- tmp_path is an empty directory with no project signals
        app = create_app()
        mock_install = _mock_install_with_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.sys.stdin") as mock_stdin,
            patch(f"{_CORE}.typer.confirm", return_value=False) as mock_confirm,
        ):
            mock_stdin.isatty.return_value = True

            # Act
            result = runner.invoke(
                app,
                ["install", str(tmp_path), "--stack", "python"],
            )

            # Assert -- a confirmation prompt must have been shown
            mock_confirm.assert_called_once()
            # Assert -- user declined, so install should NOT proceed
            mock_install.assert_not_called()
            # Assert -- the command should exit (non-zero or 0 for user cancellation)
            assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# Test 2: Non-interactive mode aborts on empty directory
# ---------------------------------------------------------------------------


class TestInstallCmdAbortsNonInteractiveOnEmptyDirectory:
    """When --non-interactive flag is set and target has no project signals,
    install should abort with a non-zero exit code."""

    def test_install_cmd_aborts_non_interactive_on_empty_directory(self, tmp_path: Path) -> None:
        """In non-interactive mode, an empty directory (no project signals)
        must cause the command to abort without running the install pipeline.
        """
        # Arrange -- tmp_path is an empty directory with no project signals
        app = create_app()
        mock_install = _mock_install_with_pipeline()

        with patch(f"{_CORE}.install_with_pipeline", mock_install):
            # Act
            result = runner.invoke(
                app,
                [
                    "install",
                    str(tmp_path),
                    "--non-interactive",
                    "--stack",
                    "python",
                ],
            )

            # Assert -- command must fail with non-zero exit code
            assert result.exit_code != 0, (
                f"Expected non-zero exit for empty directory in non-interactive mode, "
                f"got exit {result.exit_code}: {result.output}"
            )
            # Assert -- install pipeline must NOT have been called
            mock_install.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: Proceeds normally with project signals
# ---------------------------------------------------------------------------


class TestInstallCmdProceedsWithProjectSignals:
    """When target has at least one project signal, install proceeds without
    any warning or confirmation prompt."""

    @pytest.mark.parametrize(
        "signal",
        [
            ".git",
            "pyproject.toml",
            "package.json",
            "go.mod",
            "Cargo.toml",
            "tsconfig.json",
        ],
    )
    def test_install_cmd_proceeds_with_project_signals(self, tmp_path: Path, signal: str) -> None:
        """When a recognized project signal exists in the target directory,
        install_with_pipeline should be called and no confirmation prompt shown.
        """
        # Arrange -- create the project signal
        signal_path = tmp_path / signal
        if signal == ".git":
            signal_path.mkdir()
        else:
            signal_path.write_text("")

        app = create_app()
        mock_install = _mock_install_with_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.typer.confirm") as mock_confirm,
            patch(f"{_CORE}.typer.prompt") as mock_prompt,
        ):
            # Act
            result = runner.invoke(
                app,
                [
                    "install",
                    str(tmp_path),
                    "--non-interactive",
                    "--stack",
                    "python",
                ],
            )

            # Assert -- install pipeline must have been called
            mock_install.assert_called_once()
            # Assert -- no confirmation prompts should have appeared
            mock_confirm.assert_not_called()
            mock_prompt.assert_not_called()
            # Assert -- command must succeed
            assert result.exit_code == 0, (
                f"Expected exit 0 with project signal '{signal}', "
                f"got exit {result.exit_code}: {result.output}"
            )
