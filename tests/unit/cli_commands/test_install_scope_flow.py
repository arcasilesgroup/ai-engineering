"""Scope (local/global) flows from CLI flag or interactive wizard into install.

The ``--global`` / ``--local`` flags resolve to an explicit scope that skips
the prompt; with neither flag a first *interactive* install asks the wizard
(``ask_scope=True``). Non-interactive paths default to ``local``. The resolved
scope must reach ``install_with_pipeline``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_engineering.cli_commands.core import (
    _explicit_install_scope,
    _resolve_first_install_configuration,
)
from ai_engineering.cli_factory import create_app
from ai_engineering.installer.autodetect import DetectionResult

runner = CliRunner()

_CORE = "ai_engineering.cli_commands.core"


# ---------------------------------------------------------------------------
# _explicit_install_scope -- flag -> scope | None
# ---------------------------------------------------------------------------


def test_explicit_scope_global_wins() -> None:
    assert _explicit_install_scope(scope_global=True, scope_local=False) == "global"


def test_explicit_scope_local() -> None:
    assert _explicit_install_scope(scope_global=False, scope_local=True) == "local"


def test_explicit_scope_none_when_no_flag() -> None:
    """No flag -> None signals 'ask interactively / default local'."""
    assert _explicit_install_scope(scope_global=False, scope_local=False) is None


def test_explicit_scope_global_beats_local_when_both() -> None:
    assert _explicit_install_scope(scope_global=True, scope_local=True) == "global"


# ---------------------------------------------------------------------------
# _resolve_first_install_configuration -- interactive prompt vs default
# ---------------------------------------------------------------------------


def _detected() -> DetectionResult:
    return DetectionResult(stacks=["python"], surfaces=[], vcs="github")


def test_first_install_non_interactive_defaults_local() -> None:
    """No flag + non-interactive (no tty) -> local, no wizard."""
    with (
        patch(f"{_CORE}.is_json_mode", return_value=False),
        patch("sys.stdin") as mock_stdin,
        patch("ai_engineering.installer.wizard.run_wizard") as mock_wizard,
    ):
        mock_stdin.isatty.return_value = False
        _stacks, _surfaces, _vcs, scope = _resolve_first_install_configuration(
            _detected(), {}, None
        )
    mock_wizard.assert_not_called()
    assert scope == "local"


def test_first_install_non_interactive_honors_explicit_global() -> None:
    with (
        patch(f"{_CORE}.is_json_mode", return_value=False),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = False
        _stacks, _surfaces, _vcs, scope = _resolve_first_install_configuration(
            _detected(), {}, "global"
        )
    assert scope == "global"


def test_first_install_interactive_prompts_scope() -> None:
    """Greenfield interactive, no flag -> wizard called with ask_scope=True."""
    wiz = MagicMock(stacks=["python"], surfaces=["claude-code"], vcs="github", scope="global")
    with (
        patch(f"{_CORE}.is_json_mode", return_value=False),
        patch("sys.stdin") as mock_stdin,
        patch("ai_engineering.installer.wizard.run_wizard", return_value=wiz) as mock_wizard,
        patch(f"{_CORE}._show_detection_summary"),
    ):
        mock_stdin.isatty.return_value = True
        _stacks, _surfaces, _vcs, scope = _resolve_first_install_configuration(
            _detected(), {}, None
        )
    mock_wizard.assert_called_once()
    assert mock_wizard.call_args.kwargs.get("ask_scope") is True
    assert scope == "global"


def test_first_install_interactive_flag_suppresses_scope_prompt() -> None:
    """An explicit scope flag is forwarded to the wizard so it skips the prompt."""
    wiz = MagicMock(stacks=["python"], surfaces=["claude-code"], vcs="github", scope="global")
    with (
        patch(f"{_CORE}.is_json_mode", return_value=False),
        patch("sys.stdin") as mock_stdin,
        patch("ai_engineering.installer.wizard.run_wizard", return_value=wiz) as mock_wizard,
        patch(f"{_CORE}._show_detection_summary"),
    ):
        mock_stdin.isatty.return_value = True
        _resolve_first_install_configuration(_detected(), {}, "global")
    resolved_arg = mock_wizard.call_args.args[1]
    assert resolved_arg == {"scope": "global"}


# ---------------------------------------------------------------------------
# End-to-end: resolved scope reaches install_with_pipeline
# ---------------------------------------------------------------------------


def _mock_pipeline() -> MagicMock:
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
    return MagicMock(return_value=(mock_result, PipelineSummary(dry_run=False)))


def _greenfield(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "smoke"\nversion = "0.0.1"\n', encoding="utf-8"
    )
    return tmp_path


def test_global_flag_reaches_pipeline(tmp_path: Path) -> None:
    app = create_app()
    mock_pipe = _mock_pipeline()
    with patch(f"{_CORE}.install_with_pipeline", mock_pipe):
        result = runner.invoke(
            app, ["install", str(_greenfield(tmp_path)), "--global", "--non-interactive"]
        )
    assert result.exit_code == 0, result.output
    assert mock_pipe.call_args.kwargs.get("scope") == "global"


def test_no_flag_non_interactive_pipeline_local(tmp_path: Path) -> None:
    app = create_app()
    mock_pipe = _mock_pipeline()
    with patch(f"{_CORE}.install_with_pipeline", mock_pipe):
        result = runner.invoke(app, ["install", str(_greenfield(tmp_path)), "--non-interactive"])
    assert result.exit_code == 0, result.output
    assert mock_pipe.call_args.kwargs.get("scope") == "local"
