"""Unit tests for doctor/checks/feeds.py -- enterprise artifact feed diagnostics.

RED phase: these tests target check_feeds() which does not exist yet.
Expected to fail with ImportError until the implementation is written.

Tests cover:
- Feed detection from pyproject.toml [[tool.uv.index]]
- Lock file leak detection (pypi.org in uv.lock when private feed configured)
- Mixed source warnings (private + pypi)
- Keyring availability and backend checks
- CI environment keyring skip
- Lock file freshness checks
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_engineering.doctor.checks.feeds import check_feeds
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport

pytestmark = pytest.mark.unit


# -- TOML fragments ----------------------------------------------------------

_PYPROJECT_NO_FEED = """\
[project]
name = "my-app"
version = "1.0.0"
"""

_PYPROJECT_PRIVATE_FEED = """\
[project]
name = "my-app"
version = "1.0.0"

[[tool.uv.index]]
name = "corporate"
url = "https://pkgs.dev.azure.com/ORG/PROJ/_packaging/FEED/pypi/simple/"
default = true
"""

_PYPROJECT_MIXED_FEEDS = """\
[project]
name = "my-app"
version = "1.0.0"

[[tool.uv.index]]
name = "corporate"
url = "https://pkgs.dev.azure.com/ORG/PROJ/_packaging/FEED/pypi/simple/"

[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple"
"""

# -- Lock file fragments ------------------------------------------------------

_LOCK_CLEAN = """\
version = 1

[[package]]
name = "some-pkg"
source = { registry = "https://pkgs.dev.azure.com/ORG/PROJ/_packaging/FEED/pypi/simple/" }

[[package]]
name = "another-pkg"
source = { registry = "https://pkgs.dev.azure.com/ORG/PROJ/_packaging/FEED/pypi/simple/" }
"""

_LOCK_LEAKED = """\
version = 1

[[package]]
name = "internal-pkg"
source = { registry = "https://pkgs.dev.azure.com/ORG/PROJ/_packaging/FEED/pypi/simple/" }

[[package]]
name = "requests"
source = { registry = "https://pypi.org/simple" }
"""


# -- Helpers ------------------------------------------------------------------


def _write_project(
    tmp_path: Path,
    *,
    pyproject: str,
    lock: str | None = None,
    lock_mtime_offset: float = 0.0,
) -> Path:
    """Create a fake project directory with pyproject.toml and optional uv.lock.

    Parameters
    ----------
    lock_mtime_offset:
        Seconds to add to uv.lock mtime relative to pyproject.toml.
        Negative values make the lock older than pyproject.toml.
    """
    target = tmp_path / "project"
    target.mkdir()
    pyproject_path = target / "pyproject.toml"
    pyproject_path.write_text(pyproject)

    if lock is not None:
        lock_path = target / "uv.lock"
        lock_path.write_text(lock)
        # Set lock mtime relative to pyproject.toml
        pyproject_stat = pyproject_path.stat()
        os.utime(lock_path, (pyproject_stat.st_atime, pyproject_stat.st_mtime + lock_mtime_offset))

    return target


def _find_check(report: DoctorReport, name: str) -> CheckResult | None:
    """Return the first check matching *name*, or None."""
    return next((c for c in report.checks if c.name == name), None)


def _find_checks(report: DoctorReport, name: str) -> list[CheckResult]:
    """Return all checks matching *name*."""
    return [c for c in report.checks if c.name == name]


# -- Tests --------------------------------------------------------------------


class TestCheckFeedsDetection:
    """Feed detection and no-op behavior."""

    def test_no_feed_configured_emits_nothing(self, tmp_path: Path) -> None:
        """pyproject.toml without [[tool.uv.index]] produces no checks."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_NO_FEED)
        report = DoctorReport()

        # Act
        check_feeds(target, report)

        # Assert
        assert report.checks == []


class TestCheckFeedsLockLeak:
    """Lock file leak detection -- pypi.org references in uv.lock."""

    def test_private_feed_clean_lock_ok(self, tmp_path: Path) -> None:
        """Private feed with clean lock (no pypi.org) produces OK."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=_LOCK_CLEAN)
        report = DoctorReport()

        # Act
        check_feeds(target, report)

        # Assert
        check = _find_check(report, "feed-lock-leak")
        assert check is not None
        assert check.status == CheckStatus.OK

    def test_private_feed_pypi_in_lock_fails(self, tmp_path: Path) -> None:
        """Private feed without pypi index, but uv.lock contains pypi.org registry -> FAIL."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=_LOCK_LEAKED)
        report = DoctorReport()

        # Act
        check_feeds(target, report)

        # Assert
        check = _find_check(report, "feed-lock-leak")
        assert check is not None
        assert check.status == CheckStatus.FAIL
        assert "pypi.org" in check.message


class TestCheckFeedsMixedSources:
    """Mixed source detection -- private + pypi configured together."""

    def test_mixed_sources_warns(self, tmp_path: Path) -> None:
        """Private feed AND pypi.org both as [[tool.uv.index]] -> WARN."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_MIXED_FEEDS, lock=_LOCK_CLEAN)
        report = DoctorReport()

        # Act
        check_feeds(target, report)

        # Assert
        check = _find_check(report, "feed-mixed-sources")
        assert check is not None
        assert check.status == CheckStatus.WARN


class TestCheckFeedsKeyring:
    """Keyring availability and backend checks."""

    def test_keyring_not_found_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Private feed, keyring CLI not on PATH, not CI -> FAIL."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=_LOCK_CLEAN)
        report = DoctorReport()
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

        # Act
        check_feeds(target, report)

        # Assert
        check = _find_check(report, "feed-keyring")
        assert check is not None
        assert check.status == CheckStatus.FAIL

    def test_keyring_no_backend_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Private feed, keyring found but subprocess returns error (no backend) -> WARN."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=_LOCK_CLEAN)
        report = DoctorReport()
        monkeypatch.setattr(
            "shutil.which",
            lambda cmd: "/usr/bin/keyring" if cmd == "keyring" else None,
        )
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        mock_run = MagicMock(
            side_effect=subprocess.CalledProcessError(
                returncode=1, cmd=["keyring", "--list-backends"]
            ),
        )
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        check_feeds(target, report)

        # Assert
        check = _find_check(report, "feed-keyring")
        assert check is not None
        assert check.status == CheckStatus.WARN
        assert "backend" in check.message.lower()

    def test_keyring_no_credential_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Private feed, keyring works, but no credential for feed URL -> WARN."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=_LOCK_CLEAN)
        report = DoctorReport()
        monkeypatch.setattr(
            "shutil.which",
            lambda cmd: "/usr/bin/keyring" if cmd == "keyring" else None,
        )
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

        def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and "get" in cmd:
                # keyring get returns empty / no credential
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
            # Backend check succeeds
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="keyring.backends", stderr=""
            )

        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        check_feeds(target, report)

        # Assert
        check = _find_check(report, "feed-keyring")
        assert check is not None
        assert check.status == CheckStatus.WARN
        assert "credential" in check.message.lower()

    def test_ci_environment_skips_keyring(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Private feed, CI=true in env -> no keyring checks, OK with skip message."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=_LOCK_CLEAN)
        report = DoctorReport()
        monkeypatch.setenv("CI", "true")

        # Act
        check_feeds(target, report)

        # Assert -- no feed-keyring FAIL or WARN
        keyring_checks = _find_checks(report, "feed-keyring")
        assert all(c.status == CheckStatus.OK for c in keyring_checks)
        assert any("skip" in c.message.lower() for c in keyring_checks)


class TestCheckFeedsLockFreshness:
    """Lock file existence and freshness checks."""

    def test_lock_missing_warns(self, tmp_path: Path) -> None:
        """Private feed, uv.lock does not exist -> WARN for freshness, OK skip for leak."""
        # Arrange
        target = _write_project(tmp_path, pyproject=_PYPROJECT_PRIVATE_FEED, lock=None)
        report = DoctorReport()

        # Act
        check_feeds(target, report)

        # Assert -- freshness warns
        freshness = _find_check(report, "feed-lock-freshness")
        assert freshness is not None
        assert freshness.status == CheckStatus.WARN

        # Assert -- leak check emits OK with "skipped" message
        leak = _find_check(report, "feed-lock-leak")
        assert leak is not None
        assert leak.status == CheckStatus.OK
        assert "skip" in leak.message.lower()

    def test_lock_stale_warns(self, tmp_path: Path) -> None:
        """Private feed, uv.lock older than pyproject.toml -> WARN for freshness."""
        # Arrange -- lock mtime 60s before pyproject.toml
        target = _write_project(
            tmp_path,
            pyproject=_PYPROJECT_PRIVATE_FEED,
            lock=_LOCK_CLEAN,
            lock_mtime_offset=-60.0,
        )
        report = DoctorReport()

        # Act
        check_feeds(target, report)

        # Assert
        freshness = _find_check(report, "feed-lock-freshness")
        assert freshness is not None
        assert freshness.status == CheckStatus.WARN
        assert "stale" in freshness.message.lower() or "older" in freshness.message.lower()
