"""Operational readiness diagnostic check."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor.service import CheckResult, CheckStatus, DoctorReport
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import InstallManifest


def check_operational_readiness(target: Path, report: DoctorReport) -> None:
    """Check install-to-operational status from install manifest."""
    manifest_path = target / ".ai-engineering" / "state" / "install-manifest.json"
    if not manifest_path.is_file():
        return
    try:
        manifest = read_json_model(manifest_path, InstallManifest)
    except Exception as exc:  # pragma: no cover
        report.checks.append(
            CheckResult(
                name="operational-readiness",
                status=CheckStatus.FAIL,
                message=f"Cannot read install manifest: {exc}",
            )
        )
        return

    status = manifest.operational_readiness.status
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
