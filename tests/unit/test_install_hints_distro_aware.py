"""Tests for spec-113 G-3 / D-113-05 / D-113-06: distro-aware install hints.

The hint generator switches command flavour by host OS:

* macOS  -> ``brew install <pkg>``
* Alpine -> ``apk add <pkg>``
* Debian/Ubuntu -> ``sudo apt-get install -y <pkg>``
* RHEL/Fedora/CentOS -> ``sudo dnf install -y <pkg>``
* Arch -> ``sudo pacman -S <pkg>``
* Windows -> ``winget install <pkg>``
* Unknown Linux -> ``Install <pkg> using your distro's package manager``

Drivers with a dedicated upstream installer (uv, rustup, brew, ...)
short-circuit the distro lookup with the direct-upstream hint.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer import distro as distro_mod
from ai_engineering.installer import user_scope_install as usi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_platform(monkeypatch: pytest.MonkeyPatch, system: str) -> None:
    """Pin ``platform.system()`` for both modules touched by the hint flow."""
    monkeypatch.setattr(usi.platform, "system", lambda: system)
    monkeypatch.setattr(distro_mod.platform, "system", lambda: system)


def _patch_os_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, distro_id: str) -> None:
    """Write a fixture os-release file and point the detector at it."""
    fixture = tmp_path / "os-release"
    fixture.write_text(f"ID={distro_id}\n", encoding="utf-8")
    monkeypatch.setattr(distro_mod, "_OS_RELEASE_FILE", fixture)


# ---------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------


def test_macos_recommends_brew(monkeypatch: pytest.MonkeyPatch) -> None:
    """On macOS the hint recommends ``brew install <pkg>``."""
    _patch_platform(monkeypatch, "Darwin")
    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert "brew install curl" in msg
    assert "Cannot install gitleaks" in msg


def test_macos_uses_alias_for_llvm_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """``llvm-config`` is shipped via the ``llvm`` brew formula."""
    _patch_platform(monkeypatch, "Darwin")
    msg = usi._format_missing_driver_message("llvm-config", tool="clang-tidy")
    assert "brew install llvm" in msg


# ---------------------------------------------------------------------------
# Linux distros
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("distro_id", "expected_command"),
    [
        ("alpine", "apk add curl"),
        ("debian", "sudo apt-get install -y curl"),
        ("ubuntu", "sudo apt-get install -y curl"),
        ("rhel", "sudo dnf install -y curl"),
        ("fedora", "sudo dnf install -y curl"),
        ("centos", "sudo dnf install -y curl"),
        ("arch", "sudo pacman -S curl"),
    ],
)
def test_linux_distro_install_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    distro_id: str,
    expected_command: str,
) -> None:
    """Each recognised distro carries its own package-manager install command."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, distro_id)

    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert expected_command in msg
    assert "Cannot install gitleaks" in msg
    assert "driver" not in msg, "G-4: error message must not surface 'driver' jargon"


def test_linux_unknown_distro_emits_generic_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unrecognised /etc/os-release IDs degrade to the generic hint."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, "gentoo")

    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert "package manager" in msg
    assert "Cannot install gitleaks" in msg


def test_linux_missing_os_release_emits_generic_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No /etc/os-release at all -> generic hint, never an exception."""
    _patch_platform(monkeypatch, "Linux")
    monkeypatch.setattr(distro_mod, "_OS_RELEASE_FILE", tmp_path / "absent")

    msg = usi._format_missing_driver_message("wget", tool="ktlint")
    assert "package manager" in msg
    assert "Cannot install ktlint" in msg


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------


def test_windows_recommends_winget(monkeypatch: pytest.MonkeyPatch) -> None:
    """On Windows the hint recommends winget and falls back to scoop."""
    _patch_platform(monkeypatch, "Windows")
    msg = usi._format_missing_driver_message("curl", tool="gitleaks")
    assert "winget install curl" in msg
    assert "scoop install curl" in msg


# ---------------------------------------------------------------------------
# Direct-upstream short-circuits
# ---------------------------------------------------------------------------


def test_uv_uses_direct_upstream_hint_on_linux(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """uv has its own bootstrap installer -- distro lookup is bypassed."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, "alpine")

    msg = usi._format_missing_driver_message("uv", tool="ai-eng")
    assert "astral.sh/uv/install.sh" in msg


def test_brew_short_circuits_to_brew_install_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bootstrapping brew itself points to brew.sh."""
    _patch_platform(monkeypatch, "Darwin")
    msg = usi._format_missing_driver_message("brew", tool=None)
    assert "brew.sh" in msg


# ---------------------------------------------------------------------------
# Tool-less message variant
# ---------------------------------------------------------------------------


def test_message_without_tool_uses_secondary_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When *tool* is None, the message degrades to the driver-only shape."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, "alpine")

    msg = usi._format_missing_driver_message("curl", tool=None)
    assert "is required by ai-engineering" in msg
    assert "apk add curl" in msg
    assert "Cannot install" not in msg
    assert "driver" not in msg


# ---------------------------------------------------------------------------
# Backwards compat: legacy single-arg call still works
# ---------------------------------------------------------------------------


def test_legacy_single_arg_invocation_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-spec-113 callers that invoke without ``tool=...`` still get a hint."""
    _patch_platform(monkeypatch, "Linux")
    _patch_os_release(tmp_path, monkeypatch, "ubuntu")

    msg = usi._format_missing_driver_message("curl")
    assert "is required by ai-engineering" in msg
    assert "sudo apt-get install -y curl" in msg
