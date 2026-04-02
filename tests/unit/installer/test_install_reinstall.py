"""RED-phase tests for spec-095: redesigned reinstall flow.

Tests verify the new behavior:
- Default reinstall: NO menu, auto-infer mode, preview tree, Y/n confirm
- --fresh: all files as "overwrite", typed "fresh" confirmation
- --reconfigure: launches wizard, diff tree
- First install: unchanged (autodetect + wizard + install)

All tests MUST FAIL against the current implementation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()

_CORE = "ai_engineering.cli_commands.core"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_install_pipeline() -> MagicMock:
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
    return MagicMock(return_value=(mock_result, mock_summary))


def _setup_existing_install(tmp_path: Path) -> Path:
    """Create a minimal .ai-engineering dir that signals an existing installation."""
    (tmp_path / ".git").mkdir(exist_ok=True)
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "install-state.json"
    state_file.write_text('{"schema_version": "1"}', encoding="utf-8")

    manifest = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_content = (
        "providers:\n"
        "  stacks: [python]\n"
        "  ides: [terminal]\n"
        "  vcs: github\n"
        "  ai_providers: [claude_code]\n"
    )
    manifest.write_text(manifest_content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: Default reinstall does NOT show menu
# ---------------------------------------------------------------------------


class TestReinstallNoMenuShown:
    """When .ai-engineering/ exists and install-state.json exists,
    render_reinstall_options must NOT be called. The new flow auto-infers
    mode and proceeds directly to a preview tree + Y/n confirmation."""

    def test_reinstall_no_menu_shown(self, tmp_path: Path) -> None:
        """On default reinstall, render_reinstall_options is never invoked."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.render_reinstall_options", create=True) as mock_menu,
        ):
            # Act
            _result = runner.invoke(app, ["install", str(project)])

            # Assert -- the old menu must NOT be shown
            mock_menu.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Default reinstall shows a preview tree
# ---------------------------------------------------------------------------


class TestReinstallAutoInferShowsPreviewTree:
    """When reinstalling (existing install detected), the command must
    show a preview tree of what will change and ask 'Proceed? [Y/n]'."""

    def test_reinstall_auto_infer_shows_preview_tree(self, tmp_path: Path) -> None:
        """Default reinstall renders a preview tree and asks for Y/n confirmation."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        with patch(f"{_CORE}.install_with_pipeline", mock_install):
            # Act -- answer Y to the confirmation
            result = runner.invoke(app, ["install", str(project)], input="Y\n")

            # Assert -- output must contain a preview tree and confirmation prompt
            output = result.output + (result.stderr if hasattr(result, "stderr") else "")
            assert "Proceed?" in output or "proceed" in output.lower(), (
                f"Expected a 'Proceed? [Y/n]' confirmation prompt, got:\n{output}"
            )


# ---------------------------------------------------------------------------
# Test 3: Default reinstall does NOT call wizard
# ---------------------------------------------------------------------------


class TestReinstallWizardNotCalled:
    """On default reinstall (no flags), run_wizard must NOT be invoked.
    Configuration comes from the existing manifest.yml. Additionally,
    the old render_reinstall_options menu must NOT appear."""

    def test_reinstall_wizard_not_called(self, tmp_path: Path) -> None:
        """Default reinstall reads config from manifest, skips wizard AND menu."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.render_reinstall_options", create=True) as mock_menu,
            patch("ai_engineering.installer.wizard.run_wizard") as mock_wizard,
        ):
            # Act
            _result = runner.invoke(app, ["install", str(project)])

            # Assert -- BOTH wizard AND menu must be skipped on default reinstall
            mock_wizard.assert_not_called()
            mock_menu.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: --fresh requires typed "fresh" confirmation
# ---------------------------------------------------------------------------


class TestFreshFlagTypedConfirmation:
    """With --fresh, all files show as 'overwrite' in the tree and the
    command requires typing 'fresh' to confirm (not just Y/n)."""

    def test_fresh_flag_typed_confirmation(self, tmp_path: Path) -> None:
        """--fresh must require typing 'fresh' to proceed, not Y/n."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        with patch(f"{_CORE}.install_with_pipeline", mock_install):
            # Act -- type "fresh" to confirm
            result = runner.invoke(app, ["install", str(project), "--fresh"], input="fresh\n")

            # Assert -- the command must accept --fresh flag
            assert result.exit_code == 0, (
                f"Expected exit 0 with --fresh flag, got {result.exit_code}: {result.output}"
            )

    def test_fresh_flag_shows_overwrite_markers(self, tmp_path: Path) -> None:
        """--fresh must mark all files as 'overwrite' in the preview tree."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        with patch(f"{_CORE}.install_with_pipeline", mock_install):
            # Act
            result = runner.invoke(app, ["install", str(project), "--fresh"], input="fresh\n")

            # Assert -- output must contain overwrite markers
            output = result.output + (result.stderr if hasattr(result, "stderr") else "")
            assert "overwrite" in output.lower(), (
                f"Expected 'overwrite' markers in tree output, got:\n{output}"
            )

    def test_fresh_flag_rejects_y_confirmation(self, tmp_path: Path) -> None:
        """--fresh must NOT accept 'Y' as confirmation -- only 'fresh'."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        with patch(f"{_CORE}.install_with_pipeline", mock_install):
            # Act -- try 'Y' instead of 'fresh'
            result = runner.invoke(app, ["install", str(project), "--fresh"], input="Y\n")

            # Assert -- command must accept --fresh as a valid flag (exit != 2)
            assert result.exit_code != 2, (
                f"--fresh flag must be recognized by the CLI, got exit 2: {result.output}"
            )
            # Assert -- install must NOT proceed when 'Y' is typed instead of 'fresh'
            mock_install.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: --reconfigure launches wizard
# ---------------------------------------------------------------------------


class TestReconfigureFlagLaunchesWizard:
    """With --reconfigure, run_wizard IS called, then a diff tree shows
    added/removed files."""

    def test_reconfigure_flag_launches_wizard(self, tmp_path: Path) -> None:
        """--reconfigure must invoke run_wizard for provider selection."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        mock_wizard_result = MagicMock(
            stacks=["python"],
            providers=["claude_code"],
            ides=["terminal"],
            vcs="github",
        )

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(
                "ai_engineering.installer.wizard.run_wizard",
                return_value=mock_wizard_result,
            ) as mock_wizard,
        ):
            # Act
            result = runner.invoke(app, ["install", str(project), "--reconfigure"], input="Y\n")

            # Assert -- wizard must be called
            assert result.exit_code == 0, (
                f"Expected exit 0 with --reconfigure, got {result.exit_code}: {result.output}"
            )
            mock_wizard.assert_called_once()

    def test_reconfigure_flag_shows_diff_tree(self, tmp_path: Path) -> None:
        """--reconfigure must show a diff tree with added/removed files."""
        # Arrange
        app = create_app()
        project = _setup_existing_install(tmp_path)
        mock_install = _mock_install_pipeline()

        mock_wizard_result = MagicMock(
            stacks=["python", "typescript"],
            providers=["claude_code", "github_copilot"],
            ides=["terminal", "vscode"],
            vcs="github",
        )

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(
                "ai_engineering.installer.wizard.run_wizard",
                return_value=mock_wizard_result,
            ),
        ):
            # Act
            result = runner.invoke(app, ["install", str(project), "--reconfigure"], input="Y\n")

            # Assert -- command must accept --reconfigure as a valid flag
            assert result.exit_code != 2, (
                f"--reconfigure flag must be recognized by the CLI, got exit 2: {result.output}"
            )
            # Assert -- output must contain semantic diff indicators
            output = result.output + (result.stderr if hasattr(result, "stderr") else "")
            has_diff = any(
                marker in output.lower() for marker in ["added", "removed", "[add]", "[remove]"]
            )
            assert has_diff, f"Expected diff tree with added/removed markers, got:\n{output}"


# ---------------------------------------------------------------------------
# Test 6: First install unchanged
# ---------------------------------------------------------------------------


class TestFirstInstallUnchanged:
    """When .ai-engineering/ does NOT exist (first install), the flow
    is unchanged: autodetect + wizard + install."""

    def test_first_install_unchanged(self, tmp_path: Path) -> None:
        """First install (no existing .ai-engineering/) in non-TTY uses autodetect defaults."""
        # Arrange
        app = create_app()
        mock_install = _mock_install_pipeline()
        (tmp_path / ".git").mkdir(exist_ok=True)

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.render_reinstall_options", create=True) as mock_menu,
        ):
            # Act -- no .ai-engineering exists in tmp_path, CliRunner is non-TTY
            _result = runner.invoke(app, ["install", str(tmp_path)])

            # Assert -- in non-TTY, wizard is NOT called (autodetect defaults used)
            # Assert -- reinstall menu must NOT appear
            mock_menu.assert_not_called()
            # Assert -- install_with_pipeline was called (install proceeded with defaults)
            mock_install.assert_called_once()
