"""Tests for the Engram third-party install prompt + per-OS / per-IDE wiring.

Spec-123 D-123-12 / D-123-29 (Phase 5):

- ``ai-eng install`` adds an interactive prompt asking whether to install
  Engram for memory persistence.
- On *yes* the installer detects the host OS and active IDE, then invokes
  Engram's official install path (brew / winget / direct binary) and
  finally runs ``engram setup <ide>``.
- On *no* nothing is installed; the framework remains fully functional.
- ``--engram`` / ``--no-engram`` flags bypass the prompt deterministically.
- Non-interactive sessions (CI, ``stdin`` not a tty) default to *no* without
  prompting so unattended installs never block.

Engram is a *third-party* product. ai-engineering ships **no** Engram
wrapper code at runtime; the integration is install-time wiring only and
``subprocess.run`` is mocked everywhere in this module so the developer
machine is never touched by the test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from ai_engineering.installer import engram


@pytest.fixture
def mock_subprocess() -> mock.MagicMock:
    """Patch ``subprocess.run`` inside the engram module.

    All Engram CLI invocations (brew/winget/curl/engram setup) flow through
    this mock so the host machine is never modified by these tests.
    """

    with mock.patch("ai_engineering.installer.engram.subprocess.run") as mocked:
        # Default: success (returncode=0, no output).
        mocked.return_value = mock.MagicMock(returncode=0, stdout="", stderr="")
        yield mocked


# --------------------------------------------------------------------------- #
# Prompt-level behaviour                                                      #
# --------------------------------------------------------------------------- #


def test_prompt_skip_does_nothing(mock_subprocess: mock.MagicMock) -> None:
    """A 'n' answer must short-circuit before any subprocess call."""

    with mock.patch("builtins.input", return_value="n"):
        result = engram.maybe_install_engram(force=None, interactive=True)

    assert result.skipped is True, "skipped=True must propagate to caller"
    assert result.success is True, "skip is not a failure"
    mock_subprocess.assert_not_called()


def test_prompt_accept_invokes_install(mock_subprocess: mock.MagicMock) -> None:
    """A 'y' answer must call ``install_engram`` with the detected OS+IDE."""

    detected_os = "macos"
    detected_ide = "claude_code"

    with (
        mock.patch("builtins.input", return_value="y"),
        mock.patch.object(engram, "detect_os", return_value=detected_os),
        mock.patch.object(engram, "detect_ide", return_value=detected_ide),
        mock.patch.object(engram, "install_engram") as mocked_install,
    ):
        mocked_install.return_value = engram.InstallResult(
            success=True,
            message="installed",
            os_name=detected_os,
            ide_name=detected_ide,
        )

        result = engram.maybe_install_engram(force=None, interactive=True)

    mocked_install.assert_called_once_with(detected_os, detected_ide)
    assert result.skipped is False
    assert result.success is True


def test_no_engram_flag_skips_prompt(mock_subprocess: mock.MagicMock) -> None:
    """``--no-engram`` (force=False) must skip without prompting."""

    with mock.patch("builtins.input") as prompt:
        result = engram.maybe_install_engram(force=False, interactive=True)

    prompt.assert_not_called()
    assert result.skipped is True
    mock_subprocess.assert_not_called()


def test_engram_flag_forces_yes(mock_subprocess: mock.MagicMock) -> None:
    """``--engram`` (force=True) must install without prompting."""

    with (
        mock.patch("builtins.input") as prompt,
        mock.patch.object(engram, "detect_os", return_value="linux"),
        mock.patch.object(engram, "detect_ide", return_value="codex"),
        mock.patch.object(engram, "install_engram") as mocked_install,
    ):
        mocked_install.return_value = engram.InstallResult(
            success=True,
            message="installed",
            os_name="linux",
            ide_name="codex",
        )

        result = engram.maybe_install_engram(force=True, interactive=True)

    prompt.assert_not_called()
    mocked_install.assert_called_once_with("linux", "codex")
    assert result.skipped is False
    assert result.success is True


def test_non_interactive_defaults_no(mock_subprocess: mock.MagicMock) -> None:
    """``interactive=False`` (no tty) must default to skip without prompting."""

    with mock.patch("builtins.input") as prompt:
        result = engram.maybe_install_engram(force=None, interactive=False)

    prompt.assert_not_called()
    assert result.skipped is True
    mock_subprocess.assert_not_called()


# --------------------------------------------------------------------------- #
# OS detection                                                                #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "platform_value, expected",
    [
        ("darwin", "macos"),
        ("linux", "linux"),
        ("win32", "windows"),
        ("cygwin", "windows"),
        ("freebsd", "unknown"),
    ],
)
def test_detect_os_returns_canonical_name(platform_value: str, expected: str) -> None:
    """``detect_os`` must canonicalise ``sys.platform`` values."""

    with mock.patch.object(engram.sys, "platform", platform_value):
        assert engram.detect_os() == expected


# --------------------------------------------------------------------------- #
# IDE detection                                                               #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "marker, expected",
    [
        (".claude", "claude_code"),
        (".codex", "codex"),
        (".gemini", "gemini"),
    ],
)
def test_detect_ide_via_directory_marker(
    tmp_path: Path,
    marker: str,
    expected: str,
) -> None:
    """Directory-based markers must surface the matching IDE."""

    (tmp_path / marker).mkdir()
    assert engram.detect_ide(tmp_path) == expected


def test_detect_ide_via_copilot_instructions_file(tmp_path: Path) -> None:
    """A ``.github/copilot-instructions.md`` file must signal Copilot."""

    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "copilot-instructions.md").write_text("hello", encoding="utf-8")
    assert engram.detect_ide(tmp_path) == "copilot"


def test_detect_ide_returns_unknown_when_no_markers(tmp_path: Path) -> None:
    """Empty directories yield ``unknown``."""

    assert engram.detect_ide(tmp_path) == "unknown"


# --------------------------------------------------------------------------- #
# install_engram() — per-OS dispatch                                          #
# --------------------------------------------------------------------------- #


def test_install_engram_macos_uses_brew(mock_subprocess: mock.MagicMock) -> None:
    """macOS installs must shell out to ``brew install engram``."""

    result = engram.install_engram("macos", "claude_code")

    install_calls = [call_args for call_args in mock_subprocess.call_args_list if call_args.args]
    assert any(
        list(call.args[0])[:2] == ["brew", "install"] and "engram" in list(call.args[0])
        for call in install_calls
    ), "brew install engram must be invoked on macOS"
    assert result.success is True


def test_install_engram_windows_uses_winget(mock_subprocess: mock.MagicMock) -> None:
    """Windows installs must shell out to ``winget install``."""

    result = engram.install_engram("windows", "copilot")

    install_calls = [call for call in mock_subprocess.call_args_list if call.args]
    assert any(list(call.args[0])[:2] == ["winget", "install"] for call in install_calls), (
        "winget install must be invoked on Windows"
    )
    assert result.success is True


def test_install_engram_linux_downloads_binary(mock_subprocess: mock.MagicMock) -> None:
    """Linux installs must use ``curl`` (binary download fallback)."""

    result = engram.install_engram("linux", "gemini")

    invocations = [list(call.args[0]) for call in mock_subprocess.call_args_list if call.args]
    assert any(invocation and invocation[0] == "curl" for invocation in invocations), (
        "curl-based binary download must be invoked on Linux"
    )
    assert result.success is True


def test_install_engram_runs_setup_after_install(mock_subprocess: mock.MagicMock) -> None:
    """After a successful install the IDE-specific ``engram setup`` runs."""

    engram.install_engram("macos", "claude_code")

    invocations = [list(call.args[0]) for call in mock_subprocess.call_args_list if call.args]
    assert ["engram", "setup", "claude_code"] in invocations, (
        "engram setup <ide> must be the final invocation"
    )


def test_install_engram_failure_is_non_blocking(mock_subprocess: mock.MagicMock) -> None:
    """An install failure must surface a structured non-blocking result."""

    mock_subprocess.return_value = mock.MagicMock(
        returncode=1,
        stdout="",
        stderr="brew: formula not found",
    )

    result = engram.install_engram("macos", "claude_code")

    assert result.success is False
    assert result.os_name == "macos"
    assert result.ide_name == "claude_code"
    assert result.message  # Non-empty diagnostic message.


def test_install_engram_unknown_os_returns_failure(mock_subprocess: mock.MagicMock) -> None:
    """An unsupported OS must short-circuit without subprocess calls."""

    result = engram.install_engram("unknown", "claude_code")

    mock_subprocess.assert_not_called()
    assert result.success is False
    assert "unsupported" in result.message.lower()


def test_install_engram_unknown_ide_skips_setup(mock_subprocess: mock.MagicMock) -> None:
    """When IDE is unknown the install proceeds but ``engram setup`` is skipped."""

    result = engram.install_engram("macos", "unknown")

    invocations = [list(call.args[0]) for call in mock_subprocess.call_args_list if call.args]
    assert not any(invocation[:2] == ["engram", "setup"] for invocation in invocations), (
        "engram setup must not run when IDE is unknown"
    )
    # Install itself still attempted so the user gets the binary on PATH.
    assert any(invocation and invocation[0] == "brew" for invocation in invocations)
    assert result.success is True
