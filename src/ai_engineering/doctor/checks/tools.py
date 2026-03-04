"""Tool availability diagnostic checks.

Delegates detection and installation to :mod:`ai_engineering.detector.readiness`
so that tool-availability logic is not duplicated.
"""

from __future__ import annotations

from ai_engineering.detector.readiness import is_tool_available, try_install
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport

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
            success = try_install(tool)
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
