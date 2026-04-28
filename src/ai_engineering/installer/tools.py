"""OS-aware installer helpers for required CLI/system tools."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class ToolInstallResult:
    """Outcome for one tool installation attempt."""

    tool: str
    available: bool
    attempted: bool
    installed: bool
    method: str = "none"
    detail: str = ""


@dataclass(frozen=True)
class ToolCapability:
    """Auto-install support for a tool on the current platform."""

    tool: str
    automatic_supported: bool
    reason: str = ""


_WINGET_IDS: dict[str, str] = {
    "gh": "GitHub.cli",
    "az": "Microsoft.AzureCLI",
    "gitleaks": "Gitleaks.Gitleaks",
    "semgrep": "Semgrep.Semgrep",
}

_VCS_PROVIDER_TOOLS: dict[str, list[str]] = {
    "github": ["gh"],
    "azure_devops": ["az"],
}

# Python tools that can be installed via pip/uv when OS package manager
# has no mapping (e.g., ruff on Windows where winget has no ruff package).
_PIP_INSTALLABLE: dict[str, str] = {
    "ruff": "ruff",
    "ty": "ty",
    "pip-audit": "pip-audit",
}


def get_tool_capability(tool: str, *, system: str | None = None) -> ToolCapability:
    """Return whether the framework can auto-install a tool on this platform."""
    normalized_system = (system or platform.system()).lower()

    if normalized_system == "windows" and tool == "semgrep":
        return ToolCapability(
            tool=tool,
            automatic_supported=False,
            reason="Automatic Semgrep installation is not supported on Windows.",
        )

    if tool in _PIP_INSTALLABLE:
        return ToolCapability(tool=tool, automatic_supported=True, reason="pip-installable")

    if normalized_system in ("darwin", "linux"):
        return ToolCapability(tool=tool, automatic_supported=True, reason="os-package-manager")

    if normalized_system == "windows" and tool in _WINGET_IDS:
        return ToolCapability(tool=tool, automatic_supported=True, reason="winget")

    return ToolCapability(
        tool=tool,
        automatic_supported=False,
        reason="No supported package manager available.",
    )


def can_auto_install_tool(tool: str, *, system: str | None = None) -> bool:
    """Return True when the framework can attempt automatic installation."""
    return get_tool_capability(tool, system=system).automatic_supported


def manual_install_step(tool: str, *, system: str | None = None) -> str:
    """Return user-facing manual guidance for a missing tool."""
    capability = get_tool_capability(tool, system=system)
    if capability.reason:
        return f"Install `{tool}` manually. {capability.reason}"
    return f"Install `{tool}` manually."


def ensure_tool(tool: str, *, allow_install: bool | None = None) -> ToolInstallResult:
    """Ensure a tool is available, attempting OS-specific install if missing.

    Install strategy (in order):
    1. OS package manager (brew / apt-get / winget)
    2. pip/uv fallback for Python-installable tools (_PIP_INSTALLABLE)
    """
    if shutil.which(tool):
        return ToolInstallResult(tool=tool, available=True, attempted=False, installed=False)

    if allow_install is None:
        allow_install = os.getenv("AI_ENG_AUTO_INSTALL_TOOLS", "0") == "1"
    if not allow_install:
        return ToolInstallResult(
            tool=tool,
            available=False,
            attempted=False,
            installed=False,
            detail="Auto-install disabled; set AI_ENG_AUTO_INSTALL_TOOLS=1 to enable",
        )

    system = platform.system().lower()
    capability = get_tool_capability(tool, system=system)
    if not capability.automatic_supported:
        return ToolInstallResult(
            tool=tool,
            available=False,
            attempted=False,
            installed=False,
            detail=manual_install_step(tool, system=system),
        )

    cmd: list[str] | None = None
    method = ""

    # spec-101 Corr-3 (Wave 27): apt-get is intentionally NOT consulted.
    # The framework's user-scope-only invariant (D-101-02) forbids any
    # privileged package manager from running during install. The legacy
    # apt-get path was removed; tools that historically went through apt
    # must come from one of the user-scope mechanisms (brew, winget, or
    # the pip fallback below). This module is itself slated for retirement
    # in favour of :mod:`installer.tool_registry` (TODO(spec-102): remove
    # this entire helper once the new registry covers the VCS tool set).
    if system in ("darwin", "linux") and shutil.which("brew"):
        cmd = ["brew", "install", tool]
        method = "brew"
    elif system == "windows" and shutil.which("winget"):
        winget_id = _WINGET_IDS.get(tool)
        if winget_id:
            cmd = ["winget", "install", "-e", "--id", winget_id]
            method = "winget"

    if cmd is not None:
        try:
            # Route through ``_safe_run`` so the user-scope guard validates
            # argv[0] BEFORE exec. brew / winget are both in
            # :data:`installer.user_scope_install.DRIVER_BINARIES` so the
            # call passes the allowlist; any future addition that is not
            # in the allowlist will surface :class:`UserScopeViolation`
            # instead of the silent privileged escape we just removed.
            from ai_engineering.installer.user_scope_install import (
                MissingDriverError,
                UserScopeViolation,
                _safe_run,
            )

            try:
                _safe_run(cmd, check=True, timeout=180)
            except UserScopeViolation as scope_exc:
                # The argv resolved outside the user-scope allowlist. Fall
                # through to the pip fallback if applicable; otherwise
                # surface a clear error.
                if tool not in _PIP_INSTALLABLE:
                    return ToolInstallResult(
                        tool=tool,
                        available=False,
                        attempted=True,
                        installed=False,
                        method=method,
                        detail=f"user-scope violation: {scope_exc}",
                    )
            except MissingDriverError as drv_exc:
                if tool not in _PIP_INSTALLABLE:
                    return ToolInstallResult(
                        tool=tool,
                        available=False,
                        attempted=True,
                        installed=False,
                        method=method,
                        detail=str(drv_exc),
                    )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            # OS install failed -- fall through to pip fallback
            if tool not in _PIP_INSTALLABLE:
                return ToolInstallResult(
                    tool=tool,
                    available=False,
                    attempted=True,
                    installed=False,
                    method=method,
                    detail=str(exc),
                )

        available = shutil.which(tool) is not None
        if available:
            return ToolInstallResult(
                tool=tool,
                available=True,
                attempted=True,
                installed=True,
                method=method,
                detail="installed",
            )

    # Fallback: pip/uv install for Python-installable tools
    package = _PIP_INSTALLABLE.get(tool)
    if package is None:
        return ToolInstallResult(
            tool=tool,
            available=False,
            attempted=bool(cmd),
            installed=False,
            detail="No supported package manager available",
        )

    pip_result = _try_pip_install(package)
    available = shutil.which(tool) is not None
    return ToolInstallResult(
        tool=tool,
        available=available,
        attempted=True,
        installed=available,
        method="pip",
        detail="installed via pip" if available else pip_result,
    )


def _try_pip_install(package: str) -> str:
    """Attempt pip/uv install, return error detail on failure."""
    if shutil.which("uv"):
        try:
            subprocess.run(
                ["uv", "pip", "install", package],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return "installed"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            uv_err = str(exc)
    else:
        uv_err = "uv not available"

    try:
        subprocess.run(
            ["pip", "install", package],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return "installed"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return f"pip fallback failed: uv: {uv_err}, pip: {exc}"


def provider_required_tools(provider: str) -> list[str]:
    """Return provider-aware required VCS CLI tools."""
    normalized = provider.replace("-", "_").lower()
    return list(_VCS_PROVIDER_TOOLS.get(normalized, []))
