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
    cmd: list[str] | None = None
    method = ""

    if system in ("darwin", "linux") and shutil.which("brew"):
        cmd = ["brew", "install", tool]
        method = "brew"
    elif system == "linux" and shutil.which("apt-get"):
        cmd = ["apt-get", "install", "-y", tool]
        method = "apt"
    elif system == "windows" and shutil.which("winget"):
        winget_id = _WINGET_IDS.get(tool)
        if winget_id:
            cmd = ["winget", "install", "-e", "--id", winget_id]
            method = "winget"

    if cmd is not None:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            # OS install failed — fall through to pip fallback
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
