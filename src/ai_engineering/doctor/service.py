"""Diagnostic and remediation service for ai-engineering installations.

Validates:
- Framework layout (required directories and files).
- State file integrity (parseable JSON matching expected schemas).
- Git hooks installation and integrity.
- Venv health (pyvenv.cfg home path validity).
- Tool availability (ruff, ty, gitleaks, semgrep, pip-audit, gh, az).
- Branch policy (not on protected branch).

Supports ``--fix-hooks`` and ``--fix-tools`` remediation modes.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport

__all__ = ["CheckResult", "CheckStatus", "DoctorReport"]


def check_platforms(target: Path, report: DoctorReport) -> None:
    """Validate stored platform credentials are still valid."""
    from ai_engineering.credentials.service import CredentialService

    state_dir = target / ".ai-engineering" / "state"
    cred_svc = CredentialService()
    state = cred_svc.load_tools_state(state_dir)

    # GitHub check
    if state.github.configured:
        from ai_engineering.platforms.github import GitHubSetup

        gh_status = GitHubSetup.check_auth_status()
        if gh_status.authenticated:
            report.checks.append(
                CheckResult(
                    name="platform:github",
                    status=CheckStatus.OK,
                    message=f"Authenticated as {gh_status.username}",
                )
            )
        else:
            report.checks.append(
                CheckResult(
                    name="platform:github",
                    status=CheckStatus.FAIL,
                    message=f"GitHub auth failed: {gh_status.error}",
                )
            )
    else:
        report.checks.append(
            CheckResult(
                name="platform:github",
                status=CheckStatus.WARN,
                message="GitHub not configured",
            )
        )

    # Sonar check
    if state.sonar.configured and state.sonar.url:
        from ai_engineering.platforms.sonar import SonarSetup

        sonar = SonarSetup(cred_svc)
        token = sonar.retrieve_token()
        if token:
            result = sonar.validate_token(state.sonar.url, token)
            if result.valid:
                report.checks.append(
                    CheckResult(
                        name="platform:sonar",
                        status=CheckStatus.OK,
                        message=f"Token valid for {state.sonar.url}",
                    )
                )
            else:
                report.checks.append(
                    CheckResult(
                        name="platform:sonar",
                        status=CheckStatus.FAIL,
                        message=f"Token invalid: {result.error}",
                    )
                )
        else:
            report.checks.append(
                CheckResult(
                    name="platform:sonar",
                    status=CheckStatus.FAIL,
                    message="Token missing from keyring",
                )
            )
    else:
        report.checks.append(
            CheckResult(
                name="platform:sonar",
                status=CheckStatus.WARN,
                message="Sonar not configured",
            )
        )

    # Azure DevOps check
    if state.azure_devops.configured and state.azure_devops.org_url:
        from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

        azdo = AzureDevOpsSetup(cred_svc)
        pat = azdo.retrieve_pat()
        if pat:
            result = azdo.validate_pat(state.azure_devops.org_url, pat)
            if result.valid:
                report.checks.append(
                    CheckResult(
                        name="platform:azure_devops",
                        status=CheckStatus.OK,
                        message=f"PAT valid for {state.azure_devops.org_url}",
                    )
                )
            else:
                report.checks.append(
                    CheckResult(
                        name="platform:azure_devops",
                        status=CheckStatus.FAIL,
                        message=f"PAT invalid: {result.error}",
                    )
                )
        else:
            report.checks.append(
                CheckResult(
                    name="platform:azure_devops",
                    status=CheckStatus.FAIL,
                    message="PAT missing from keyring",
                )
            )
    else:
        report.checks.append(
            CheckResult(
                name="platform:azure_devops",
                status=CheckStatus.WARN,
                message="Azure DevOps not configured",
            )
        )


def diagnose(
    target: Path,
    *,
    fix_hooks: bool = False,
    fix_tools: bool = False,
    include_platforms: bool = False,
) -> DoctorReport:
    """Run all diagnostic checks on a target project.

    Args:
        target: Root directory of the target project.
        fix_hooks: If True, attempt to reinstall hooks on failure.
        fix_tools: If True, attempt to install missing tools via pip/uv.
        include_platforms: If True, validate stored platform credentials.

    Returns:
        DoctorReport with all check results.
    """
    from ai_engineering.doctor.checks.branch_policy import check_branch_policy
    from ai_engineering.doctor.checks.hooks import check_hooks
    from ai_engineering.doctor.checks.layout import check_layout
    from ai_engineering.doctor.checks.readiness import check_operational_readiness
    from ai_engineering.doctor.checks.state_files import check_state_files
    from ai_engineering.doctor.checks.tools import check_tools, check_vcs_tools
    from ai_engineering.doctor.checks.venv import check_venv_health
    from ai_engineering.doctor.checks.version_check import check_version

    report = DoctorReport()

    check_layout(target, report)
    check_state_files(target, report)
    check_hooks(target, report, fix=fix_hooks)
    check_venv_health(target, report, fix=fix_tools)
    check_tools(report, fix=fix_tools)
    check_vcs_tools(report)
    check_branch_policy(target, report)
    check_operational_readiness(target, report)
    check_version(report)

    if include_platforms:
        check_platforms(target, report)

    return report
