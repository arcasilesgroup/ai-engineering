"""Unit tests for ``capture_os_release()`` -- spec-101 T-2.11 RED.

D-101-07 demands ``os_release`` be captured at **major.minor granularity
only** -- deliberately coarser than a kernel point release to avoid
nuisance re-probing on routine point/patch updates that do not affect
binary ABI in practice.

Resolution per OS:

* **macOS**: ``sw_vers -productVersion`` truncated to ``<major>.<minor>``
  (e.g. ``14.4.1`` -> ``14.4``).
* **Linux**: ``lsb_release -rs`` truncated to ``<major>.<minor>`` (distro
  release like ``22.04``); fall back to ``/etc/os-release`` ``VERSION_ID``
  if ``lsb_release`` is missing. Kernel point bumps (e.g. ``6.8.0-47``)
  must NOT trigger re-probe -- the function returns the distro release,
  never the kernel string.
* **Windows**: ``[System.Environment]::OSVersion.Version`` major.minor
  (e.g. ``10.0`` for Windows 10/11). Build numbers are intentionally
  ignored.

The helper lives in ``installer/user_scope_install.py`` as a
single-concern function (no PATH / shell logic -- those live in the
sibling helpers added in T-2.13/T-2.14).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _completed_proc(stdout: str = "", returncode: int = 0) -> SimpleNamespace:
    """Build a CompletedProcess-shaped double for subprocess.run patches."""
    return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)


# ---------------------------------------------------------------------------
# macOS -- sw_vers -productVersion truncation
# ---------------------------------------------------------------------------


class TestCaptureOsReleaseMacOS:
    """``sw_vers -productVersion`` is truncated to ``<major>.<minor>``."""

    def test_macos_14_4_1_captures_14_4(self) -> None:
        """A point release like 14.4.1 truncates to 14.4."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Darwin"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="14.4.1\n"),
            ),
        ):
            assert user_scope_install.capture_os_release() == "14.4"

    def test_macos_15_0_captures_15_0(self) -> None:
        """A clean major.minor is preserved verbatim."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Darwin"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="15.0\n"),
            ),
        ):
            assert user_scope_install.capture_os_release() == "15.0"

    def test_macos_sonoma_14_captures_14(self) -> None:
        """A bare major (no minor) is preserved as-is."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Darwin"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="14\n"),
            ),
        ):
            assert user_scope_install.capture_os_release() == "14"

    def test_macos_subprocess_failure_returns_empty(self) -> None:
        """When sw_vers fails, the helper returns an empty string."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Darwin"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="", returncode=1),
            ),
        ):
            assert user_scope_install.capture_os_release() == ""


# ---------------------------------------------------------------------------
# Linux -- lsb_release first; /etc/os-release fallback
# ---------------------------------------------------------------------------


class TestCaptureOsReleaseLinux:
    """``lsb_release -rs`` is preferred; ``/etc/os-release`` is the fallback."""

    def test_linux_lsb_release_22_04_captures_22_04(self) -> None:
        """lsb_release returning 22.04 captures 22.04 verbatim."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value="/usr/bin/lsb_release"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="22.04\n"),
            ),
        ):
            assert user_scope_install.capture_os_release() == "22.04"

    def test_linux_lsb_release_22_04_3_truncates_to_22_04(self) -> None:
        """A point release like 22.04.3 truncates to 22.04."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value="/usr/bin/lsb_release"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="22.04.3\n"),
            ),
        ):
            assert user_scope_install.capture_os_release() == "22.04"

    def test_linux_kernel_point_bumps_not_returned(self) -> None:
        """Kernel point bumps (uname output 6.8.0-47) MUST NOT bleed in.

        The helper queries the distro release via lsb_release; the kernel
        version is irrelevant for re-probe decisions per D-101-07. This
        test patches lsb_release to return distro 24.04 and asserts the
        kernel string never appears.
        """
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value="/usr/bin/lsb_release"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="24.04\n"),
            ),
        ):
            captured = user_scope_install.capture_os_release()

        assert captured == "24.04"
        assert "6.8" not in captured
        assert "kernel" not in captured.lower()

    def test_linux_falls_back_to_os_release_when_lsb_missing(self, tmp_path) -> None:
        """When lsb_release is missing, /etc/os-release VERSION_ID is used."""
        from ai_engineering.installer import user_scope_install

        os_release_file = tmp_path / "os-release"
        os_release_file.write_text(
            'NAME="Ubuntu"\nVERSION_ID="22.04"\nPRETTY_NAME="Ubuntu 22.04 LTS"\n',
            encoding="utf-8",
        )

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value=None),
            patch.object(
                user_scope_install,
                "_OS_RELEASE_FILE",
                os_release_file,
            ),
        ):
            assert user_scope_install.capture_os_release() == "22.04"

    def test_linux_os_release_truncates_to_major_minor(self, tmp_path) -> None:
        """VERSION_ID with a patch number truncates to <major>.<minor>."""
        from ai_engineering.installer import user_scope_install

        os_release_file = tmp_path / "os-release"
        os_release_file.write_text(
            'NAME="Debian"\nVERSION_ID="12.4.0"\n',
            encoding="utf-8",
        )

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value=None),
            patch.object(
                user_scope_install,
                "_OS_RELEASE_FILE",
                os_release_file,
            ),
        ):
            assert user_scope_install.capture_os_release() == "12.4"

    def test_linux_no_lsb_no_os_release_returns_empty(self, tmp_path) -> None:
        """No detection source -> empty string (never raises)."""
        from ai_engineering.installer import user_scope_install

        missing = tmp_path / "absent" / "os-release"

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value=None),
            patch.object(
                user_scope_install,
                "_OS_RELEASE_FILE",
                missing,
            ),
        ):
            assert user_scope_install.capture_os_release() == ""

    def test_linux_lsb_release_blank_falls_back_to_os_release(self, tmp_path) -> None:
        """Empty lsb_release stdout falls through to /etc/os-release."""
        from ai_engineering.installer import user_scope_install

        os_release_file = tmp_path / "os-release"
        os_release_file.write_text('VERSION_ID="20.04"\n', encoding="utf-8")

        with (
            patch.object(user_scope_install.platform, "system", return_value="Linux"),
            patch.object(user_scope_install.shutil, "which", return_value="/usr/bin/lsb_release"),
            patch.object(
                user_scope_install.subprocess,
                "run",
                return_value=_completed_proc(stdout="\n"),
            ),
            patch.object(
                user_scope_install,
                "_OS_RELEASE_FILE",
                os_release_file,
            ),
        ):
            assert user_scope_install.capture_os_release() == "20.04"


# ---------------------------------------------------------------------------
# Windows -- platform.version() / platform.win32_ver() major.minor
# ---------------------------------------------------------------------------


class TestCaptureOsReleaseWindows:
    """Windows resolution truncates to ``<major>.<minor>``; build numbers ignored."""

    def test_windows_10_returns_10_0(self) -> None:
        """``[System.Environment]::OSVersion.Version`` -> ``10.0`` for Win 10/11."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Windows"),
            patch.object(user_scope_install.platform, "version", return_value="10.0.19045"),
        ):
            assert user_scope_install.capture_os_release() == "10.0"

    def test_windows_11_returns_10_0_per_spec_d101_07(self) -> None:
        """Windows 11 still reports 10.0 -- build numbers ignored per D-101-07."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Windows"),
            patch.object(user_scope_install.platform, "version", return_value="10.0.22631"),
        ):
            assert user_scope_install.capture_os_release() == "10.0"

    def test_windows_blank_version_returns_empty(self) -> None:
        """Empty platform.version() output -> empty captured release."""
        from ai_engineering.installer import user_scope_install

        with (
            patch.object(user_scope_install.platform, "system", return_value="Windows"),
            patch.object(user_scope_install.platform, "version", return_value=""),
        ):
            assert user_scope_install.capture_os_release() == ""


# ---------------------------------------------------------------------------
# Unknown OS -- defensive empty
# ---------------------------------------------------------------------------


class TestCaptureOsReleaseUnknown:
    """Unknown ``platform.system()`` returns an empty string defensively."""

    def test_unknown_os_returns_empty(self) -> None:
        """An unknown OS name (e.g. ``Plan9``) -> empty release."""
        from ai_engineering.installer import user_scope_install

        with patch.object(user_scope_install.platform, "system", return_value="Plan9"):
            assert user_scope_install.capture_os_release() == ""


# ---------------------------------------------------------------------------
# API contract -- single-concern, returns str, never raises
# ---------------------------------------------------------------------------


class TestCaptureOsReleaseContract:
    """``capture_os_release`` is a single-concern, total function."""

    def test_returns_str(self) -> None:
        """Always returns a string (never None, never raises)."""
        from ai_engineering.installer import user_scope_install

        with patch.object(user_scope_install.platform, "system", return_value=""):
            result = user_scope_install.capture_os_release()

        assert isinstance(result, str)

    def test_no_path_logic(self) -> None:
        """The helper does NOT touch PATH / shell detection.

        Single-concern guard per the T-2.12 spec: ``capture_os_release``
        only returns the OS release string; PATH + shell snippet
        emission lives in the sibling helpers.
        """
        from ai_engineering.installer import user_scope_install

        # The function exists at module level and the module exposes the
        # PATH helper as a separate public symbol (asserted in the
        # T-2.13 RED file). Here we just guard that the function is
        # callable in isolation.
        assert callable(user_scope_install.capture_os_release)

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("14.4.1", "14.4"),
            ("14.4", "14.4"),
            ("14", "14"),
            ("", ""),
            ("22.04.3", "22.04"),
            ("12.4.0", "12.4"),
        ],
    )
    def test_truncate_helper_major_minor(self, raw: str, expected: str) -> None:
        """The internal truncation helper returns at most two dotted parts."""
        from ai_engineering.installer import user_scope_install

        assert user_scope_install._truncate_to_major_minor(raw) == expected
