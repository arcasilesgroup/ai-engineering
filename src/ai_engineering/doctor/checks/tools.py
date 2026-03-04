"""Tool availability diagnostic checks."""

from __future__ import annotations

import shutil
import subprocess

from ai_engineering.doctor.service import CheckResult, CheckStatus, DoctorReport

_TOOLS: list[str] = ["ruff", "ty", "gitleaks", "semgrep", "pip-audit"]
_VCS_TOOLS: list[str] = ["gh", "az"]


def check_tools(report: DoctorReport, *, fix: bool) -> None:
    """Check that required development tools are available on PATH."""
    for tool in _TOOLS:
        if is_tool_available(tool):
            report.checks.append(
                CheckResult(
                    name=f"tool:{tool}",
                    status=CheckStatus.OK,
                    message=f"{tool} found",
                )
            )
        elif fix:
            success = try_install_tool(tool)
            report.checks.append(
                CheckResult(
                    name=f"tool:{tool}",
                    status=CheckStatus.FIXED if success else CheckStatus.FAIL,
                    message=f"{tool} {'installed' if success else 'install failed'}",
                )
            )
        else:
            report.checks.append(
                CheckResult(
                    name=f"tool:{tool}",
                    status=CheckStatus.WARN,
                    message=f"{tool} not found",
                )
            )


def check_vcs_tools(report: DoctorReport) -> None:
    """Check VCS provider tools (gh, az) availability."""
    for tool in _VCS_TOOLS:
        if is_tool_available(tool):
            report.checks.append(
                CheckResult(
                    name=f"tool:{tool}",
                    status=CheckStatus.OK,
                    message=f"{tool} found",
                )
            )
        else:
            report.checks.append(
                CheckResult(
                    name=f"tool:{tool}",
                    status=CheckStatus.WARN,
                    message=f"{tool} not found (optional)",
                )
            )


def is_tool_available(tool: str) -> bool:
    """Check if a tool is available on PATH."""
    return shutil.which(tool) is not None


def try_install_tool(tool: str) -> bool:
    """Attempt to install a missing Python tool via uv or pip."""
    for installer in ["uv pip install", "pip install"]:
        try:
            subprocess.run(
                [*installer.split(), tool],
                check=True,
                capture_output=True,
                timeout=60,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False
