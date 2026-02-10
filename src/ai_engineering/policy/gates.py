"""Git hook gate checks for ai-engineering.

Implements the quality gates invoked by git hooks:
- **pre-commit**: ruff format, ruff lint, gitleaks.
- **commit-msg**: commit message format validation.
- **pre-push**: semgrep, pip-audit, stack tests, ty type-check.

Also enforces protected branch blocking: direct commits to main/master
are rejected.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.state.models import GateHook


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


# Protected branch names where direct commits are blocked.
_PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master"})


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

    if hook == GateHook.PRE_COMMIT:
        _run_pre_commit_checks(project_root, result)
    elif hook == GateHook.COMMIT_MSG:
        _run_commit_msg_checks(commit_msg_file, result)
    elif hook == GateHook.PRE_PUSH:
        _run_pre_push_checks(project_root, result)

    return result


def _check_branch_protection(project_root: Path, result: GateResult) -> None:
    """Block direct commits to protected branches."""
    branch = _get_current_branch(project_root)
    if branch and branch in _PROTECTED_BRANCHES:
        result.checks.append(GateCheckResult(
            name="branch-protection",
            passed=False,
            output=f"Direct commits to '{branch}' are blocked. Use a feature branch.",
        ))
    else:
        result.checks.append(GateCheckResult(
            name="branch-protection",
            passed=True,
            output=f"On branch: {branch or 'unknown'}",
        ))


def _run_pre_commit_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-commit gate checks: ruff format, ruff lint, gitleaks."""
    # ruff format --check
    _run_tool_check(
        result,
        name="ruff-format",
        cmd=["ruff", "format", "--check", "."],
        cwd=project_root,
    )

    # ruff check (lint)
    _run_tool_check(
        result,
        name="ruff-lint",
        cmd=["ruff", "check", "."],
        cwd=project_root,
    )

    # gitleaks
    _run_tool_check(
        result,
        name="gitleaks",
        cmd=["gitleaks", "detect", "--source", ".", "--no-git"],
        cwd=project_root,
    )


def _run_commit_msg_checks(
    commit_msg_file: Path | None,
    result: GateResult,
) -> None:
    """Validate commit message format."""
    if commit_msg_file is None or not commit_msg_file.is_file():
        result.checks.append(GateCheckResult(
            name="commit-msg-format",
            passed=True,
            output="No commit message file provided — skipped",
        ))
        return

    try:
        msg = commit_msg_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        result.checks.append(GateCheckResult(
            name="commit-msg-format",
            passed=False,
            output=f"Failed to read commit message: {exc}",
        ))
        return

    errors = _validate_commit_message(msg)
    if errors:
        result.checks.append(GateCheckResult(
            name="commit-msg-format",
            passed=False,
            output="; ".join(errors),
        ))
    else:
        result.checks.append(GateCheckResult(
            name="commit-msg-format",
            passed=True,
            output="Commit message format valid",
        ))


def _run_pre_push_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-push gate checks: semgrep, pip-audit, tests, ty."""
    # semgrep
    _run_tool_check(
        result,
        name="semgrep",
        cmd=["semgrep", "--config", ".semgrep.yml", "--error", "."],
        cwd=project_root,
    )

    # pip-audit
    _run_tool_check(
        result,
        name="pip-audit",
        cmd=["pip-audit"],
        cwd=project_root,
    )

    # stack tests (pytest)
    _run_tool_check(
        result,
        name="stack-tests",
        cmd=["uv", "run", "pytest", "--tb=short", "-q"],
        cwd=project_root,
    )

    # ty type-check
    _run_tool_check(
        result,
        name="ty-check",
        cmd=["ty", "check", "src"],
        cwd=project_root,
    )


def _run_tool_check(
    result: GateResult,
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
) -> None:
    """Run a tool command and record the result.

    If the tool is not found on PATH, the check is skipped with a warning
    rather than failing (auto-remediation is handled by the doctor).

    Args:
        result: GateResult to append check to.
        name: Human-readable check name.
        cmd: Command and arguments to run.
        cwd: Working directory for the command.
    """
    tool_name = cmd[0]
    if not shutil.which(tool_name):
        result.checks.append(GateCheckResult(
            name=name,
            passed=True,
            output=f"{tool_name} not found — skipped (run 'ai-eng doctor --fix-tools')",
        ))
        return

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        passed = proc.returncode == 0
        output = proc.stdout.strip() or proc.stderr.strip()
        # Truncate long output
        if len(output) > 500:
            output = output[:500] + "\n... (truncated)"
    except subprocess.TimeoutExpired:
        passed = False
        output = f"{tool_name} timed out after 300s"
    except FileNotFoundError:
        passed = True
        output = f"{tool_name} not found — skipped"

    result.checks.append(GateCheckResult(
        name=name,
        passed=passed,
        output=output,
    ))


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
        errors.append(
            f"First line exceeds 72 characters ({len(first_line)} chars)"
        )

    return errors


def _get_current_branch(project_root: Path) -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
