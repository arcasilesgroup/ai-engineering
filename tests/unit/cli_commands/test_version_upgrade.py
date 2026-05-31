"""Tests for the ``version`` Typer sub-group and ``version upgrade`` command.

Covers (spec version-update-notice, sub-002):
- ``ai-eng version`` (no subcommand) still shows installed + latest.
- ``ai-eng version upgrade --dry-run`` prints the exact detected command and
  runs nothing.
- ``ai-eng version upgrade`` runs the detected argv via subprocess.
- A non-zero subprocess return is fail-loud: prints the manual command and
  exits non-zero.
- JSON mode emits a structured envelope.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from ai_engineering import __version__
from ai_engineering.cli_factory import create_app
from ai_engineering.version.checker import VersionCheckResult
from ai_engineering.version.models import VersionStatus

runner = CliRunner()

_CHECK_TARGET = "ai_engineering.version.checker.check_version"
_DETECT_TARGET = "ai_engineering.version.install_method.detect"
_RUN_TARGET = "ai_engineering.cli_commands.core.subprocess.run"


def _check_result(message: str = "0.1.0 (current)") -> VersionCheckResult:
    return VersionCheckResult(
        installed="0.1.0",
        status=VersionStatus.CURRENT,
        is_current=True,
        is_outdated=False,
        is_deprecated=False,
        is_eol=False,
        latest="0.1.0",
        message=message,
    )


# ---------------------------------------------------------------------------
# version (no subcommand) — show path
# ---------------------------------------------------------------------------


class TestVersionShow:
    """``ai-eng version`` shows installed version and lifecycle message."""

    def test_shows_installed_and_message(self) -> None:
        app = create_app()
        with patch(_CHECK_TARGET, return_value=_check_result("0.1.0 (current)")):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0 (current)" in result.output

    def test_shows_cached_latest_when_available(self) -> None:
        app = create_app()
        with (
            patch(_CHECK_TARGET, return_value=_check_result()),
            patch(
                "ai_engineering.version.cache.read",
                return_value={"latest": "0.9.0"},
            ),
        ):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.9.0" in result.output

    def test_degrades_gracefully_when_cache_empty(self) -> None:
        app = create_app()
        with (
            patch(_CHECK_TARGET, return_value=_check_result("0.1.0 (current)")),
            patch("ai_engineering.version.cache.read", return_value={}),
        ):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0 (current)" in result.output

    def test_json_mode_emits_envelope(self) -> None:
        app = create_app()
        with (
            patch(_CHECK_TARGET, return_value=_check_result()),
            patch(
                "ai_engineering.version.cache.read",
                return_value={"latest": "0.9.0"},
            ),
        ):
            result = runner.invoke(app, ["--json", "version"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["result"]["version"] == __version__
        assert payload["result"]["latest"] == "0.9.0"


# ---------------------------------------------------------------------------
# version upgrade — dry-run
# ---------------------------------------------------------------------------


class TestVersionUpgradeDryRun:
    """``--dry-run`` prints the exact command and executes nothing."""

    def test_prints_exact_command(self) -> None:
        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            result = runner.invoke(app, ["version", "upgrade", "--dry-run"])
        assert result.exit_code == 0
        assert "pipx upgrade ai-engineering" in result.output
        run_mock.assert_not_called()

    def test_json_dry_run_envelope(self) -> None:
        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            result = runner.invoke(app, ["--json", "version", "upgrade", "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["result"]["command"] == "pipx upgrade ai-engineering"
        assert payload["result"]["dry_run"] is True
        run_mock.assert_not_called()


# ---------------------------------------------------------------------------
# version upgrade — execute
# ---------------------------------------------------------------------------


class TestVersionUpgradeExecute:
    """The execute path runs the detected argv via subprocess."""

    def test_runs_detected_argv(self) -> None:
        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            run_mock.return_value.returncode = 0
            result = runner.invoke(app, ["version", "upgrade"])
        assert result.exit_code == 0
        called_argv = run_mock.call_args.args[0]
        assert called_argv == argv

    def test_success_prints_confirmation(self) -> None:
        app = create_app()
        argv = ["pip", "install", "-U", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pip", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            run_mock.return_value.returncode = 0
            result = runner.invoke(app, ["version", "upgrade"])
        assert result.exit_code == 0

    def test_json_success_emits_clean_envelope_and_suppresses_subprocess_output(self) -> None:
        """spec-156 D-156-14: in --json mode the upgrade subprocess stdout/stderr
        redirect to DEVNULL so the tool's chatter never corrupts the JSON
        envelope, and rc 0 emits a clean success envelope."""
        import subprocess as _subprocess

        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            run_mock.return_value.returncode = 0
            result = runner.invoke(app, ["--json", "version", "upgrade"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["result"]["upgraded"] is True
        assert payload["result"]["method"] == "pipx"
        kwargs = run_mock.call_args.kwargs
        assert kwargs.get("stdout") == _subprocess.DEVNULL
        assert kwargs.get("stderr") == _subprocess.DEVNULL


# ---------------------------------------------------------------------------
# version upgrade — unknown method (pip unavailable on a standalone tool)
# ---------------------------------------------------------------------------


class TestVersionUpgradeUnknownMethod:
    """When detect() cannot resolve a runnable upgrade, never execute a doomed
    command. Print manual guidance (pipx / uv tool / pip) and exit non-zero."""

    def test_unknown_prints_manual_guidance_and_exits_nonzero(self) -> None:
        app = create_app()
        with (
            patch(_DETECT_TARGET, return_value=("unknown", [])),
            patch(_RUN_TARGET) as run_mock,
        ):
            result = runner.invoke(app, ["version", "upgrade"])
        assert result.exit_code != 0
        # Never executes a subprocess in the unknown path.
        run_mock.assert_not_called()
        # Surfaces the likely manual commands.
        assert "pipx upgrade ai-engineering" in result.output
        assert "uv tool upgrade ai-engineering" in result.output
        assert "pip install -U ai-engineering" in result.output

    def test_unknown_json_envelope_is_error(self) -> None:
        app = create_app()
        with (
            patch(_DETECT_TARGET, return_value=("unknown", [])),
            patch(_RUN_TARGET) as run_mock,
        ):
            result = runner.invoke(app, ["--json", "version", "upgrade"])
        assert result.exit_code != 0
        run_mock.assert_not_called()
        payload = json.loads(result.output)
        assert payload["ok"] is False
        blob = json.dumps(payload)
        assert "pipx upgrade ai-engineering" in blob
        assert "uv tool upgrade ai-engineering" in blob


# ---------------------------------------------------------------------------
# version upgrade — fail-loud
# ---------------------------------------------------------------------------


class TestVersionUpgradeFailLoud:
    """A non-zero subprocess return must fail loudly, never silently."""

    def test_nonzero_exits_nonzero(self) -> None:
        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            run_mock.return_value.returncode = 1
            result = runner.invoke(app, ["version", "upgrade"])
        assert result.exit_code != 0

    def test_nonzero_prints_manual_command(self) -> None:
        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            run_mock.return_value.returncode = 1
            result = runner.invoke(app, ["version", "upgrade"])
        assert "pipx upgrade ai-engineering" in result.output

    def test_json_failure_envelope(self) -> None:
        app = create_app()
        argv = ["pipx", "upgrade", "ai-engineering"]
        with (
            patch(_DETECT_TARGET, return_value=("pipx", argv)),
            patch(_RUN_TARGET) as run_mock,
        ):
            run_mock.return_value.returncode = 1
            result = runner.invoke(app, ["--json", "version", "upgrade"])
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert "pipx upgrade ai-engineering" in json.dumps(payload)
