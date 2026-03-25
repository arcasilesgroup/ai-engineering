"""Operational readiness diagnostic check."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport
from ai_engineering.state.service import load_install_state


def check_operational_readiness(target: Path, report: DoctorReport) -> None:
    """Check install-to-operational status from install state."""
    state_path = target / ".ai-engineering" / "state" / "install-state.json"
    if not state_path.is_file():
        return
    try:
        state = load_install_state(target / ".ai-engineering" / "state")
    except Exception as exc:
        report.checks.append(
            CheckResult(
                name="operational-readiness",
                status=CheckStatus.FAIL,
                message=f"Cannot read install state: {exc}",
            )
        )
        return

    status = state.operational_readiness.status
    if status == "READY":
        report.checks.append(
            CheckResult(
                name="operational-readiness",
                status=CheckStatus.OK,
                message="Install-to-operational checks passed",
            )
        )
        return

    if status == "READY WITH MANUAL STEPS":
        report.checks.append(
            CheckResult(
                name="operational-readiness",
                status=CheckStatus.WARN,
                message="Manual setup steps required for full CI/CD governance",
            )
        )
        return

    report.checks.append(
        CheckResult(
            name="operational-readiness",
            status=CheckStatus.FAIL,
            message=f"Operational readiness status: {status}",
        )
    )
