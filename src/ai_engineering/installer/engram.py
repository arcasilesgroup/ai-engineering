"""Install-time wiring for the third-party Engram memory product.

Spec-123 D-123-12 / D-123-29 (Phase 5).

Engram (https://github.com/Gentleman-Programming/engram) is a *peer*
memory product, not an ai-engineering dependency.  This module contains
the **install-time only** glue that lets ``ai-eng install`` ask whether
to opt in and, on a "yes" answer, invoke Engram's documented install
path for the host OS plus ``engram setup <ide>`` for the active IDE.

Design constraints (per spec-123):

- No Engram-specific *runtime* code anywhere in ai-engineering.  Only the
  install-time prompt + per-OS dispatch lives here.
- The integration is non-blocking: any failure surfaces a structured
  :class:`InstallResult` with ``success=False`` so ``ai-eng install``
  continues regardless of Engram's availability.
- The host machine is never modified outside ``install_engram``; the
  prompt path can short-circuit for ``--engram`` / ``--no-engram`` flags
  and for non-tty (CI) sessions which default to *skip*.

Subprocess invocations:

- macOS:   ``brew install engram``
- Linux:   ``curl -fsSL <release-url> -o <dest>`` then ``chmod +x``
- Windows: ``winget install Engram``
- Setup:   ``engram setup <ide>`` (after the install succeeds and the IDE
  is one of the four canonical agents).

Tests in :mod:`tests.unit.installer.test_engram_prompt` mock every
subprocess call so the developer machine is never touched by the suite.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


OsName = Literal["macos", "linux", "windows", "unknown"]
IdeName = Literal["claude-code", "codex", "gemini-cli", "github-copilot", "unknown"]


@dataclass(frozen=True)
class InstallResult:
    """Structured outcome of a single Engram install attempt.

    Attributes:
        success: True when the install pipeline completed without error
            (or when the user opted out -- see ``skipped``).
        message: Human-readable diagnostic.  Always populated.
        os_name: Detected OS at the time of install (canonical name).
        ide_name: Detected IDE at the time of install (canonical name).
        skipped: True when the user (or non-interactive default) opted
            out before any subprocess ran.  ``success`` stays True in
            that case because skipping is *not* a failure.
    """

    success: bool
    message: str
    os_name: OsName | str = "unknown"
    ide_name: IdeName | str = "unknown"
    skipped: bool = False


# Canonical Linux release binary location.  Engram publishes pre-built
# binaries on its GitHub releases page; we mirror the standard Unix
# convention (``/usr/local/bin`` if root, ``~/.local/bin`` otherwise).
_LINUX_RELEASE_URL = (
    "https://github.com/Gentleman-Programming/engram/releases/latest/download/engram-linux-x86_64"
)


def detect_os() -> OsName:
    """Return the canonical OS name for the current host.

    Maps :data:`sys.platform` values to the four labels Engram's install
    docs reference.  Anything outside that whitelist returns ``unknown``
    so the caller can short-circuit before shelling out to a missing
    package manager.
    """

    platform = sys.platform
    if platform == "darwin":
        return "macos"
    if platform.startswith("linux"):
        return "linux"
    if platform in {"win32", "cygwin"}:
        return "windows"
    return "unknown"


def detect_ide(project_root: Path | None = None) -> IdeName:
    """Detect the active IDE by inspecting project-root markers.

    The detection looks for the canonical configuration directories
    each agent ships:

    - ``.claude/``                       -> ``claude-code``
    - ``.codex/``                        -> ``codex``
    - ``.gemini/``                       -> ``gemini-cli``
    - ``.github/copilot-instructions.md``-> ``github-copilot``

    Args:
        project_root: Directory to inspect.  Defaults to the current
            working directory so the function can be called without a
            cwd argument from the install pipeline.

    Returns:
        The first marker that matches, or ``"unknown"`` if none do.
    """

    root = project_root if project_root is not None else Path.cwd()
    if (root / ".claude").is_dir():
        return "claude-code"
    if (root / ".codex").is_dir():
        return "codex"
    if (root / ".gemini").is_dir():
        return "gemini-cli"
    if (root / ".github" / "copilot-instructions.md").is_file():
        return "github-copilot"
    return "unknown"


def _linux_install_dir() -> Path:
    """Pick a writable install dir for the Linux release binary.

    ``/usr/local/bin`` for root; ``~/.local/bin`` otherwise.  The
    fallback path is the de-facto Linux user-bin convention and is
    almost always already on ``$PATH`` for interactive shells.

    ``os.geteuid`` is POSIX-only; on Windows callers exercising this
    helper through the test surface get the user-bin default without
    raising AttributeError.
    """

    geteuid = getattr(os, "geteuid", None)
    if geteuid is not None and geteuid() == 0:
        return Path("/usr/local/bin")
    return Path.home() / ".local" / "bin"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Thin ``subprocess.run`` wrapper that captures output as text.

    Centralised so the tests can patch a single call site
    (``ai_engineering.installer.engram.subprocess.run``).
    """

    logger.debug("engram install: invoking %s", cmd)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _install_macos() -> tuple[bool, str]:
    """Run ``brew install engram``.

    Returns ``(success, message)``.  Brew is the documented macOS path.
    Any non-zero exit surfaces the captured stderr to the caller.
    """

    result = _run(["brew", "install", "engram"])
    if result.returncode == 0:
        return True, "brew install engram succeeded"
    return False, f"brew install engram failed: {result.stderr.strip() or 'unknown error'}"


def _install_linux() -> tuple[bool, str]:
    """Download the Engram release binary and install it on $PATH.

    The path is chosen by :func:`_linux_install_dir`.  ``chmod +x`` is
    applied via a follow-up subprocess so the whole pipeline is mockable
    through a single ``subprocess.run`` patch.
    """

    install_dir = _linux_install_dir()
    binary_path = install_dir / "engram"
    try:
        install_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"failed to create install dir {install_dir}: {exc}"
    download = _run(
        [
            "curl",
            "-fsSL",
            _LINUX_RELEASE_URL,
            "-o",
            str(binary_path),
        ]
    )
    if download.returncode != 0:
        return False, (
            f"curl download of Engram release failed: {download.stderr.strip() or 'unknown error'}"
        )
    chmod_result = _run(["chmod", "+x", str(binary_path)])
    if chmod_result.returncode != 0:
        return False, (
            f"chmod +x on {binary_path} failed: {chmod_result.stderr.strip() or 'unknown error'}"
        )
    return True, f"Engram binary installed at {binary_path}"


def _install_windows() -> tuple[bool, str]:
    """Run ``winget install Engram``.

    Winget is the documented Windows path.  No GitHub-release fallback
    is wired here -- the install is opt-in and non-blocking, so a
    locked-down host without winget surfaces a structured failure to
    the operator who can retry manually.
    """

    result = _run(["winget", "install", "Engram"])
    if result.returncode == 0:
        return True, "winget install Engram succeeded"
    return False, f"winget install Engram failed: {result.stderr.strip() or 'unknown error'}"


def _run_engram_setup(ide_name: str) -> tuple[bool, str]:
    """Run ``engram setup <ide>`` after a successful install.

    Skips silently when the IDE is ``unknown`` (we still want the binary
    on PATH so the user can run setup themselves later).  Also skips for
    ``github-copilot`` -- Engram does not support that IDE today.
    """

    if ide_name == "unknown":
        return True, "skipped engram setup (unknown IDE)"
    if ide_name == "github-copilot":
        return True, "engram setup not run for github-copilot: not supported by Engram"
    result = _run(["engram", "setup", ide_name])
    if result.returncode == 0:
        return True, f"engram setup {ide_name} succeeded"
    return False, (f"engram setup {ide_name} failed: {result.stderr.strip() or 'unknown error'}")


def install_engram(os_name: str, ide_name: str) -> InstallResult:
    """Install Engram via the OS-appropriate path then run ``engram setup``.

    Non-blocking: any failure surfaces ``success=False`` and a populated
    ``message``.  Callers should log the result and continue.

    Args:
        os_name: One of ``macos`` / ``linux`` / ``windows`` (anything
            else short-circuits with ``success=False``).
        ide_name: Canonical IDE name (one of the four agents) or
            ``unknown``.  When ``unknown`` the install still runs but
            ``engram setup`` is skipped.

    Returns:
        An :class:`InstallResult` describing the outcome.
    """

    if os_name == "macos":
        ok, message = _install_macos()
    elif os_name == "linux":
        ok, message = _install_linux()
    elif os_name == "windows":
        ok, message = _install_windows()
    else:
        return InstallResult(
            success=False,
            message=f"unsupported OS: {os_name!r} -- install Engram manually",
            os_name=os_name,
            ide_name=ide_name,
        )

    if not ok:
        return InstallResult(
            success=False,
            message=message,
            os_name=os_name,
            ide_name=ide_name,
        )

    setup_ok, setup_message = _run_engram_setup(ide_name)
    final_message = f"{message}; {setup_message}"
    return InstallResult(
        success=setup_ok,
        message=final_message,
        os_name=os_name,
        ide_name=ide_name,
    )


def _resolve_interactive(interactive: bool | None) -> bool:
    """Resolve the effective interactive flag.

    ``None`` falls back to ``sys.stdin.isatty()`` so callers from CLI
    code paths that already know the tty state can pass an explicit
    boolean.
    """

    if interactive is None:
        return bool(sys.stdin.isatty())
    return interactive


def maybe_install_engram(
    *,
    force: bool | None,
    interactive: bool | None,
    project_root: Path | None = None,
) -> InstallResult:
    """Optionally prompt for and install Engram.

    Decision matrix:

    - ``force=True``  -> install without prompting (``--engram``).
    - ``force=False`` -> skip without prompting (``--no-engram``).
    - ``force=None`` and ``interactive=False`` -> skip (CI default).
    - ``force=None`` and ``interactive=True``  -> prompt.

    The prompt accepts ``y`` / ``yes`` (case-insensitive); anything
    else is treated as ``no`` so accidental ``Enter`` presses do not
    silently install a third-party product.

    Args:
        force: ``True`` to install, ``False`` to skip, ``None`` to
            consult the interactive prompt.
        interactive: ``True`` if the caller has a tty, ``False``
            otherwise.  ``None`` falls back to :func:`sys.stdin.isatty`.
        project_root: Optional directory used by :func:`detect_ide`.
            Defaults to the current working directory.

    Returns:
        An :class:`InstallResult`.  Skip paths set ``skipped=True``
        with ``success=True`` (skip is not a failure).
    """

    effective_interactive = _resolve_interactive(interactive)

    if force is True:
        return _do_install(project_root)
    if force is False:
        return InstallResult(
            success=True,
            message="Engram install skipped (--no-engram)",
            skipped=True,
        )
    if not effective_interactive:
        return InstallResult(
            success=True,
            message="Engram install skipped (non-interactive session)",
            skipped=True,
        )

    answer = input("Install Engram for memory persistence? [y/N] ").strip().lower()
    if answer in {"y", "yes"}:
        return _do_install(project_root)
    return InstallResult(
        success=True,
        message="Engram install skipped (user declined)",
        skipped=True,
    )


def _do_install(project_root: Path | None) -> InstallResult:
    """Run the per-OS install + setup pipeline.

    Extracted so :func:`maybe_install_engram` and any future direct
    caller (e.g., ``ai-eng install --engram`` re-run after a transient
    network failure) share a single execution path.
    """

    os_name = detect_os()
    ide_name = detect_ide(project_root)
    return install_engram(os_name, ide_name)


__all__ = [
    "InstallResult",
    "detect_ide",
    "detect_os",
    "install_engram",
    "maybe_install_engram",
]
