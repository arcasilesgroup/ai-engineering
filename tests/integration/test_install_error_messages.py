"""Integration test for spec-113 G-4: user-facing install error message.

Asserts the new shape of the install-failure surface:

    Cannot install <tool>: '<driver>' is required to download release
    binaries. <distro_command>

The legacy "driver 'curl' not found on PATH -- install curl via your OS
package manager (brew/winget/scoop)" shape is dropped. The new message
respects host platform: macOS recommends brew, Alpine recommends apk,
Debian/Ubuntu recommends apt, etc.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer import distro as distro_mod
from ai_engineering.installer import user_scope_install as usi


def _patch_platform(monkeypatch: pytest.MonkeyPatch, system: str) -> None:
    monkeypatch.setattr(usi.platform, "system", lambda: system)
    monkeypatch.setattr(distro_mod.platform, "system", lambda: system)


def _patch_os_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, distro_id: str) -> None:
    fixture = tmp_path / "os-release"
    fixture.write_text(f"ID={distro_id}\n", encoding="utf-8")
    monkeypatch.setattr(distro_mod, "_OS_RELEASE_FILE", fixture)


def test_install_error_drops_driver_jargon(monkeypatch: pytest.MonkeyPatch) -> None:
    """G-4: the new error message no longer surfaces 'driver' as an internal name."""
    _patch_platform(monkeypatch, "Darwin")
    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert "driver" not in msg, f"G-4 forbids 'driver' jargon in user message; got {msg!r}"


def test_install_error_alpine_message_full_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Alpine variant matches the spec's example exactly."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, "alpine")

    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert msg == (
        "Cannot install gitleaks: 'curl' is required to download "
        "release binaries. Install with: apk add curl"
    )


@pytest.mark.parametrize(
    ("distro_id", "expected_command"),
    [
        ("alpine", "apk add wget"),
        ("debian", "sudo apt-get install -y wget"),
        ("ubuntu", "sudo apt-get install -y wget"),
        ("rhel", "sudo dnf install -y wget"),
        ("fedora", "sudo dnf install -y wget"),
        ("arch", "sudo pacman -S wget"),
    ],
)
def test_install_error_per_distro_recommendation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    distro_id: str,
    expected_command: str,
) -> None:
    """G-4 + G-3: per-distro install command shows up in the user-facing error."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, distro_id)

    msg = usi._format_missing_driver_message("wget", tool="ktlint")
    assert msg.startswith("Cannot install ktlint:")
    assert expected_command in msg
    assert "release binaries" in msg


def test_install_error_macos_recommends_brew(monkeypatch: pytest.MonkeyPatch) -> None:
    """G-4: macOS variant recommends brew, not apk/apt."""
    _patch_platform(monkeypatch, "Darwin")
    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert "brew install curl" in msg
    assert "apk" not in msg
    assert "apt" not in msg


def test_install_error_windows_recommends_winget(monkeypatch: pytest.MonkeyPatch) -> None:
    """G-4: Windows variant recommends winget + scoop, never apt."""
    _patch_platform(monkeypatch, "Windows")
    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert "winget install curl" in msg
    assert "scoop install curl" in msg
    assert "apt" not in msg
