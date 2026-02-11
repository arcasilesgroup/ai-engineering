"""Tests for version lifecycle CLI integration.

Covers:
- _version_lifecycle_callback: blocks deprecated (non-exempt), allows exempt
  commands, warns outdated, silent when current, graceful on registry error.
- version_cmd: shows lifecycle status.
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import _EXEMPT_COMMANDS, create_app
from ai_engineering.version.checker import VersionCheckResult
from ai_engineering.version.models import VersionStatus

runner = CliRunner()

# All patches target the canonical module where check_version is defined,
# because cli_factory.py and core.py import it locally inside functions.
_PATCH_TARGET = "ai_engineering.version.checker.check_version"


def _make_check_result(
    *,
    installed: str = "0.1.0",
    status: VersionStatus | None = VersionStatus.CURRENT,
    is_current: bool = False,
    is_outdated: bool = False,
    is_deprecated: bool = False,
    is_eol: bool = False,
    latest: str | None = "0.1.0",
    message: str = "0.1.0 (current)",
) -> VersionCheckResult:
    """Build a VersionCheckResult for testing."""
    return VersionCheckResult(
        installed=installed,
        status=status,
        is_current=is_current,
        is_outdated=is_outdated,
        is_deprecated=is_deprecated,
        is_eol=is_eol,
        latest=latest,
        message=message,
    )


# ---------------------------------------------------------------------------
# CLI callback — deprecation blocking
# ---------------------------------------------------------------------------


class TestDeprecationBlocking:
    """Tests for CLI callback blocking deprecated versions."""

    def test_blocks_deprecated_on_install(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            is_deprecated=True,
            status=VersionStatus.DEPRECATED,
            message="0.1.0 (deprecated — CVE-2025-9999)",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["install"])
        assert result.exit_code == 1

    def test_blocks_eol_on_install(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            is_eol=True,
            status=VersionStatus.EOL,
            message="0.1.0 (end-of-life)",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["install"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# CLI callback — exempt commands
# ---------------------------------------------------------------------------


class TestExemptCommands:
    """Tests that exempt commands work even with deprecated version."""

    def test_version_allowed_when_deprecated(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            is_deprecated=True,
            status=VersionStatus.DEPRECATED,
            message="0.1.0 (deprecated)",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "deprecated" in result.output.lower()

    def test_exempt_commands_set(self) -> None:
        assert "version" in _EXEMPT_COMMANDS
        assert "update" in _EXEMPT_COMMANDS
        assert "doctor" in _EXEMPT_COMMANDS
        assert "install" not in _EXEMPT_COMMANDS


# ---------------------------------------------------------------------------
# CLI callback — outdated warning
# ---------------------------------------------------------------------------


class TestOutdatedWarning:
    """Tests that outdated versions produce a warning but don't block."""

    def test_warns_outdated_on_version_cmd(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            is_outdated=True,
            status=VersionStatus.SUPPORTED,
            message="0.1.0 (outdated — latest is 0.2.0)",
            latest="0.2.0",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI callback — current version (silent)
# ---------------------------------------------------------------------------


class TestCurrentVersionSilent:
    """Tests that current versions produce no warnings."""

    def test_no_warning_when_current(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            is_current=True,
            status=VersionStatus.CURRENT,
            message="0.1.0 (current)",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "BLOCKED" not in result.output


# ---------------------------------------------------------------------------
# CLI callback — registry error (fail-open)
# ---------------------------------------------------------------------------


class TestRegistryErrorFailOpen:
    """Tests that registry errors don't block commands."""

    def test_graceful_on_registry_error(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            status=None,
            message="Version registry unavailable — skipping lifecycle check",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["version"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# version_cmd output
# ---------------------------------------------------------------------------


class TestVersionCmd:
    """Tests for the version command output."""

    def test_shows_lifecycle_status(self) -> None:
        app = create_app()
        result_mock = _make_check_result(
            is_current=True,
            status=VersionStatus.CURRENT,
            message="0.1.0 (current)",
        )
        with patch(_PATCH_TARGET, return_value=result_mock):
            result = runner.invoke(app, ["version"])
        assert "0.1.0 (current)" in result.output
