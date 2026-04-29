"""Linux distribution detection helper for spec-113 (D-113-05, D-113-06, G-13).

The framework recommends user-facing install commands tailored to the host
distribution (apk on Alpine, apt on Debian/Ubuntu, dnf on RHEL/Fedora,
pacman on Arch). The hint generator is decoupled from the detection so the
helper stays single-concern and test-fixture-friendly.

The detector parses ``/etc/os-release`` (the systemd standard, present on
Alpine 3.x, Debian 8+, Ubuntu 14.04+, RHEL 7+, Fedora 16+, Arch since 2012,
CentOS 7+) and reads the unquoted ``ID=`` field. Recognised IDs collapse to
the canonical token returned by :func:`detect_linux_distro`. Anything else
falls through to ``None`` so callers emit the generic hint without
guessing.

D-101-02 invariant: this module NEVER executes the package manager. It
only returns identification tokens that callers translate into hint
strings. Privilege escalation stays in the user's hands.
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Final

__all__ = (
    "DISTRO_PACKAGE_INSTALL_COMMAND",
    "detect_linux_distro",
    "format_install_command",
)


# /etc/os-release is the canonical Linux distribution identifier file
# (systemd interface stability promise; present on every distro shipped
# in the last decade). Stored as a module-level Path so tests can patch
# the symbol with a tmp_path fixture without monkeypatching open().
_OS_RELEASE_FILE: Final[Path] = Path("/etc/os-release")


# Mapping from recognised /etc/os-release ID values to the canonical
# distro token returned by :func:`detect_linux_distro`. The right-hand
# values map directly onto the package-manager command lookup below.
#
# IDs not present here (gentoo, slackware, openSUSE, ...) fall through to
# the generic token "linux" rather than None, so the caller still gets a
# usable distro-name surface for error messages while the
# install-command lookup degrades to the generic hint.
_OS_RELEASE_ID_MAP: Final[dict[str, str]] = {
    "alpine": "alpine",
    "debian": "debian",
    "ubuntu": "ubuntu",
    # Pop!_OS, Linux Mint, ElementaryOS, Kali — Ubuntu derivatives.
    "pop": "ubuntu",
    "linuxmint": "ubuntu",
    "elementary": "ubuntu",
    "kali": "debian",
    # Raspberry Pi OS reports as "raspbian"; package manager is apt.
    "raspbian": "debian",
    "rhel": "rhel",
    "centos": "centos",
    "fedora": "fedora",
    "rocky": "rhel",
    "almalinux": "rhel",
    "ol": "rhel",  # Oracle Linux
    "amzn": "rhel",  # Amazon Linux 2/2023 (dnf-compatible)
    "arch": "arch",
    "manjaro": "arch",
    "endeavouros": "arch",
}


# Per-distro package install command template. Keys MUST match the values
# in :data:`_OS_RELEASE_ID_MAP`. Each template carries a ``{pkg}``
# placeholder that callers substitute at format-time.
#
# D-113-06: hint commands include ``sudo`` for distros that require it
# (apt/dnf/pacman). Alpine ``apk`` does not need sudo in container
# root-by-default contexts; user-namespaced setups already prepend sudo
# at the user's discretion. The ``sudo`` is text addressed at the human
# operator -- the framework NEVER executes it (D-101-02 invariant).
DISTRO_PACKAGE_INSTALL_COMMAND: Final[dict[str, str]] = {
    "alpine": "apk add {pkg}",
    "debian": "sudo apt-get install -y {pkg}",
    "ubuntu": "sudo apt-get install -y {pkg}",
    "rhel": "sudo dnf install -y {pkg}",
    "fedora": "sudo dnf install -y {pkg}",
    "centos": "sudo dnf install -y {pkg}",
    "arch": "sudo pacman -S {pkg}",
}


def _read_os_release_id(path: Path) -> str | None:
    """Return the lower-case ``ID=`` value parsed from *path*; None on any error.

    Strips surrounding single or double quotes (``ID="alpine"`` and
    ``ID='alpine'`` both reduce to ``alpine``). Multi-token IDs (rare,
    e.g. ``ID="manjaro arm"``) are split on whitespace and the first
    token wins. Returns ``None`` when the file is missing, unreadable,
    or carries no ID line.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("ID="):
            continue
        value = line[len("ID=") :].strip()
        for quote in ('"', "'"):
            if value.startswith(quote) and value.endswith(quote):
                value = value[1:-1]
                break
        # Some distros set ID_LIKE-style values; keep only the first token.
        token = value.split()[0] if value else ""
        return token.lower() or None
    return None


def detect_linux_distro() -> str | None:
    """Return the canonical token for the current Linux distribution.

    Returns one of:

    * ``"alpine"``, ``"debian"``, ``"ubuntu"``, ``"rhel"``, ``"fedora"``,
      ``"centos"``, ``"arch"`` -- recognised distros with a package
      manager hint.
    * ``"linux"`` -- ``/etc/os-release`` is present but the ``ID`` value
      is unrecognised (gentoo, slackware, opensuse, ...).
    * ``None`` -- not Linux, or ``/etc/os-release`` is missing/unreadable.

    The function is total -- it never raises. Callers that want the
    package-manager command should pass the return value to
    :func:`format_install_command`. The token "linux" intentionally
    falls through to the generic hint there.
    """
    if (platform.system() or "").lower() != "linux":
        return None
    raw_id = _read_os_release_id(_OS_RELEASE_FILE)
    if raw_id is None:
        return None
    canonical = _OS_RELEASE_ID_MAP.get(raw_id)
    if canonical is not None:
        return canonical
    # Recognised file but unrecognised ID -- caller still gets a usable
    # token for diagnostics; the install command lookup will degrade to
    # the generic hint via :func:`format_install_command`.
    return "linux"


def format_install_command(distro: str | None, package: str) -> str:
    """Return the per-distro package-install command for *package*.

    Examples:

    * ``format_install_command("alpine", "curl")`` -> ``"apk add curl"``
    * ``format_install_command("debian", "wget")`` -> ``"sudo apt-get install -y wget"``
    * ``format_install_command("rhel", "jq")`` -> ``"sudo dnf install -y jq"``
    * ``format_install_command(None, "foo")`` -> generic 'use your package manager' hint.
    * ``format_install_command("linux", "foo")`` -> same generic hint as None.
    """
    if distro is None:
        return f"Install {package} using your distro's package manager"
    template = DISTRO_PACKAGE_INSTALL_COMMAND.get(distro)
    if template is None:
        return f"Install {package} using your distro's package manager"
    return template.format(pkg=package)
