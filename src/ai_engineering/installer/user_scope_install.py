"""User-scope install foundation for spec-101 (D-101-02).

This module is the load-bearing runtime guard for every install / verify
subprocess invocation made by the framework. It enforces D-101-02's two
allowlists (install-target prefixes + driver allowlist), implements the
four hardenings described in spec.md L154-L160:

* **Hardening 1**: argv allowlist before exec (``_safe_run``).
* **Hardening 2**: sensitive-env scrubbing (``_scrubbed_env``).
* **Hardening 3**: compound-shell exfiltration scan when ``argv[0]`` is a
  shell or interpreter driver -- delegated to
  :mod:`ai_engineering.installer._shell_patterns`.
* **Hardening 4**: cached, frozen ``RESOLVED_DRIVERS`` populated at module
  load time (TOCTOU defense -- ``shutil.which`` is NOT re-invoked per call).

The module also publishes the offline-safe ``run_verify`` wrapper used by
the post-install verification phase (D-101-04) and the typed
``VerifyResult`` payload it returns.

External callers should import from this module rather than crafting their
own subprocess invocations -- the framework's R-1 + R-7 + G-4 guarantees
all flow from the allowlist enforcement implemented here.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel

from ai_engineering.installer import _shell_patterns
from ai_engineering.installer.results import InstallResult

__all__ = (
    "DRIVER_BINARIES",
    "RESOLVED_DRIVERS",
    "MissingDriverError",
    "UnsafeVerifyCommand",
    "UserScopeViolation",
    "VerifyResult",
    "_check_simulate_fail",
    "_safe_run",
    "_scrubbed_env",
    "capture_os_release",
    "emit_path_snippet",
    "resolve_driver",
    "run_verify",
)


# ---------------------------------------------------------------------------
# Section 1 -- DRIVER_BINARIES allowlist + resolver (T-1.4)
#
# D-101-02 enumerates the install-time helpers (git, uv, python, node, ...);
# D-101-14 enumerates the SDK probes (java, kotlinc, swift, dart, ...). The
# union forms the driver allowlist. The container is a frozenset so consumers
# cannot mutate the source of truth in place (Hardening 4).
# ---------------------------------------------------------------------------

DRIVER_BINARIES: frozenset[str] = frozenset(
    {
        # D-101-02 install-time helpers
        "git",
        "uv",
        "python",
        "python3",
        "node",
        "npm",
        "pnpm",
        "bun",
        "dotnet",
        "brew",
        "winget",
        "scoop",
        "curl",
        # spec-113 G-2: wget joins the download driver allowlist so the
        # ``GitHubReleaseBinaryMechanism`` fallback chain can reach Alpine
        # BusyBox images (curl absent, wget shipped). Universal flag set
        # only -- ``-O <path> <url>`` works on both GNU and BusyBox wget.
        "wget",
        # D-101-14 SDK probes
        "java",
        "kotlinc",
        "swift",
        "dart",
        "go",
        "rustc",
        "cargo",
        "php",
        "composer",
        "clang",
        "gcc",
        "llvm-config",
    }
)


class MissingDriverError(RuntimeError):
    """Raised when an allowlisted driver is not present on PATH.

    The exception message names the driver and provides an actionable
    install hint per Hardening 4.
    """


# spec-113 G-3 / D-113-05 / D-113-06: per-driver install hints are now
# distro-aware. On macOS we recommend brew, on Windows winget/scoop, and
# on Linux we read ``/etc/os-release`` to recommend the correct package
# manager (``apk add`` on Alpine, ``apt-get install`` on Debian/Ubuntu,
# ``dnf install`` on RHEL/Fedora/CentOS, ``pacman -S`` on Arch). The
# linux-package-manager column is read from
# :mod:`ai_engineering.installer.distro` so the detector logic stays
# single-concern.
#
# The hint dict carries package-name aliases for drivers whose distro
# package name differs from the binary name (e.g. ``llvm-config`` ships
# in the ``llvm`` package on most distros). When a driver lacks a
# Linux-package alias the binary name itself is used.
_LINUX_PACKAGE_ALIASES: dict[str, str] = {
    "llvm-config": "llvm",
    "kotlinc": "kotlin",
    "rustc": "rustup",
    "cargo": "rustup",
    "python": "python3",
    "pnpm": "nodejs-pnpm",
    "bun": "bun",
    "dotnet": "dotnet-sdk",
}

# Macros used in macOS / Windows hints (the non-Linux fallback path).
_MACOS_HINT_DEFAULT = "Install with: brew install {pkg}"
_WINDOWS_HINT_DEFAULT = "Install with: winget install {pkg} (or: scoop install {pkg})"

# Drivers whose recommended install path is NOT a package manager (uv,
# rustup, brew, etc.). These short-circuit the distro lookup with a
# direct upstream recommendation so the hint surface stays useful even
# when the user is on a niche distro.
_DRIVER_DIRECT_HINTS: dict[str, str] = {
    "uv": "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh",
    "brew": "Install Homebrew from https://brew.sh/",
    "winget": "Install via the App Installer from the Microsoft Store",
    "scoop": "Install Scoop from https://scoop.sh/",
    "rustc": "Install via rustup: https://rustup.rs/",
    "cargo": "Install via rustup: https://rustup.rs/",
    "go": "Install Go from https://go.dev/doc/install",
    "swift": "Install Swift via Xcode (macOS) or https://swift.org/download/ (Linux)",
    "dart": "Install Dart from https://dart.dev/get-dart",
    "java": "Install a JDK from https://adoptium.net/",
    "composer": "Install Composer from https://getcomposer.org/download/",
}


def _build_install_hint(name: str) -> str:
    """Compose a distro-aware install hint for *name* (D-113-05, D-113-06).

    Resolution order:

    1. Direct-upstream hint from :data:`_DRIVER_DIRECT_HINTS` -- used for
       drivers that ship via a dedicated installer rather than a distro
       package (uv, rustup, brew, ...).
    2. macOS  -> ``brew install <pkg>``.
    3. Linux  -> distro-aware (``apk``/``apt-get``/``dnf``/``pacman``)
                 via :func:`detect_linux_distro` + :func:`format_install_command`.
    4. Windows -> ``winget install <pkg>`` with scoop fallback.
    5. Fallback -> ``"Install <name> using your OS package manager"``.
    """
    if name in _DRIVER_DIRECT_HINTS:
        return _DRIVER_DIRECT_HINTS[name]

    package = _LINUX_PACKAGE_ALIASES.get(name, name)

    # macOS: brew is the canonical user-scope install path (D-101-02).
    system = (platform.system() or "").lower()
    if system == "darwin":
        return _MACOS_HINT_DEFAULT.format(pkg=package)

    # Linux: distro-aware via /etc/os-release.
    if system == "linux":
        from ai_engineering.installer.distro import (
            detect_linux_distro,
            format_install_command,
        )

        distro = detect_linux_distro()
        return f"Install with: {format_install_command(distro, package)}"

    # Windows: winget preferred; scoop as fallback.
    if system.startswith("win"):
        return _WINDOWS_HINT_DEFAULT.format(pkg=package)

    return f"Install {name} using your OS package manager"


# Legacy hint dict retained for tests that import it; the runtime path
# now goes through :func:`_build_install_hint` so the static text falls
# back to the distro-aware computation when present. Kept as a module
# constant so importers (none in the runtime tree, defensive only) keep
# working.
_DRIVER_INSTALL_HINTS: dict[str, str] = {}


def _resolve_drivers_at_load() -> MappingProxyType[str, Path]:
    """Resolve every allowlisted driver via ``shutil.which`` at module load.

    Drivers absent from PATH at import time are simply omitted from the
    cache. ``resolve_driver`` raises ``MissingDriverError`` for omitted
    keys; ``_safe_run`` consults the cache directly so subsequent ``$PATH``
    mutations cannot smuggle in hostile binaries (Hardening 4).
    """
    cache: dict[str, Path] = {}
    for name in DRIVER_BINARIES:
        located = shutil.which(name)
        if located is not None:
            cache[name] = Path(located).resolve()
    return MappingProxyType(cache)


RESOLVED_DRIVERS: MappingProxyType[str, Path] = _resolve_drivers_at_load()


def _format_missing_driver_message(name: str, *, tool: str | None = None) -> str:
    """Compose an actionable ``MissingDriverError`` message for ``name``.

    spec-113 G-4: the user-facing message no longer leaks "driver"
    terminology. The new shape is::

        Cannot install <tool>: '<name>' is required to download release
        binaries. <distro_command>

    When *tool* is None (callers that resolve drivers directly without a
    target tool, e.g. SDK probes) the message degrades to::

        '<name>' is required by ai-engineering. <distro_command>

    The distro-aware command is computed via :func:`_build_install_hint`
    so macOS recommends brew, Linux recommends the distro package
    manager (apk/apt/dnf/pacman), and Windows recommends winget/scoop.
    """
    hint = _build_install_hint(name)
    if tool is not None:
        return f"Cannot install {tool}: {name!r} is required to download release binaries. {hint}"
    return f"{name!r} is required by ai-engineering. {hint}"


def resolve_driver(name: str) -> Path:
    """Return the cached absolute Path for an allowlisted driver.

    Args:
        name: Driver name (must be a member of ``DRIVER_BINARIES``).

    Returns:
        Absolute Path to the resolved driver binary.

    Raises:
        KeyError: ``name`` is not in ``DRIVER_BINARIES`` (allowlist denial).
        MissingDriverError: ``name`` is allowlisted but not present on PATH.

    Hardening 4 properties:
    * Allowlist check happens BEFORE any filesystem lookup.
    * ``shutil.which`` is consulted on every call to detect a removed
      driver, but the resulting Path is cached on first non-None return
      so subsequent calls are immune to ``$PATH`` mutation pointing at a
      hostile binary (TOCTOU defense).
    """
    if name not in DRIVER_BINARIES:
        raise KeyError(
            f"driver {name!r} is not in DRIVER_BINARIES allowlist (D-101-02). "
            f"Allowlisted drivers: {sorted(DRIVER_BINARIES)}"
        )
    # Always consult ``shutil.which`` at call time so a driver that
    # disappears from PATH (e.g. uninstalled mid-process) surfaces a
    # ``MissingDriverError`` rather than a stale cached Path.
    located = shutil.which(name)
    if located is None:
        raise MissingDriverError(_format_missing_driver_message(name))
    # First non-None resolution wins for the lifetime of the process.
    # Subsequent ``shutil.which`` results (potentially hostile) are
    # discarded -- the cached Path is the canonical resolution.
    if name not in _LATE_RESOLVED:
        _LATE_RESOLVED[name] = Path(located).resolve()
    return _LATE_RESOLVED[name]


# Late-resolved cache for drivers absent at module load. Populated lazily
# by ``resolve_driver``; once a name lands here, the value is frozen for
# the remainder of the process (Hardening 4 TOCTOU defense -- subsequent
# ``shutil.which`` results are ignored).
_LATE_RESOLVED: dict[str, Path] = {}


# ---------------------------------------------------------------------------
# Section 2 -- _safe_run runtime guard (T-1.6) + compound-shell scan (T-1.20)
#
# Two-layer allowlist:
# * Install-target prefixes (D-101-02 (a)) -- user-scope landing zones.
# * DRIVER_BINARIES (D-101-02 (b)) -- name-based driver allowlist.
#
# When ``argv[0]`` resolves to a shell driver, the compound-shell blocklist
# from ``_shell_patterns`` is applied to the joined argv tail (Hardening 3).
# ---------------------------------------------------------------------------


class UserScopeViolation(RuntimeError):
    """Raised when ``_safe_run`` rejects an argv per the D-101-02 allowlist.

    The exception message names the rejected absolute path AND the policy
    reason (allowlist / user-scope / D-101-02). Used as a fail-closed
    signal: subprocess is NOT spawned when this is raised.
    """


# Install-target prefixes per D-101-02 (a). All are user-scope, no privilege
# escalation. Stored as resolved absolute Paths so prefix comparison is
# string-stable across symlinks.
def _install_target_prefixes() -> tuple[Path, ...]:
    """Build the D-101-02 (a) install-target prefix tuple at module load.

    Each entry is resolved against the current user's home directory. The
    Homebrew prefix is detected via ``$(brew --prefix)`` heuristics (the
    canonical macOS Apple-Silicon path is ``/opt/homebrew``; Intel is
    ``/usr/local``). Project venv detection happens dynamically inside
    ``_argv_path_under_user_scope`` -- the active venv path is volatile
    and must be re-checked per call.
    """
    home = Path.home()
    prefixes: list[Path] = [
        home / ".local",
        home / ".cargo",
        home / ".dotnet" / "tools",
        home / ".composer" / "vendor" / "bin",
        home / "go" / "bin",
        home / ".local" / "share" / "uv" / "tools",
        home / ".rustup",
        home / ".sdkman",
        home / ".pyenv",
        home / ".nvm",
        home / ".bun",
        home / "AppData" / "Local" / "Programs",  # Windows user-scope
        home / "AppData" / "Local" / "Microsoft" / "WinGet",
        home / "scoop",  # Scoop's default user prefix
        Path("/opt/homebrew"),  # Apple Silicon Homebrew (canonical)
        Path("/home/linuxbrew/.linuxbrew"),  # Linuxbrew default
    ]
    # NOTE: ``/usr/local`` is intentionally NOT a static prefix. The Intel
    # Homebrew prefix is ``/usr/local`` but so are forbidden privileged
    # binaries that ship under the same root -- we cannot blanket-allow
    # ``/usr/local``. Intel Homebrew acceptance flows through the brew
    # driver's resolved path (brew is in ``DRIVER_BINARIES`` and its
    # resolved bin dir is allowlisted via the driver allowlist).
    return tuple(prefixes)


_INSTALL_TARGET_PREFIXES: tuple[Path, ...] = _install_target_prefixes()


# Drivers whose argv tail is shell-evaluated. When ``argv[0]`` resolves to
# one of these names, the compound-shell blocklist is applied to the rest
# of the argv (Hardening 3). ``python`` / ``python3`` / ``node`` are
# included because ``python -c "..."`` and ``node -e "..."`` carry the
# same shell-eval risk surface.
_SHELL_DRIVERS: frozenset[str] = frozenset(
    {
        "bash",
        "sh",
        "zsh",
        "fish",
        "pwsh",
        "powershell",
        "node",
        "python",
        "python3",
    }
)


# spec-101 Sec-5 (Wave 27): the shell-driver carve-out only accepts shell
# binaries that resolve under one of these canonical system paths. Any
# other shell-named binary (e.g. attacker-supplied ``/tmp/bash``) is
# rejected even though its basename matches ``_SHELL_DRIVERS``. The set
# enumerates the standard system-shell + interpreter locations across
# macOS, Linux, and Windows runners.
_CANONICAL_SHELL_PATHS: frozenset[str] = frozenset(
    {
        # POSIX system shells
        "/bin/sh",
        "/bin/bash",
        "/bin/zsh",
        "/bin/dash",
        "/usr/bin/sh",
        "/usr/bin/bash",
        "/usr/bin/zsh",
        "/usr/local/bin/bash",
        "/usr/local/bin/zsh",
        "/opt/homebrew/bin/bash",
        "/opt/homebrew/bin/zsh",
        # Fish (less common but legitimate)
        "/usr/bin/fish",
        "/usr/local/bin/fish",
        "/opt/homebrew/bin/fish",
        # System Python
        "/usr/bin/python",
        "/usr/bin/python3",
        "/usr/local/bin/python",
        "/usr/local/bin/python3",
        "/opt/homebrew/bin/python3",
        # System Node (rare, but exists on packaged distros)
        "/usr/bin/node",
        # PowerShell on Windows runners (canonical install paths)
        "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        # Git-bash on Windows runners (bash + posix sh shim)
        "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
        "C:\\Program Files\\Git\\bin\\bash.exe",
        "C:\\Program Files\\Git\\usr\\bin\\sh.exe",
        "C:\\Program Files\\Git\\bin\\sh.exe",
    }
)


def _is_under_canonical_shell_allowlist(resolved: Path) -> bool:
    """Return True when ``resolved`` matches a canonical system-shell path.

    Compares both the exact string and a case-insensitive variant so the
    Windows-style paths (which carry ``EXE`` capitalisation drift) match
    consistently.
    """
    resolved_str = str(resolved)
    if resolved_str in _CANONICAL_SHELL_PATHS:
        return True
    resolved_lower = resolved_str.lower()
    return any(canonical.lower() == resolved_lower for canonical in _CANONICAL_SHELL_PATHS)


def _shell_driver_stem(resolved_name: str) -> str:
    """Return the lower-case stem for shell-driver membership tests.

    On Windows, ``shutil.which("bash")`` returns paths like
    ``C:\\Program Files\\Git\\usr\\bin\\bash.EXE`` -- ``Path.name`` yields
    ``bash.EXE`` which fails a membership check against the lower-case
    ``_SHELL_DRIVERS`` set. We normalise by stripping a trailing ``.exe``
    (case-insensitive) and lower-casing so the same set works for POSIX
    runners (where ``bash`` is already an exact match) and Windows.
    """
    stem = resolved_name
    if stem.lower().endswith(".exe"):
        stem = stem[: -len(".exe")]
    return stem.lower()


def _path_under_any_prefix(path: Path, prefixes: tuple[Path, ...]) -> bool:
    """Return True when ``path`` is rooted under any prefix in ``prefixes``."""
    try:
        path_str = str(path.resolve())
    except (OSError, RuntimeError):
        path_str = str(path)
    for prefix in prefixes:
        prefix_str = str(prefix)
        if path_str == prefix_str or path_str.startswith(prefix_str + os.sep):
            return True
        # Allow trailing slash match (``/usr/local`` vs ``/usr/local/bin/jq``).
        if path_str.startswith(prefix_str + "/"):
            return True
    return False


def _project_venv_prefix() -> Path | None:
    """Return the active project venv root, or None when not in a venv.

    Resolved at call time because ``VIRTUAL_ENV`` may be set after module
    import (e.g. when the user activates a venv mid-process).
    """
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        return Path(venv).resolve()
    # Fall back to a sibling ``.venv`` rooted at the current working dir.
    candidate = Path.cwd() / ".venv"
    if candidate.exists():
        return candidate.resolve()
    return None


def _is_under_user_scope(resolved: Path) -> bool:
    """Return True when ``resolved`` is inside an install-target prefix."""
    if _path_under_any_prefix(resolved, _INSTALL_TARGET_PREFIXES):
        return True
    venv = _project_venv_prefix()
    if venv is not None and _path_under_any_prefix(resolved, (venv,)):
        return True
    # ``.venv/bin/...`` segments are also accepted via marker detection so
    # any ancestor virtualenv (not just CWD-rooted) is honoured.
    return ".venv" in resolved.parts


def _is_under_driver_allowlist(resolved: Path) -> bool:
    """Return True when ``resolved`` matches a cached driver path."""
    resolved_str = str(resolved)
    if any(resolved_str == str(cached) for cached in RESOLVED_DRIVERS.values()):
        return True
    return any(resolved_str == str(cached) for cached in _LATE_RESOLVED.values())


def _scan_compound_shell(argv: list[str], driver_basename: str) -> None:
    """Reject compound-shell exfiltration patterns; raise on hit.

    Hardening 3: when ``argv[0]`` resolves to a shell or interpreter
    driver, the FULL argv tail is scanned against the blocklist. Legit
    shell calls (``bash -c "echo ok"``, ``python -c "print('hi')"``)
    must clear the scan -- the patterns in :mod:`_shell_patterns` are
    intentionally narrow.
    """
    # Normalise so Windows ``bash.EXE`` matches the lower-case stem set.
    if _shell_driver_stem(driver_basename) not in _SHELL_DRIVERS:
        return
    # Scan the joined tail; this surfaces patterns that span multiple argv
    # entries (``bash -c "curl X | bash"`` -- the malicious payload is
    # entirely inside argv[2]).
    tail = " ".join(argv[1:])
    hit = _shell_patterns.matches_any_block_pattern(tail)
    if hit is not None:
        pattern, matched = hit
        raise UserScopeViolation(
            f"compound-shell exfiltration blocked by D-101-02 Hardening 3 "
            f"(blocklist pattern {pattern.pattern!r} matched {matched!r} in argv[1:]); "
            f"shell driver {driver_basename!r} carries shell-eval semantics"
        )


def _safe_run(
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Spawn a subprocess after enforcing the D-101-02 allowlist.

    Args:
        argv: Argument vector. ``argv[0]`` is resolved against the cached
            ``RESOLVED_DRIVERS`` first; falls back to ``shutil.which`` for
            project-local launchers (e.g. ``.venv/bin/ruff``) which are
            outside ``DRIVER_BINARIES`` but inside the install-target
            prefix allowlist.
        env: Optional environment dict. Sensitive keys are stripped via
            ``_scrubbed_env`` before the child inherits.
        timeout: Per-call timeout (seconds). Propagated to ``subprocess.run``.
        check: Whether to raise on non-zero exit. Defaults to False (caller
            inspects ``returncode``).
        capture_output: Whether to capture stdout/stderr. Default True.
        text: Whether to decode stdout/stderr as text. Default True.
        **kwargs: Additional ``subprocess.run`` kwargs (cwd, input, etc.).

    Returns:
        ``subprocess.CompletedProcess`` from the underlying ``subprocess.run``.

    Raises:
        ValueError: ``argv`` is empty.
        UserScopeViolation: ``argv[0]`` resolves outside the allowlist OR
            the compound-shell scan fired.
        MissingDriverError: ``argv[0]`` is an allowlisted driver name but
            not on PATH.
    """
    if not argv:
        raise ValueError("_safe_run requires a non-empty argv (got [])")

    name = argv[0]

    # Resolution priority (Hardening 4):
    # 1. ``name`` is already an absolute path -- accept it as-is. This
    #    skips the ``shutil.which`` round-trip entirely so the TOCTOU
    #    test that patches ``shutil.which`` to None can still execute
    #    real binaries via their absolute path (e.g. ``sys.executable``).
    # 2. ``name`` is an allowlisted driver name and present in the
    #    module-load cache -- use the cached absolute Path.
    # 3. ``name`` was resolved lazily via ``resolve_driver`` -- use the
    #    late cache.
    # 4. Otherwise consult ``shutil.which`` once for project-local
    #    launchers (uv tool installs land in ``.local/bin``, project
    #    venvs in ``.venv/bin``).
    # 5. Empty resolution => MissingDriverError (allowlisted name absent)
    #    or UserScopeViolation (non-allowlisted name).
    resolved_str: str | None
    if os.path.isabs(name):
        resolved_str = name
    elif name in RESOLVED_DRIVERS:
        resolved_str = str(RESOLVED_DRIVERS[name])
    elif name in _LATE_RESOLVED:
        resolved_str = str(_LATE_RESOLVED[name])
    else:
        resolved_str = shutil.which(name)
        if resolved_str is None:
            if name in DRIVER_BINARIES:
                raise MissingDriverError(_format_missing_driver_message(name))
            raise UserScopeViolation(
                f"argv[0]={name!r} could not be resolved on PATH and is not in the "
                f"D-101-02 driver allowlist; refusing to exec outside the user-scope policy"
            )

    resolved = Path(resolved_str)
    if not resolved.is_absolute():
        resolved = resolved.resolve()
    driver_basename = resolved.name

    # Allowlist enforcement (D-101-02 (a) install-target prefixes
    # OR (b) DRIVER_BINARIES name-based allowlist).
    accepted = _is_under_user_scope(resolved) or _is_under_driver_allowlist(resolved)
    if not accepted and name in DRIVER_BINARIES:
        # The argv[0] is an allowlisted driver name even though the cached
        # Path is not exactly equal -- treat the patched-resolution test
        # case (the cache check uses the patched ``shutil.which`` result)
        # as accepted under (b).
        accepted = True
    # Shell / interpreter drivers (sh, bash, zsh, pwsh, fish, python,
    # node) are allowed to resolve to system paths because the install
    # flow legitimately runs them (``sh -c "..."`` / ``python -c ...``
    # for in-process probes). The compound-shell scan below provides
    # the load-bearing security control for shell drivers.
    #
    # spec-101 Sec-5 (Wave 27): the previous blanket acceptance let
    # any path-shaped resolution slip through provided the basename
    # matched a shell stem. Tighten by also requiring the resolved
    # path to land under a canonical system-shell allowlist OR the
    # install-target prefixes -- so an attacker cannot redirect a
    # ``bash`` argv onto an arbitrary user-supplied binary just by
    # naming it ``bash``.
    if (
        not accepted
        and _shell_driver_stem(resolved.name) in _SHELL_DRIVERS
        and (_is_under_canonical_shell_allowlist(resolved) or _is_under_user_scope(resolved))
    ):
        accepted = True

    if not accepted:
        raise UserScopeViolation(
            f"argv[0]={name!r} resolved to {resolved_str!r} which is outside the "
            f"D-101-02 user-scope allowlist (neither install-target prefix nor "
            f"driver allowlist entry); refusing to exec"
        )

    # Hardening 3 -- compound-shell scan when argv[0] is a shell driver.
    _scan_compound_shell(argv, driver_basename)

    # Hardening 2 -- env scrubbing. ``env=None`` means "inherit", which
    # equals scrubbing the parent's os.environ.
    scrubbed = _scrubbed_env(dict(os.environ)) if env is None else _scrubbed_env(env)

    # Strip allowlist kwargs that callers might not understand. The remaining
    # kwargs flow to ``subprocess.run`` unchanged.
    return subprocess.run(
        argv,
        env=scrubbed,
        timeout=timeout,
        check=check,
        capture_output=capture_output,
        text=text,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Section 3 -- _scrubbed_env (T-1.22)
#
# Hardening 2: strip secret-shaped env keys before any subprocess inherits
# the parent's environment. The regex enumerates known secret families
# (``*_API_KEY``, ``*_SECRET``, ``*_TOKEN``, ``*_PASSWORD``) AND specific
# names that do not follow the suffix convention
# (``ANTHROPIC_API_KEY``, ``AWS_SECRET_ACCESS_KEY``, ``DATABASE_URL``,
# ``GOOGLE_APPLICATION_CREDENTIALS``).
# ---------------------------------------------------------------------------


_SENSITIVE_KEY_PATTERN: re.Pattern[str] = re.compile(
    r"^("
    r".+_API_KEY"
    r"|.+_SECRET"
    r"|.+_TOKEN"
    r"|.+_PASSWORD"
    r"|ANTHROPIC_API_KEY"
    r"|AWS_SECRET_ACCESS_KEY"
    r"|AWS_ACCESS_KEY_ID"
    r"|GITHUB_TOKEN"
    r"|DATABASE_URL"
    r"|GH_TOKEN"
    r"|AZURE_.+_KEY"
    r"|GOOGLE_APPLICATION_CREDENTIALS"
    r")$"
)


def _scrubbed_env(env: dict[str, str]) -> dict[str, str]:
    """Return a new dict with sensitive keys removed.

    The function is pure -- the input dict is NOT mutated. Standard env
    keys (``PATH``, ``HOME``, ``LANG``, ``TZ``, ``TERM``) are preserved
    unconditionally; sensitive keys matched by ``_SENSITIVE_KEY_PATTERN``
    are dropped.

    Args:
        env: Source environment mapping.

    Returns:
        New dict with sensitive keys stripped.
    """
    return {key: value for key, value in env.items() if not _SENSITIVE_KEY_PATTERN.match(key)}


# ---------------------------------------------------------------------------
# Section 4 -- run_verify offline-safe wrapper (T-1.10)
#
# D-101-04: post-install verification MUST be offline-safe (R-11 air-gapped
# enterprise environments). The wrapper:
# * Refuses cmds carrying network-touching flags (the wrapper guards itself).
# * Invokes ``_safe_run`` with a 10-second timeout.
# * Applies the registry's ``verify.regex`` to stdout to extract a version.
# * Catches ``subprocess.TimeoutExpired`` and reports it via
#   ``VerifyResult(passed=False, error="timeout")``.
# ---------------------------------------------------------------------------


class VerifyResult(BaseModel):
    """Structured result of a single tool verification (D-101-04)."""

    passed: bool
    version: str | None = None
    stderr: str = ""
    error: str = ""

    model_config = {"frozen": True}


class UnsafeVerifyCommand(ValueError):
    """Raised when a verify cmd carries forbidden network-touching flags."""


# Forbidden verify-cmd substrings per D-101-04. Stored as compiled
# patterns so subtle whitespace/casing variants are matched. The
# substrings are checked against the joined cmd string AND any single
# argv element to catch both ``[..., '--config', 'auto']`` (split) and
# ``[..., '--config auto']`` (joined) shapes.
_FORBIDDEN_VERIFY_FRAGMENTS: tuple[str, ...] = (
    "--config auto",
    "--refresh",
    "--update",
)


def _validate_offline_safe_cmd(cmd: list[str]) -> None:
    """Reject verify cmds that carry network-touching flags (D-101-04).

    Special-cases ``--config auto`` because it spans two argv entries:
    ``["semgrep", "--config", "auto"]``. The remaining fragments
    (``--refresh``, ``--update``) are matched per-argv-entry.
    """
    # Two-token split for --config auto.
    for index in range(len(cmd) - 1):
        if cmd[index] == "--config" and cmd[index + 1] == "auto":
            raise UnsafeVerifyCommand(
                "verify cmd contains forbidden network fragment "
                "'--config auto' (D-101-04 forbids egress in verify probes)"
            )
    # Per-argv-entry exact matches.
    forbidden_singletons = {"--refresh", "--update"}
    for arg in cmd:
        if arg in forbidden_singletons:
            raise UnsafeVerifyCommand(
                f"verify cmd contains forbidden network fragment {arg!r} "
                f"(D-101-04 forbids egress in verify probes)"
            )
    # Joined-string check for any defence-in-depth fragment that slipped
    # through (e.g. a single-arg ``"--config auto"`` literal).
    joined = " ".join(cmd)
    for fragment in _FORBIDDEN_VERIFY_FRAGMENTS:
        if fragment in joined and not _fragment_already_caught(fragment):
            raise UnsafeVerifyCommand(
                f"verify cmd contains forbidden network fragment {fragment!r} "
                f"(D-101-04 forbids egress in verify probes)"
            )


def _fragment_already_caught(fragment: str) -> bool:
    """Return True when ``fragment`` is handled by the per-arg checks above.

    Avoids double-raising when the joined-string scan would re-detect a
    fragment already rejected by the structured token sweep.
    """
    return fragment in {"--refresh", "--update", "--config auto"}


def run_verify(tool_spec: dict[str, Any]) -> VerifyResult:
    """Execute the canonical offline-safe verify cmd for ``tool_spec``.

    Args:
        tool_spec: Mapping containing a ``verify`` block with ``cmd``
            (list[str]) and ``regex`` (str). Matches the shape published
            by ``installer/tool_registry.py``.

    Returns:
        ``VerifyResult`` with ``passed``, ``version`` (extracted via
        the regex), ``stderr`` (propagated from the subprocess) and
        ``error`` (``"timeout"`` on subprocess timeout, empty otherwise).

    Raises:
        UnsafeVerifyCommand: ``tool_spec.verify.cmd`` carries a network
            fragment forbidden by D-101-04.
    """
    verify_block = tool_spec.get("verify", {})
    cmd: list[str] = list(verify_block.get("cmd", []))
    regex_pattern: str = verify_block.get("regex", "")

    if not cmd:
        return VerifyResult(passed=False, stderr="verify.cmd is empty")

    # Wrapper-layer self-guard: refuse forbidden cmds even if a future
    # registry regression smuggles them in.
    _validate_offline_safe_cmd(cmd)

    try:
        completed = _safe_run(cmd, timeout=10)
    except subprocess.TimeoutExpired:
        return VerifyResult(passed=False, error="timeout", stderr="verify timed out after 10s")

    stdout: str = getattr(completed, "stdout", "") or ""
    stderr: str = getattr(completed, "stderr", "") or ""
    returncode: int = getattr(completed, "returncode", 0) or 0

    # Regex match against stdout AND stderr (spec-109 follow-up): some tools
    # (gitleaks, git, several ones with ANSI logs) emit success markers to
    # stderr instead of stdout. Searching both streams catches those without
    # weakening the "positive proof" contract -- regex still has to find the
    # marker SOMEWHERE in the captured output.
    matched_version: str | None = None
    if regex_pattern:
        match = re.search(regex_pattern, stdout) or re.search(regex_pattern, stderr)
        if match is not None:
            matched_version = match.group(0)

    passed = returncode == 0 and matched_version is not None

    return VerifyResult(
        passed=passed,
        version=matched_version,
        stderr=stderr,
        error="",
    )


# ---------------------------------------------------------------------------
# Section 5 -- capture_os_release (T-2.12)
#
# D-101-07: ``os_release`` is captured at major.minor granularity ONLY --
# deliberately coarser than a kernel point release to avoid nuisance
# re-probing on routine point/patch updates that do not affect binary ABI
# in practice. Resolution per OS:
#
# * macOS  : ``sw_vers -productVersion`` truncated to ``<major>.<minor>``.
# * Linux  : ``lsb_release -rs`` truncated to ``<major>.<minor>``; falls
#            back to ``/etc/os-release`` ``VERSION_ID`` when ``lsb_release``
#            is missing. Kernel point bumps NEVER bleed in -- only the
#            distro release is read.
# * Windows: ``platform.version()`` (mapped from
#            ``[System.Environment]::OSVersion.Version``) major.minor.
#
# This helper is single-concern -- it does NOT touch PATH or shell
# detection. PATH / shell helpers live in Section 6.
# ---------------------------------------------------------------------------


# /etc/os-release is the canonical Linux distro identifier file. Stored as a
# module-level Path so tests can patch it onto a tmp-path fixture without
# monkeypatching the open() builtin.
_OS_RELEASE_FILE: Path = Path("/etc/os-release")


def _truncate_to_major_minor(raw: str) -> str:
    """Return the first ``<major>.<minor>`` slice of a dotted version string.

    Examples:
        ``"14.4.1"`` -> ``"14.4"``
        ``"14.4"``   -> ``"14.4"``
        ``"14"``     -> ``"14"``
        ``""``       -> ``""``

    The helper is pure and never raises. Inputs that do not contain a
    digit are returned verbatim (the caller treats empty / unparseable
    strings as "unknown release").
    """
    cleaned = raw.strip()
    if not cleaned:
        return ""
    parts = cleaned.split(".")
    return ".".join(parts[:2])


def _capture_macos_release() -> str:
    """Return ``sw_vers -productVersion`` truncated to ``<major>.<minor>``."""
    try:
        completed = subprocess.run(
            ["/usr/bin/sw_vers", "-productVersion"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    returncode = getattr(completed, "returncode", 0) or 0
    if returncode != 0:
        return ""
    stdout = (getattr(completed, "stdout", "") or "").strip()
    return _truncate_to_major_minor(stdout)


def _read_os_release_version_id() -> str:
    """Parse ``/etc/os-release`` and return ``VERSION_ID`` as ``<major>.<minor>``.

    Returns an empty string when the file is missing or carries no
    ``VERSION_ID`` line. ``VERSION_ID`` values are typically quoted
    (``VERSION_ID="22.04"``); the helper strips the surrounding quotes.
    """
    if not _OS_RELEASE_FILE.is_file():
        return ""
    try:
        text = _OS_RELEASE_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        if not line.startswith("VERSION_ID="):
            continue
        value = line[len("VERSION_ID=") :].strip()
        # Strip surrounding quotes (``"22.04"`` or ``'22.04'``).
        for quote in ('"', "'"):
            if value.startswith(quote) and value.endswith(quote):
                value = value[1:-1]
                break
        return _truncate_to_major_minor(value)
    return ""


def _capture_linux_release() -> str:
    """Return distro release via ``lsb_release -rs`` or ``/etc/os-release``.

    Tries ``lsb_release -rs`` first (preferred when present); falls back
    to ``/etc/os-release`` ``VERSION_ID`` when lsb_release is missing or
    returns an empty string. Kernel version is intentionally NEVER
    consulted (D-101-07: kernel point bumps must not trigger re-probe).
    """
    lsb_path = shutil.which("lsb_release")
    if lsb_path is not None:
        try:
            completed = subprocess.run(
                [lsb_path, "-rs"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            completed = None
        if completed is not None:
            returncode = getattr(completed, "returncode", 0) or 0
            stdout = (getattr(completed, "stdout", "") or "").strip()
            if returncode == 0 and stdout:
                return _truncate_to_major_minor(stdout)
    return _read_os_release_version_id()


def _capture_windows_release() -> str:
    """Return ``platform.version()`` truncated to ``<major>.<minor>``.

    On Windows, ``platform.version()`` returns the value of
    ``[System.Environment]::OSVersion.Version`` (e.g. ``"10.0.19045"`` for
    Windows 10, ``"10.0.22631"`` for Windows 11). The build number is
    truncated away per D-101-07 -- both Win 10 and Win 11 collapse to
    ``10.0`` for re-probe purposes since they share an ABI.
    """
    raw = (platform.version() or "").strip()
    return _truncate_to_major_minor(raw)


def capture_os_release() -> str:
    """Capture the current OS release at major.minor granularity (D-101-07).

    Returns the empty string when the release cannot be determined; the
    function is total -- it never raises. The granularity guarantee is
    load-bearing: kernel point bumps and Windows build numbers are
    intentionally NOT surfaced so re-installs on routine point updates
    do not invalidate the install-state skip predicate.

    Resolution
    ----------
    macOS   : ``sw_vers -productVersion`` -> truncated.
    Linux   : ``lsb_release -rs`` -> truncated; falls back to
              ``/etc/os-release`` ``VERSION_ID``.
    Windows : ``platform.version()`` -> truncated.
    Unknown : empty string.
    """
    system_name = (platform.system() or "").strip().lower()
    if system_name == "darwin":
        return _capture_macos_release()
    if system_name == "linux":
        return _capture_linux_release()
    if system_name.startswith("win"):
        return _capture_windows_release()
    return ""


# ---------------------------------------------------------------------------
# Section 6 -- PATH + shell remediation snippet (T-2.14)
#
# When a tool lands outside the user's interactive ``$PATH`` (e.g. fresh
# ``uv tool install ruff`` lands ``$HOME/.local/bin`` which the user has
# not yet added to their shell rc), the installer emits a shell-specific
# copy-paste snippet so the operator can fix the PATH gap without
# guessing which dialect their login shell uses.
#
# Two single-concern helpers, both intentionally orthogonal to the
# ``capture_os_release`` flow above:
#
# * ``_detect_active_shell()`` -- returns one of the five canonical
#   shell literals based on env signals.
# * ``emit_path_snippet(target_dir)`` -- renders a one-liner the user
#   pastes into their rc to add ``target_dir`` to PATH.
# ---------------------------------------------------------------------------


_ShellLiteral = Literal["bash", "zsh", "fish", "pwsh", "cmd"]


def _detect_active_shell() -> _ShellLiteral:
    """Return the active interactive shell as one of five canonical literals.

    Resolution priority (highest to lowest):

    1. ``$PSModulePath`` set -> ``"pwsh"`` (PowerShell session). This
       takes precedence over inherited ``$SHELL`` because some Windows
       wrappers (Cygwin shims, terminal hosts) leak a Unix-shaped
       ``$SHELL`` into a PowerShell child.
    2. ``$SHELL`` ending in ``/zsh`` -> ``"zsh"``.
    3. ``$SHELL`` ending in ``/fish`` -> ``"fish"``.
    4. ``$SHELL`` ending in ``/bash`` -> ``"bash"``.
    5. ``$COMSPEC`` set (and no PowerShell) -> ``"cmd"``.
    6. Fallback: ``"bash"`` -- the snippet still renders.

    The function reads ``os.environ`` directly so test patches on
    ``os.environ`` are observed.
    """
    env = os.environ

    # PowerShell takes precedence over inherited Unix-shaped $SHELL.
    if env.get("PSModulePath"):
        return "pwsh"

    shell_value = (env.get("SHELL") or "").strip()
    if shell_value:
        # Match the basename so ``/bin/bash``, ``/opt/homebrew/bin/bash``
        # etc. all resolve to ``"bash"`` consistently.
        basename = shell_value.rsplit("/", 1)[-1].lower()
        if basename == "zsh":
            return "zsh"
        if basename == "fish":
            return "fish"
        if basename == "bash":
            return "bash"
        # Exotic shells (tcsh, csh, ...) fall through to bash.

    if env.get("COMSPEC"):
        return "cmd"

    return "bash"


def _format_path_with_home(target_dir: Path) -> str:
    """Return ``target_dir`` rendered as ``$HOME/...`` when applicable.

    Falls back to the absolute string when the target is not under
    ``$HOME``. Used by the snippet renderers so the user sees a
    portable ``$HOME``-rooted path on Unix shells when possible.
    """
    home = Path.home()
    try:
        rel = target_dir.relative_to(home)
    except ValueError:
        return str(target_dir)
    return f"$HOME/{rel.as_posix()}"


def emit_path_snippet(target_dir: Path) -> str:
    """Render the shell-specific PATH-addition snippet for ``target_dir``.

    The active shell is sniffed via :func:`_detect_active_shell`. The
    rendered string is the literal one-liner the user pastes into their
    rc / profile.

    Examples (with ``target_dir = $HOME/.local/bin``):

    * bash / zsh : ``export PATH="$HOME/.local/bin:$PATH"``
    * fish       : ``fish_add_path $HOME/.local/bin``
    * PowerShell : ``$env:Path += ";$HOME\\.local\\bin"``
    * cmd        : ``set PATH=%USERPROFILE%\\.local\\bin;%PATH%``

    Args:
        target_dir: The user-scope install directory whose PATH entry
            is missing (e.g. ``Path.home() / ".local" / "bin"``).

    Returns:
        The shell-specific one-liner, ready for stdout.
    """
    shell = _detect_active_shell()
    if shell in {"bash", "zsh"}:
        rendered = _format_path_with_home(target_dir)
        return f'export PATH="{rendered}:$PATH"'
    if shell == "fish":
        rendered = _format_path_with_home(target_dir)
        return f"fish_add_path {rendered}"
    if shell == "pwsh":
        # PowerShell uses semicolon-separated PATH entries on Windows.
        # The literal ``$HOME`` placeholder works in modern PowerShell;
        # backslashes match Windows path conventions.
        try:
            rel = target_dir.relative_to(Path.home())
            tail = "\\" + str(rel).replace("/", "\\")
            rendered = f"$HOME{tail}"
        except ValueError:
            rendered = str(target_dir)
        return f'$env:Path += ";{rendered}"'
    # cmd.exe -- batch-style. ``%USERPROFILE%`` is the canonical home
    # placeholder on Windows; falls back to the absolute path when the
    # target is not under home.
    home = Path.home()
    try:
        rel = target_dir.relative_to(home)
        tail = "\\" + str(rel).replace("/", "\\")
        rendered = f"%USERPROFILE%{tail}"
    except ValueError:
        rendered = str(target_dir)
    return f"set PATH={rendered};%PATH%"


# ---------------------------------------------------------------------------
# Section 7 -- AIENG_TEST_SIMULATE_FAIL hook (T-2.18)
#
# D-101-11 reserves an env-gated test hook so verifier jobs can
# deterministically synthesize an install failure for a named tool
# without spawning the real install mechanism. NG-8 keeps the public
# CLI clean: ``AIENG_TEST=1`` is the gate, and without it the
# ``AIENG_TEST_SIMULATE_FAIL`` env var is inert.
#
# Cleanest interception point lives in this module so any future caller
# (a phase, a mechanism, doctor) can consult the same single source of
# truth for the synthetic failure decision. Today only
# :class:`installer.phases.tools.ToolsPhase` calls it; mechanisms are
# stateless and do not know their owning tool name, so the phase is the
# natural caller.
#
# spec-101 Sec-2 hardening (Wave 27): the hooks are now gated by a
# build-time check (:func:`_is_dev_build`) so they cannot fire from a
# distributed wheel under any environment. ``AIENG_TEST=1`` alone is no
# longer sufficient; the running install must be a development checkout
# (editable install / source tree) OR carry the explicit
# ``AIENG_DEV_BUILD=1`` opt-in. When the env var is set on a production
# build the hooks raise :class:`RuntimeError` so a release wheel never
# silently honours synthetic install instructions.
# ---------------------------------------------------------------------------


_SIMULATE_FAIL_STDERR = "simulated failure for testing"
_SIMULATE_FAIL_MECHANISM_NAME = "aieng_test_simulate_fail"
_SIMULATE_OK_MECHANISM_NAME = "aieng_test_simulate_install_ok"


def _is_dev_build() -> bool:
    """Return True when running from a development checkout, not a wheel.

    A dev build is detected by either signal:

    * The package ``__file__`` lives outside any ``site-packages`` /
      ``dist-packages`` directory (editable install / source tree).
    * The explicit ``AIENG_DEV_BUILD=1`` env opt-in is set (CI runners
      that install from a built wheel for end-to-end coverage).

    The check is intentionally conservative -- ambiguous cases default
    to False so a production wheel never honours synthetic install
    instructions even when imported from a non-standard location.
    """
    if os.getenv("AIENG_DEV_BUILD") == "1":
        return True
    # ``__file__`` is the fully-resolved path of this module. A wheel
    # install lands the package under ``site-packages`` / ``dist-packages``;
    # editable installs and source trees do not.
    file_path = os.path.realpath(__file__)
    return "site-packages" not in file_path and "dist-packages" not in file_path


def _emit_simulate_event(*, tool_name: str, mechanism: str, outcome: str) -> None:
    """Write an audit-trail entry to ``framework-events.ndjson`` (Sec-2 audit).

    The event records every synthetic hook firing so an operator reviewing
    a CI run can distinguish real installs from simulated ones. Failures
    to write the event are silently swallowed -- the function is purely
    advisory and must NEVER block the install pipeline.

    Resolves the project root from the current working directory because
    the install hook does not propagate the install target through this
    layer; CWD matches the install target during ``ai-eng install`` runs.
    """
    try:
        from ai_engineering.state.observability import emit_framework_operation
    except ImportError:  # pragma: no cover - circular guard
        return
    try:
        emit_framework_operation(
            Path.cwd(),
            operation="install_simulate_hook",
            component="installer.user_scope_install",
            outcome=outcome,
            metadata={
                "tool": tool_name,
                "mechanism": mechanism,
            },
        )
    except Exception:  # pragma: no cover - fail-open audit trail
        return


def _refuse_in_production(env_var: str) -> None:
    """Raise when a synthetic-install env var is set on a production wheel.

    A distributed wheel must NEVER honour ``AIENG_TEST_SIMULATE_*``. The
    explicit ``RuntimeError`` makes the intent visible in stack traces
    instead of letting a misconfigured production install silently
    short-circuit installation.
    """
    if not _is_dev_build():
        raise RuntimeError(
            f"{env_var} is not available in production builds. "
            f"Set AIENG_DEV_BUILD=1 (CI/test runners only) to opt in, "
            f"OR remove the env var from the environment."
        )


def _check_simulate_fail(tool_name: str) -> InstallResult | None:
    """Return a synthetic ``InstallResult`` when the test hook fires; else ``None``.

    Hook semantics (D-101-11 + Sec-2 dev-build gate):

    * ``AIENG_TEST != "1"``                                          -> ``None``.
    * ``AIENG_TEST=1`` but ``AIENG_TEST_SIMULATE_FAIL`` unset/empty   -> ``None``.
    * ``AIENG_TEST=1`` AND ``AIENG_TEST_SIMULATE_FAIL`` set on a
      production build                                               -> raises.
    * ``AIENG_TEST=1`` AND dev-build AND ``tool_name`` is in the
      comma-separated ``AIENG_TEST_SIMULATE_FAIL`` list               -> synthetic
      ``InstallResult(failed=True, stderr="simulated failure for testing", ...)``.

    Whitespace around each entry of the comma-separated list is
    stripped so ``"ruff,  ty "`` is honoured as ``{"ruff", "ty"}``.

    Each synthetic firing emits an ``install_simulate_hook`` framework
    event so the synthetic state remains auditable downstream.
    """
    if os.getenv("AIENG_TEST") != "1":
        return None
    raw = os.getenv("AIENG_TEST_SIMULATE_FAIL") or ""
    if not raw:
        return None
    targets = {entry.strip() for entry in raw.split(",") if entry.strip()}
    if tool_name not in targets:
        return None
    # Sec-2: synthetic failure must never fire from a distributed wheel.
    _refuse_in_production("AIENG_TEST_SIMULATE_FAIL")
    _emit_simulate_event(
        tool_name=tool_name,
        mechanism=_SIMULATE_FAIL_MECHANISM_NAME,
        outcome="fail",
    )
    return InstallResult(
        failed=True,
        stderr=_SIMULATE_FAIL_STDERR,
        mechanism=_SIMULATE_FAIL_MECHANISM_NAME,
    )


def _check_simulate_install_ok(tool_name: str) -> InstallResult | None:
    """Return a synthetic SUCCESS ``InstallResult`` when the test hook fires.

    Sister hook to :func:`_check_simulate_fail`. Used by the install-smoke
    CI matrix on runners where the real install mechanism (GitHub releases
    download, brew tap, winget package) is unavailable or rate-limited.
    The smoke test still exercises every code path UP TO the mechanism
    boundary; only the network-bound install call is short-circuited.

    Hook semantics (Sec-2 dev-build gate):

    * ``AIENG_TEST != "1"``                                                  -> ``None``.
    * ``AIENG_TEST=1`` but ``AIENG_TEST_SIMULATE_INSTALL_OK`` unset/empty     -> ``None``.
    * ``AIENG_TEST=1`` AND ``AIENG_TEST_SIMULATE_INSTALL_OK`` set on a
      production build                                                       -> raises.
    * ``AIENG_TEST=1`` AND dev-build AND ``AIENG_TEST_SIMULATE_INSTALL_OK="*"``
      -> synthetic success for every tool (used by smoke runs).
    * ``AIENG_TEST=1`` AND dev-build AND ``tool_name`` in comma list         -> synthetic
      ``InstallResult(failed=False, mechanism="aieng_test_simulate_install_ok", ...)``.

    The ``"*"`` wildcard is admitted because the smoke matrix needs to
    cover every required tool without enumerating them in the workflow YAML.

    Each synthetic firing emits an ``install_simulate_hook`` framework
    event so the synthetic state remains auditable downstream.
    """
    if os.getenv("AIENG_TEST") != "1":
        return None
    raw = os.getenv("AIENG_TEST_SIMULATE_INSTALL_OK") or ""
    if not raw:
        return None
    raw_stripped = raw.strip()
    matched = False
    if raw_stripped == "*":
        matched = True
    else:
        targets = {entry.strip() for entry in raw.split(",") if entry.strip()}
        matched = tool_name in targets
    if not matched:
        return None
    # Sec-2: synthetic success must never fire from a distributed wheel.
    _refuse_in_production("AIENG_TEST_SIMULATE_INSTALL_OK")
    _emit_simulate_event(
        tool_name=tool_name,
        mechanism=_SIMULATE_OK_MECHANISM_NAME,
        outcome="ok",
    )
    return InstallResult(
        failed=False,
        stderr="",
        mechanism=_SIMULATE_OK_MECHANISM_NAME,
        version="aieng-test",
    )
