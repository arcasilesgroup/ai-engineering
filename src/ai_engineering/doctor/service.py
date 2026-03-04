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

import shutil  # noqa: F401 — re-exported for test patching
import subprocess  # noqa: F401 — re-exported for test patching
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class CheckStatus(StrEnum):
    """Status of a single diagnostic check."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    FIXED = "fixed"


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    status: CheckStatus
    message: str


@dataclass
class DoctorReport:
    """Aggregated report from all diagnostic checks."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no checks failed."""
        return all(c.status != CheckStatus.FAIL for c in self.checks)

    @property
    def summary(self) -> dict[str, int]:
        """Count of checks by status."""
        counts: dict[str, int] = {}
        for check in self.checks:
            counts[check.status.value] = counts.get(check.status.value, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        """Serialize report for JSON output."""
        return {
            "passed": self.passed,
            "summary": self.summary,
            "checks": [
                {"name": c.name, "status": c.status.value, "message": c.message}
                for c in self.checks
            ],
        }


def diagnose(
    target: Path,
    *,
    fix_hooks: bool = False,
    fix_tools: bool = False,
) -> DoctorReport:
    """Run all diagnostic checks on a target project.

    Args:
        target: Root directory of the target project.
        fix_hooks: If True, attempt to reinstall hooks on failure.
        fix_tools: If True, attempt to install missing tools via pip/uv.

    Returns:
        DoctorReport with all check results.
    """
    report = DoctorReport()

    _check_layout(target, report)
    _check_state_files(target, report)
    _check_hooks(target, report, fix=fix_hooks)
    _check_venv_health(target, report, fix=fix_tools)
    _check_tools(report, fix=fix_tools)
    _check_vcs_tools(report)
    _check_branch_policy(target, report)
    _check_operational_readiness(target, report)
    _check_version(report)

    return report


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


# ---------------------------------------------------------------------------
# Backward-compatible re-exports for tests and consumers.
# ---------------------------------------------------------------------------

# Constants
_REQUIRED_DIRS = [
    "standards",
    "standards/framework",
    "context",
    "state",
]
_REQUIRED_STATE_FILES = [
    "state/install-manifest.json",
    "state/ownership-map.json",
    "state/decision-store.json",
    "state/sources.lock.json",
]
_TOOLS = ["ruff", "ty", "gitleaks", "semgrep", "pip-audit"]
_VCS_TOOLS = ["gh", "az"]
_PROTECTED_BRANCHES = frozenset({"main", "master"})


def _check_layout(target: Path, report: DoctorReport) -> None:
    from ai_engineering.doctor.checks.layout import check_layout

    check_layout(target, report)


def _check_state_files(target: Path, report: DoctorReport) -> None:
    from ai_engineering.doctor.checks.state_files import check_state_files

    check_state_files(target, report)


def _check_hooks(target: Path, report: DoctorReport, *, fix: bool) -> None:
    from ai_engineering.doctor.checks.hooks import check_hooks

    check_hooks(target, report, fix=fix)


def _check_venv_health(target: Path, report: DoctorReport, *, fix: bool) -> None:
    from ai_engineering.doctor.checks.venv import check_venv_health

    check_venv_health(target, report, fix=fix)


def _check_tools(report: DoctorReport, *, fix: bool) -> None:
    from ai_engineering.doctor.checks.tools import check_tools

    check_tools(report, fix=fix)


def _check_vcs_tools(report: DoctorReport) -> None:
    from ai_engineering.doctor.checks.tools import check_vcs_tools

    check_vcs_tools(report)


def _check_branch_policy(target: Path, report: DoctorReport) -> None:
    from ai_engineering.doctor.checks.branch_policy import check_branch_policy

    check_branch_policy(target, report)


def _check_operational_readiness(target: Path, report: DoctorReport) -> None:
    from ai_engineering.doctor.checks.readiness import check_operational_readiness

    check_operational_readiness(target, report)


def _check_version(report: DoctorReport) -> None:
    from ai_engineering.doctor.checks.version_check import check_version

    check_version(report)


def _is_tool_available(tool: str) -> bool:
    from ai_engineering.doctor.checks.tools import is_tool_available

    return is_tool_available(tool)


def _try_install_tool(tool: str) -> bool:
    from ai_engineering.doctor.checks.tools import try_install_tool

    return try_install_tool(tool)


def _get_current_branch(target: Path) -> str | None:
    from ai_engineering.doctor.checks.branch_policy import get_current_branch

    return get_current_branch(target)


def _parse_pyvenv_home(cfg_path: Path) -> str | None:
    from ai_engineering.doctor.checks.venv import parse_pyvenv_home

    return parse_pyvenv_home(cfg_path)


def _recreate_venv(target: Path) -> bool:
    from ai_engineering.doctor.checks.venv import recreate_venv

    return recreate_venv(target)
