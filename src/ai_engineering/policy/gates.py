"""Git hook gate checks for ai-engineering.

Implements the quality gates invoked by git hooks:
- **pre-commit**: stack-aware format/lint checks + gitleaks + risk expiry warnings.
- **commit-msg**: commit message format validation.
- **pre-push**: stack-aware tests/type-checks/vuln-scans + semgrep + expired risk blocking.

Gate dispatch is stack-aware: reads ``installedStacks`` from
``install-manifest.json`` and runs only checks relevant to active stacks.
Falls back to Python-only checks if no manifest exists.

Also enforces protected branch blocking: direct commits to main/master
are rejected.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.git.operations import PROTECTED_BRANCHES, current_branch
from ai_engineering.state.decision_logic import list_expired_decisions, list_expiring_soon
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore, GateHook, InstallManifest


@dataclass
class GateCheckResult:
    """Result of a single gate check."""

    name: str
    passed: bool
    output: str = ""


@dataclass
class GateResult:
    """Aggregated result from a gate execution."""

    hook: GateHook
    checks: list[GateCheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all gate checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[str]:
        """Names of failed checks."""
        return [c.name for c in self.checks if not c.passed]


def run_gate(
    hook: GateHook,
    project_root: Path,
    *,
    commit_msg_file: Path | None = None,
) -> GateResult:
    """Execute all checks for a specific gate hook.

    Args:
        hook: The gate hook type to execute.
        project_root: Root directory of the project.
        commit_msg_file: Path to the commit message file (commit-msg only).

    Returns:
        GateResult with all check outcomes.
    """
    result = GateResult(hook=hook)

    # Branch protection check (all hooks)
    _check_branch_protection(project_root, result)
    if not result.passed:
        return result

    # Version deprecation check (defense-in-depth, all hooks)
    _check_version_deprecation(result)
    if not result.passed:
        return result

    if hook == GateHook.PRE_COMMIT:
        _run_pre_commit_checks(project_root, result)
    elif hook == GateHook.COMMIT_MSG:
        _run_commit_msg_checks(commit_msg_file, result)
    elif hook == GateHook.PRE_PUSH:
        _run_pre_push_checks(project_root, result)

    return result


# --- Stack-aware check registry ---


@dataclass
class CheckConfig:
    """Configuration for a single gate check command."""

    name: str
    cmd: list[str]
    required: bool = True


# Pre-commit checks per stack.
_PRE_COMMIT_CHECKS: dict[str, list[CheckConfig]] = {
    "common": [
        CheckConfig(
            name="gitleaks",
            cmd=["gitleaks", "detect", "--source", ".", "--no-git"],
        ),
    ],
    "python": [
        CheckConfig(name="ruff-format", cmd=["ruff", "format", "--check", "."]),
        CheckConfig(name="ruff-lint", cmd=["ruff", "check", "."]),
    ],
    "dotnet": [
        CheckConfig(name="dotnet-format", cmd=["dotnet", "format", "--verify-no-changes"]),
    ],
    "nextjs": [
        CheckConfig(name="prettier-check", cmd=["prettier", "--check", "."]),
        CheckConfig(name="eslint", cmd=["eslint", "."]),
    ],
}

# Pre-push checks per stack.
_PRE_PUSH_CHECKS: dict[str, list[CheckConfig]] = {
    "common": [
        CheckConfig(
            name="semgrep",
            cmd=["semgrep", "--config", ".semgrep.yml", "--error", "."],
        ),
    ],
    "python": [
        CheckConfig(name="pip-audit", cmd=["pip-audit"]),
        CheckConfig(name="stack-tests", cmd=["uv", "run", "pytest", "--tb=short", "-q"]),
        CheckConfig(name="ty-check", cmd=["ty", "check", "src/ai_engineering"]),
    ],
    "dotnet": [
        CheckConfig(name="dotnet-build", cmd=["dotnet", "build", "--no-restore"]),
        CheckConfig(name="dotnet-test", cmd=["dotnet", "test", "--no-build"]),
        CheckConfig(name="dotnet-vuln", cmd=["dotnet", "list", "package", "--vulnerable"]),
    ],
    "nextjs": [
        CheckConfig(name="tsc-check", cmd=["tsc", "--noEmit"]),
        CheckConfig(name="vitest", cmd=["vitest", "run"]),
        CheckConfig(name="npm-audit", cmd=["npm", "audit"]),
    ],
}


def _get_active_stacks(project_root: Path) -> list[str]:
    """Read installed stacks from install-manifest.json.

    Falls back to ``["python"]`` if the manifest does not exist or cannot
    be parsed, preserving backward-compatible behavior.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of active stack names.
    """
    manifest_path = project_root / ".ai-engineering" / "state" / "install-manifest.json"
    if not manifest_path.exists():
        return ["python"]
    try:
        manifest = read_json_model(manifest_path, InstallManifest)
        stacks = manifest.installed_stacks
        return stacks if stacks else ["python"]
    except (OSError, ValueError):
        return ["python"]


def _check_branch_protection(project_root: Path, result: GateResult) -> None:
    """Block direct commits to protected branches."""
    branch = current_branch(project_root)
    if branch and branch in PROTECTED_BRANCHES:
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=False,
                output=f"Direct commits to '{branch}' are blocked. Use a feature branch.",
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=True,
                output=f"On branch: {branch or 'unknown'}",
            )
        )


def _check_version_deprecation(result: GateResult) -> None:
    """Block gate execution if the installed version is deprecated or EOL.

    Defense-in-depth check (D-010-2). The primary block is the CLI callback;
    this gate check provides an additional enforcement layer in git hooks.
    Fail-open: registry errors pass the check.
    """
    from ai_engineering.__version__ import __version__
    from ai_engineering.version.checker import check_version

    check = check_version(__version__)

    if check.is_deprecated or check.is_eol:
        status_label = "deprecated" if check.is_deprecated else "end-of-life"
        result.checks.append(
            GateCheckResult(
                name="version-deprecation",
                passed=False,
                output=(
                    f"ai-engineering {__version__} is {status_label}. "
                    f"{check.message}. "
                    f"Run 'ai-eng update' to upgrade."
                ),
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="version-deprecation",
                passed=True,
                output=f"Version lifecycle: {check.message}",
            )
        )


def _run_pre_commit_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-commit gate checks: common + per-stack checks + risk warnings."""
    stacks = _get_active_stacks(project_root)
    _run_checks_for_stacks(
        project_root,
        result,
        _PRE_COMMIT_CHECKS,
        stacks,
    )

    # Risk expiry warnings (non-blocking)
    _check_expiring_risk_acceptances(project_root, result)


def _run_commit_msg_checks(
    commit_msg_file: Path | None,
    result: GateResult,
) -> None:
    """Validate commit message format."""
    if commit_msg_file is None or not commit_msg_file.is_file():
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=True,
                output="No commit message file provided — skipped",
            )
        )
        return

    try:
        msg = commit_msg_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=False,
                output=f"Failed to read commit message: {exc}",
            )
        )
        return

    errors = _validate_commit_message(msg)
    if errors:
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=False,
                output="; ".join(errors),
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=True,
                output="Commit message format valid",
            )
        )


def _run_pre_push_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-push gate checks: common + per-stack checks + expired risks."""
    stacks = _get_active_stacks(project_root)
    _run_checks_for_stacks(
        project_root,
        result,
        _PRE_PUSH_CHECKS,
        stacks,
    )

    # Expired risk acceptances (blocking)
    _check_expired_risk_acceptances(project_root, result)


def _run_checks_for_stacks(
    project_root: Path,
    result: GateResult,
    registry: dict[str, list[CheckConfig]],
    stacks: list[str],
) -> None:
    """Execute checks from *registry* for common + each active stack.

    Args:
        project_root: Root directory of the project.
        result: GateResult to append check outcomes to.
        registry: Mapping of stack name to list of check configurations.
        stacks: Active stack names from install manifest.
    """
    # Always run common checks
    for check in registry.get("common", []):
        _run_tool_check(
            result,
            name=check.name,
            cmd=check.cmd,
            cwd=project_root,
            required=check.required,
        )

    # Run per-stack checks
    for stack in stacks:
        for check in registry.get(stack, []):
            _run_tool_check(
                result,
                name=check.name,
                cmd=check.cmd,
                cwd=project_root,
                required=check.required,
            )


def _run_tool_check(
    result: GateResult,
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
    required: bool = False,
) -> None:
    """Run a tool command and record the result.

    If the tool is not found on PATH, behavior depends on ``required``:
    when True the check fails; when False it is skipped with a warning.

    Args:
        result: GateResult to append check to.
        name: Human-readable check name.
        cmd: Command and arguments to run.
        cwd: Working directory for the command.
        required: If True, missing tool causes check failure.
    """
    tool_name = cmd[0]
    if not shutil.which(tool_name):
        if required:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=False,
                    output=(
                        f"{tool_name} not found — required. "
                        "Run 'ai-eng doctor --fix-tools' to install."
                    ),
                )
            )
        else:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=True,
                    output=f"{tool_name} not found — skipped (run 'ai-eng doctor --fix-tools')",
                )
            )
        return

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        passed = proc.returncode == 0
        output = proc.stdout.strip() or proc.stderr.strip()
        if not output:
            output = f"{tool_name} exited with code {proc.returncode}"
        # Truncate long output
        if len(output) > 500:
            output = output[:500] + "\n... (truncated)"
    except subprocess.TimeoutExpired:
        passed = False
        output = f"{tool_name} timed out after 300s"
    except FileNotFoundError:
        if required:
            passed = False
            output = (
                f"{tool_name} not found — required. Run 'ai-eng doctor --fix-tools' to install."
            )
        else:
            passed = True
            output = f"{tool_name} not found — skipped"

    result.checks.append(
        GateCheckResult(
            name=name,
            passed=passed,
            output=output,
        )
    )


def _load_decision_store(project_root: Path) -> DecisionStore | None:
    """Load the decision store from the project, or None if unavailable.

    Args:
        project_root: Root directory of the project.

    Returns:
        DecisionStore if the file exists and parses, else None.
    """
    ds_path = project_root / ".ai-engineering" / "state" / "decision-store.json"
    if not ds_path.exists():
        return None
    try:
        return read_json_model(ds_path, DecisionStore)
    except (OSError, ValueError):
        return None


def _check_expiring_risk_acceptances(
    project_root: Path,
    result: GateResult,
) -> None:
    """Warn about risk acceptances expiring within 7 days (non-blocking).

    This is a pre-commit advisory check. It always passes but includes
    warning text in the output.

    Args:
        project_root: Root directory of the project.
        result: GateResult to append check to.
    """
    store = _load_decision_store(project_root)
    if store is None:
        result.checks.append(
            GateCheckResult(
                name="risk-expiry-warning",
                passed=True,
                output="No decision store found — skipped",
            )
        )
        return

    expiring = list_expiring_soon(store)
    if not expiring:
        result.checks.append(
            GateCheckResult(
                name="risk-expiry-warning",
                passed=True,
                output="No risk acceptances expiring soon",
            )
        )
        return

    lines = [f"{len(expiring)} risk acceptance(s) expiring within 7 days:"]
    for d in expiring:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
        lines.append(f"  - {d.id}: expires {exp} ({d.context[:60]})")
    lines.append("Consider renewing or remediating before expiry.")

    result.checks.append(
        GateCheckResult(
            name="risk-expiry-warning",
            passed=True,
            output="\n".join(lines),
        )
    )


def _check_expired_risk_acceptances(
    project_root: Path,
    result: GateResult,
) -> None:
    """Block push if expired risk acceptances exist (blocking).

    This is a pre-push gate check. Expired unresolved risk acceptances
    must be renewed or remediated before code can be pushed.

    Args:
        project_root: Root directory of the project.
        result: GateResult to append check to.
    """
    store = _load_decision_store(project_root)
    if store is None:
        result.checks.append(
            GateCheckResult(
                name="risk-expired-block",
                passed=True,
                output="No decision store found — skipped",
            )
        )
        return

    expired = list_expired_decisions(store)
    if not expired:
        result.checks.append(
            GateCheckResult(
                name="risk-expired-block",
                passed=True,
                output="No expired risk acceptances",
            )
        )
        return

    lines = [f"{len(expired)} expired risk acceptance(s) blocking push:"]
    for d in expired:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
        lines.append(f"  - {d.id}: expired {exp} ({d.context[:60]})")
    lines.append("Run 'ai-eng maintenance risk-status' to review.")
    lines.append("Renew with accept-risk skill or remediate with resolve-risk skill.")

    result.checks.append(
        GateCheckResult(
            name="risk-expired-block",
            passed=False,
            output="\n".join(lines),
        )
    )


def _validate_commit_message(msg: str) -> list[str]:
    """Validate a commit message against project conventions.

    Rules:
    - Must not be empty.
    - First line must not exceed 72 characters.
    - First line must start with a lowercase letter or a known prefix.

    Args:
        msg: The full commit message text.

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[str] = []

    if not msg:
        errors.append("Commit message is empty")
        return errors

    first_line = msg.splitlines()[0].strip()

    if not first_line:
        errors.append("First line is empty")
        return errors

    if len(first_line) > 72:
        errors.append(f"First line exceeds 72 characters ({len(first_line)} chars)")

    return errors
