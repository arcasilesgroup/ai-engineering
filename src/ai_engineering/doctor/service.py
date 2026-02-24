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

import shutil
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from ai_engineering.hooks.manager import install_hooks, verify_hooks
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import InstallManifest, OwnershipMap


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


# Required directories under .ai-engineering/
_REQUIRED_DIRS: list[str] = [
    "standards",
    "standards/framework",
    "context",
    "state",
]

# Required state files
_REQUIRED_STATE_FILES: list[str] = [
    "state/install-manifest.json",
    "state/ownership-map.json",
    "state/decision-store.json",
    "state/sources.lock.json",
]

# Tools to check availability for
_TOOLS: list[str] = ["ruff", "ty", "gitleaks", "semgrep", "pip-audit"]
_VCS_TOOLS: list[str] = ["gh", "az"]

# Protected branch names
_PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master"})


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


def _check_layout(target: Path, report: DoctorReport) -> None:
    """Check that required framework directories exist."""
    ai_eng = target / ".ai-engineering"

    if not ai_eng.is_dir():
        report.checks.append(
            CheckResult(
                name="framework-layout",
                status=CheckStatus.FAIL,
                message=".ai-engineering/ directory not found",
            )
        )
        return

    missing: list[str] = []
    for d in _REQUIRED_DIRS:
        if not (ai_eng / d).is_dir():
            missing.append(d)

    if missing:
        report.checks.append(
            CheckResult(
                name="framework-layout",
                status=CheckStatus.FAIL,
                message=f"Missing directories: {', '.join(missing)}",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="framework-layout",
                status=CheckStatus.OK,
                message="All required directories present",
            )
        )


def _check_state_files(target: Path, report: DoctorReport) -> None:
    """Check that state files exist and are parseable."""
    ai_eng = target / ".ai-engineering"

    for relative in _REQUIRED_STATE_FILES:
        path = ai_eng / relative
        name = f"state:{Path(relative).name}"

        if not path.is_file():
            report.checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    message=f"Missing: {relative}",
                )
            )
            continue

        try:
            if "install-manifest" in relative:
                read_json_model(path, InstallManifest)
            elif "ownership-map" in relative:
                read_json_model(path, OwnershipMap)
            else:
                # For decision-store and sources.lock, just verify valid JSON
                import json

                json.loads(path.read_text(encoding="utf-8"))

            report.checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.OK,
                    message=f"Valid: {relative}",
                )
            )
        except Exception as exc:
            report.checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    message=f"Invalid {relative}: {exc}",
                )
            )


def _check_hooks(target: Path, report: DoctorReport, *, fix: bool) -> None:
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


def _check_venv_health(target: Path, report: DoctorReport, *, fix: bool) -> None:
    """Check that the project venv exists and points to a valid Python path.

    Parses ``.venv/pyvenv.cfg`` and verifies the ``home`` path exists on disk.
    When ``fix=True`` and the venv is stale, recreates it via ``uv venv``.
    """
    venv_dir = target / ".venv"
    cfg_path = venv_dir / "pyvenv.cfg"

    if not venv_dir.is_dir():
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="No .venv directory found",
            )
        )
        return

    if not cfg_path.is_file():
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="No .venv/pyvenv.cfg found",
            )
        )
        return

    # Parse home path from pyvenv.cfg
    home_path = _parse_pyvenv_home(cfg_path)
    if home_path is None:
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="Could not parse home from pyvenv.cfg",
            )
        )
        return

    if Path(home_path).is_dir():
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.OK,
                message=f"Venv home valid: {home_path}",
            )
        )
        return

    # Stale venv detected
    if fix:
        success = _recreate_venv(target)
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.FIXED if success else CheckStatus.FAIL,
                message="Venv recreated" if success else "Venv recreation failed",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.FAIL,
                message=(
                    f"Stale venv — home path does not exist: {home_path}. "
                    "Run 'ai-eng doctor --fix-tools' to recreate."
                ),
            )
        )


def _parse_pyvenv_home(cfg_path: Path) -> str | None:
    """Extract the ``home`` value from a pyvenv.cfg file.

    Args:
        cfg_path: Path to the pyvenv.cfg file.

    Returns:
        The home directory path string, or None if not found.
    """
    try:
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("home"):
                _, _, value = line.partition("=")
                return value.strip()
    except OSError:
        pass
    return None


def _recreate_venv(target: Path) -> bool:
    """Recreate the project venv using ``uv venv``.

    Reads ``.python-version`` if present to determine the Python version,
    otherwise defaults to the system Python.

    Args:
        target: Root directory of the project.

    Returns:
        True if recreation succeeded.
    """
    cmd: list[str] = ["uv", "venv"]

    # Use .python-version pin if available
    pin_file = target / ".python-version"
    if pin_file.is_file():
        version = pin_file.read_text(encoding="utf-8").strip()
        if version:
            cmd.extend(["--python", version])

    cmd.append(str(target / ".venv"))

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=60,
            cwd=target,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _check_tools(report: DoctorReport, *, fix: bool) -> None:
    """Check that required development tools are available on PATH."""
    for tool in _TOOLS:
        if _is_tool_available(tool):
            report.checks.append(
                CheckResult(
                    name=f"tool:{tool}",
                    status=CheckStatus.OK,
                    message=f"{tool} found",
                )
            )
        elif fix:
            success = _try_install_tool(tool)
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


def _check_vcs_tools(report: DoctorReport) -> None:
    """Check VCS provider tools (gh, az) availability."""
    for tool in _VCS_TOOLS:
        if _is_tool_available(tool):
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


def _check_branch_policy(target: Path, report: DoctorReport) -> None:
    """Check that the current branch is not a protected branch."""
    branch = _get_current_branch(target)
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


def _check_version(report: DoctorReport) -> None:
    """Check the version lifecycle status of the installed framework.

    Reports OK for current, WARN for outdated/supported, FAIL for deprecated/eol.
    Fail-open: registry errors produce a WARN, not a FAIL.
    """
    from ai_engineering.__version__ import __version__
    from ai_engineering.version.checker import check_version

    result = check_version(__version__)

    if result.status is None:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.WARN,
                message=result.message,
            )
        )
    elif result.is_current:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.OK,
                message=result.message,
            )
        )
    elif result.is_deprecated or result.is_eol:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.FAIL,
                message=result.message,
            )
        )
    else:
        # Outdated or supported — warning only
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.WARN,
                message=result.message,
            )
        )


def _check_operational_readiness(target: Path, report: DoctorReport) -> None:
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


def _is_tool_available(tool: str) -> bool:
    """Check if a tool is available on PATH."""
    return shutil.which(tool) is not None


def _try_install_tool(tool: str) -> bool:
    """Attempt to install a missing Python tool via uv or pip.

    Args:
        tool: Tool name to install.

    Returns:
        True if installation succeeded.
    """
    # Try uv first, then pip
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


def _get_current_branch(target: Path) -> str | None:
    """Get the current git branch name.

    Args:
        target: Root directory of the git repository.

    Returns:
        Branch name or None if not determinable.
    """
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
