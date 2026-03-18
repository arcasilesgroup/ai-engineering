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


def ensure_tool(tool: str, *, allow_install: bool | None = None) -> ToolInstallResult:
    """Ensure a tool is available, attempting OS-specific install if missing."""
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

    if system == "darwin" and shutil.which("brew"):
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

    if cmd is None:
        return ToolInstallResult(
            tool=tool,
            available=False,
            attempted=False,
            installed=False,
            detail="No supported package manager available",
        )

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return ToolInstallResult(
            tool=tool,
            available=False,
            attempted=True,
            installed=False,
            method=method,
            detail=str(exc),
        )

    available = shutil.which(tool) is not None
    return ToolInstallResult(
        tool=tool,
        available=available,
        attempted=True,
        installed=available,
        method=method,
        detail="installed" if available else "install command completed but tool not found",
    )


def provider_required_tools(provider: str) -> list[str]:
    """Return provider-aware required VCS CLI tools."""
    return ["gh"] if provider == "github" else ["az"]
