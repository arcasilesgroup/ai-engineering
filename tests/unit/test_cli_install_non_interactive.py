"""Unit tests for --non-interactive flag on the install command.

Tests verify:
1. The --non-interactive flag exists on install_cmd.
2. When passed, install completes without interactive prompts (defaults used).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

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
        (tmp_path / ".git").mkdir(exist_ok=True)

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.check_uv_prereq", return_value=None),
            patch(f"{_CORE}.typer.prompt") as mock_prompt,
            patch(f"{_CORE}.typer.confirm") as mock_confirm,
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
        (tmp_path / ".git").mkdir(exist_ok=True)

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.check_uv_prereq", return_value=None),
            patch("ai_engineering.git.operations.run_git", return_value=(False, "")),
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
        """In non-interactive mode without --provider, default ['claude-code'] must be used."""
        # Arrange
        app = create_app()
        mock_install = _mock_install_with_pipeline()
        (tmp_path / ".git").mkdir(exist_ok=True)

        with (
            patch(f"{_CORE}.install_with_pipeline", mock_install),
            patch(f"{_CORE}.check_uv_prereq", return_value=None),
            patch("ai_engineering.git.operations.run_git", return_value=(False, "")),
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
            assert call_kwargs.kwargs.get("surfaces") == ["claude-code"] or (
                len(call_kwargs.args) > 0 and "claude-code" in str(call_kwargs)
            )


# ---------------------------------------------------------------------------
# Test 3: failed tools are named on stderr in non-interactive mode (ARC-319)
# ---------------------------------------------------------------------------


class _FakePhaseResult:
    """Minimal stand-in for a PhaseResult carrying tool markers."""

    def __init__(self, phase_name: str, *, failed: list[str], skipped: list[str]) -> None:
        self.phase_name = phase_name
        self.failed = failed
        self.skipped = skipped


class _FakeSummary:
    def __init__(self, results: list[_FakePhaseResult]) -> None:
        self.results = results


class TestFailedToolsAreNamed:
    """ARC-319: exit-80 install logs must NAME the unresolved tool.

    Regression guard for the windows-only latent tool-gap where the
    aggregate EXIT 80 fired but stdout never named which required tool
    failed (only skipped markers were emitted).
    """

    def test_failed_tool_markers_emitted_to_stderr(self) -> None:
        from ai_engineering.cli_commands import core
        from ai_engineering.installer.phases import PHASE_TOOLS

        summary = _FakeSummary(
            [
                _FakePhaseResult(
                    PHASE_TOOLS,
                    failed=["tool:gitleaks:install-failed", "not-a-tool-line"],
                    skipped=["tool:jq:preexisting-user-scope"],
                )
            ]
        )

        with patch(f"{_CORE}.print_stderr") as mock_stderr:
            core._emit_noninteractive_failed_tools(summary, non_interactive=True)

        emitted = [c.args[0] for c in mock_stderr.call_args_list]
        assert "tool:gitleaks:install-failed" in emitted
        # Only ``tool:``-prefixed markers are surfaced.
        assert "not-a-tool-line" not in emitted

    def test_no_emission_when_interactive(self) -> None:
        from ai_engineering.cli_commands import core
        from ai_engineering.installer.phases import PHASE_TOOLS

        summary = _FakeSummary(
            [_FakePhaseResult(PHASE_TOOLS, failed=["tool:gitleaks:install-failed"], skipped=[])]
        )

        with patch(f"{_CORE}.print_stderr") as mock_stderr:
            core._emit_noninteractive_failed_tools(summary, non_interactive=False)

        mock_stderr.assert_not_called()

    def test_no_emission_when_no_failures(self) -> None:
        from ai_engineering.cli_commands import core
        from ai_engineering.installer.phases import PHASE_TOOLS

        summary = _FakeSummary([_FakePhaseResult(PHASE_TOOLS, failed=[], skipped=[])])

        with patch(f"{_CORE}.print_stderr") as mock_stderr:
            core._emit_noninteractive_failed_tools(summary, non_interactive=True)

        mock_stderr.assert_not_called()
