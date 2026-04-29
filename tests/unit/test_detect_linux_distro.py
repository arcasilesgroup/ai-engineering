"""Tests for :func:`ai_engineering.installer.distro.detect_linux_distro` (G-13).

The detector parses ``/etc/os-release`` and collapses recognised IDs to a
canonical token used by the install-hint generator. Coverage targets:

* recognised IDs (alpine, debian, ubuntu, rhel, fedora, centos, arch);
* derivative IDs (pop -> ubuntu, manjaro -> arch, raspbian -> debian, ...);
* unrecognised IDs return the generic ``"linux"`` token;
* missing / unreadable / non-Linux platforms return ``None``;
* quoting variants (``ID="alpine"`` vs ``ID='alpine'`` vs ``ID=alpine``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer import distro as distro_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_os_release(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Point the module's _OS_RELEASE_FILE at *path* and force platform=linux."""
    monkeypatch.setattr(distro_mod, "_OS_RELEASE_FILE", path)
    monkeypatch.setattr(distro_mod.platform, "system", lambda: "Linux")


def _write_os_release(tmp_path: Path, body: str) -> Path:
    """Write *body* to a tmp os-release fixture and return its path."""
    target = tmp_path / "os-release"
    target.write_text(body, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Recognised distros (one token per supported distro)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("os_release_id", "expected_token"),
    [
        ("alpine", "alpine"),
        ("debian", "debian"),
        ("ubuntu", "ubuntu"),
        ("rhel", "rhel"),
        ("fedora", "fedora"),
        ("centos", "centos"),
        ("arch", "arch"),
    ],
)
def test_detect_recognised_distros(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_release_id: str,
    expected_token: str,
) -> None:
    """Each recognised ID collapses to its canonical token."""
    fixture = _write_os_release(tmp_path, f'ID={os_release_id}\nVERSION_ID="1.0"\n')
    _patch_os_release(monkeypatch, fixture)
    assert distro_mod.detect_linux_distro() == expected_token


@pytest.mark.parametrize(
    ("os_release_id", "expected_token"),
    [
        ("pop", "ubuntu"),
        ("linuxmint", "ubuntu"),
        ("elementary", "ubuntu"),
        ("kali", "debian"),
        ("raspbian", "debian"),
        ("rocky", "rhel"),
        ("almalinux", "rhel"),
        ("ol", "rhel"),
        ("amzn", "rhel"),
        ("manjaro", "arch"),
        ("endeavouros", "arch"),
    ],
)
def test_detect_derivative_distros_collapse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_release_id: str,
    expected_token: str,
) -> None:
    """Distro derivatives map to their canonical parent token."""
    fixture = _write_os_release(tmp_path, f"ID={os_release_id}\n")
    _patch_os_release(monkeypatch, fixture)
    assert distro_mod.detect_linux_distro() == expected_token


# ---------------------------------------------------------------------------
# Quoting variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "ID=alpine",
        'ID="alpine"',
        "ID='alpine'",
        '   ID="alpine"   ',  # leading/trailing whitespace
    ],
)
def test_detect_handles_quoting_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line: str
) -> None:
    """``ID=`` parsing strips surrounding single/double quotes + whitespace."""
    fixture = _write_os_release(tmp_path, line + "\n")
    _patch_os_release(monkeypatch, fixture)
    assert distro_mod.detect_linux_distro() == "alpine"


def test_detect_multi_token_id_uses_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``ID="manjaro arm"`` collapses on the first whitespace token."""
    fixture = _write_os_release(tmp_path, 'ID="manjaro arm"\n')
    _patch_os_release(monkeypatch, fixture)
    assert distro_mod.detect_linux_distro() == "arch"


# ---------------------------------------------------------------------------
# Unrecognised + missing inputs
# ---------------------------------------------------------------------------


def test_detect_unrecognised_id_returns_generic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unrecognised ID returns the generic ``"linux"`` token."""
    fixture = _write_os_release(tmp_path, "ID=gentoo\n")
    _patch_os_release(monkeypatch, fixture)
    assert distro_mod.detect_linux_distro() == "linux"


def test_detect_missing_os_release_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Absent ``/etc/os-release`` returns ``None`` (caller emits generic hint)."""
    nonexistent = tmp_path / "absent"
    _patch_os_release(monkeypatch, nonexistent)
    assert distro_mod.detect_linux_distro() is None


def test_detect_os_release_without_id_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``/etc/os-release`` present but missing ID line returns ``None``."""
    fixture = _write_os_release(tmp_path, 'VERSION_ID="1.0"\nNAME="Mystery OS"\n')
    _patch_os_release(monkeypatch, fixture)
    assert distro_mod.detect_linux_distro() is None


def test_detect_non_linux_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Detector early-returns ``None`` when ``platform.system()`` is not Linux."""
    fixture = _write_os_release(tmp_path, "ID=alpine\n")
    monkeypatch.setattr(distro_mod, "_OS_RELEASE_FILE", fixture)
    monkeypatch.setattr(distro_mod.platform, "system", lambda: "Darwin")
    assert distro_mod.detect_linux_distro() is None

    monkeypatch.setattr(distro_mod.platform, "system", lambda: "Windows")
    assert distro_mod.detect_linux_distro() is None


def test_detect_unreadable_file_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OSError during read degrades to ``None`` rather than raising."""

    class _Path(type(tmp_path)):  # type: ignore[misc]
        pass

    fixture = tmp_path / "os-release"
    fixture.write_text("ID=alpine\n", encoding="utf-8")

    def _boom(self, encoding: str = "utf-8") -> str:
        raise OSError("EACCES")

    monkeypatch.setattr(distro_mod, "_OS_RELEASE_FILE", fixture)
    monkeypatch.setattr(distro_mod.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "read_text", _boom, raising=True)
    assert distro_mod.detect_linux_distro() is None


# ---------------------------------------------------------------------------
# format_install_command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("distro", "package", "expected"),
    [
        ("alpine", "curl", "apk add curl"),
        ("alpine", "wget", "apk add wget"),
        ("debian", "wget", "sudo apt-get install -y wget"),
        ("ubuntu", "git", "sudo apt-get install -y git"),
        ("rhel", "jq", "sudo dnf install -y jq"),
        ("fedora", "jq", "sudo dnf install -y jq"),
        ("centos", "curl", "sudo dnf install -y curl"),
        ("arch", "shellcheck", "sudo pacman -S shellcheck"),
    ],
)
def test_format_install_command_per_distro(distro: str, package: str, expected: str) -> None:
    """Hint formatter emits the canonical command per recognised distro."""
    assert distro_mod.format_install_command(distro, package) == expected


def test_format_install_command_none_returns_generic_hint() -> None:
    """``None`` distro falls through to the generic 'use your package manager' hint."""
    assert (
        distro_mod.format_install_command(None, "foo")
        == "Install foo using your distro's package manager"
    )


def test_format_install_command_generic_linux_falls_through() -> None:
    """The ``"linux"`` fallback token also returns the generic hint."""
    assert (
        distro_mod.format_install_command("linux", "foo")
        == "Install foo using your distro's package manager"
    )
