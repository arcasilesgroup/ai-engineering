"""Doctor runtime check: vcs-auth -- validates VCS authentication.

Runs ``gh auth status`` (GitHub) or ``az account show`` (Azure DevOps)
to verify the current user has valid credentials. This is a runtime
check because it requires network/credential access that the install
pipeline does not own.
"""

from __future__ import annotations

import subprocess

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Check VCS authentication status."""
    if ctx.install_state is None:
        return [
            CheckResult(
                name="vcs-auth",
                status=CheckStatus.OK,
                message="skipped (no install state)",
            )
        ]

    vcs_provider = getattr(ctx.install_state, "vcs_provider", None) or "github"

    if vcs_provider == "azure_devops":
        return [_check_azure_auth()]

    return [_check_github_auth()]


def _check_github_auth() -> CheckResult:
    """Run ``gh auth status`` and map exit code to CheckResult."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return CheckResult(
            name="vcs-auth",
            status=CheckStatus.WARN,
            message="gh CLI not found; install GitHub CLI to verify auth",
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return CheckResult(
            name="vcs-auth",
            status=CheckStatus.WARN,
            message=f"gh auth status failed: {exc}",
        )

    if result.returncode == 0:
        return CheckResult(
            name="vcs-auth",
            status=CheckStatus.OK,
            message="GitHub authentication valid",
        )
    return CheckResult(
        name="vcs-auth",
        status=CheckStatus.WARN,
        message="GitHub authentication not configured; run 'gh auth login'",
    )


def _check_azure_auth() -> CheckResult:
    """Run ``az account show`` and map exit code to CheckResult."""
    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return CheckResult(
            name="vcs-auth",
            status=CheckStatus.WARN,
            message="az CLI not found; install Azure CLI to verify auth",
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return CheckResult(
            name="vcs-auth",
            status=CheckStatus.WARN,
            message=f"az account show failed: {exc}",
        )

    if result.returncode == 0:
        return CheckResult(
            name="vcs-auth",
            status=CheckStatus.OK,
            message="Azure DevOps authentication valid",
        )
    return CheckResult(
        name="vcs-auth",
        status=CheckStatus.WARN,
        message="Azure authentication not configured; run 'az login'",
    )
