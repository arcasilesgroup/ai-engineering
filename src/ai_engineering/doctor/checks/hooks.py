"""Git hooks diagnostic check."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport
from ai_engineering.hooks.manager import install_hooks, verify_hooks


def check_hooks(target: Path, report: DoctorReport, *, fix: bool) -> None:
    """Check git hooks installation and integrity."""
    git_dir = target / ".git"
    if not git_dir.is_dir():
        report.checks.append(
            CheckResult(
                name="git-hooks",
                status=CheckStatus.WARN,
                message="Not a git repository — hooks check skipped",
            )
        )
        return

    status = verify_hooks(target)
    all_valid = all(status.values())

    if all_valid:
        report.checks.append(
            CheckResult(
                name="git-hooks",
                status=CheckStatus.OK,
                message="All hooks installed and verified",
            )
        )
        return

    missing = [name for name, valid in status.items() if not valid]

    if fix:
        install_hooks(target, force=True)
        report.checks.append(
            CheckResult(
                name="git-hooks",
                status=CheckStatus.FIXED,
                message=f"Reinstalled hooks: {', '.join(missing)}",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="git-hooks",
                status=CheckStatus.FAIL,
                message=f"Missing or invalid hooks: {', '.join(missing)}",
            )
        )
