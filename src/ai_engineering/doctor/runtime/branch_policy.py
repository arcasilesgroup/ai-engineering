"""Doctor runtime check: branch-policy -- warns when on a protected branch.

A simple guard that alerts the developer if they are currently on ``main``
or ``master``.  This is informational only (WARN, not FAIL) because some
workflows legitimately operate on protected branches.
"""

from __future__ import annotations

import subprocess

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext

_PROTECTED_BRANCHES = frozenset({"main", "master"})


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Check whether the working tree is on a protected branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=ctx.target,
            timeout=5,
        )
    except (FileNotFoundError, OSError):
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message="not a git repository",
            )
        ]

    if result.returncode != 0:
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message="not a git repository",
            )
        ]

    branch = result.stdout.strip()
    if branch in _PROTECTED_BRANCHES:
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message=f"on protected branch '{branch}'; create a feature branch",
            )
        ]

    return [
        CheckResult(
            name="branch-policy",
            status=CheckStatus.OK,
            message=f"on branch '{branch}'",
        )
    ]
