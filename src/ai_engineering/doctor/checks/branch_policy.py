"""Branch policy diagnostic check."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport

_PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master"})


def check_branch_policy(target: Path, report: DoctorReport) -> None:
    """Check that the current branch is not a protected branch."""
    branch = get_current_branch(target)
    if branch is None:
        report.checks.append(
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message="Could not determine current branch",
            )
        )
        return

    if branch in _PROTECTED_BRANCHES:
        report.checks.append(
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message=f"On protected branch: {branch}",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="branch-policy",
                status=CheckStatus.OK,
                message=f"On branch: {branch}",
            )
        )


def get_current_branch(target: Path) -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=target,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
