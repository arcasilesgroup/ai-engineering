"""Commit/PR/Acho workflow helper functions.

Provides programmatic building blocks for the ``/commit``, ``/pr``,
and ``/acho`` flows described in ``skills/workflows/``.

Flow summary:

- ``run_commit_workflow`` — stage, format, lint, gitleaks, commit, push.
- ``run_pr_workflow`` — commit flow + pre-push checks + create PR + auto-complete.
- ``run_pr_only_workflow`` — create PR from current HEAD (no stage/commit).

These are **helper functions**, not CLI entry points.
The CLI invokes them from ``cli_commands/``.
Workflow skills (``/commit``, ``/pr``, ``/acho``) are markdown documents
AI agents read — these Python functions are the implementation backing.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering.git.operations import (
    PROTECTED_BRANCHES,
    current_branch,
    is_branch_pushed,
)
from ai_engineering.policy.gates import GateHook, run_gate
from ai_engineering.state.io import append_ndjson, read_json_model
from ai_engineering.state.models import AuditEntry, DecisionStore

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Outcome of a single workflow step."""

    name: str
    passed: bool
    output: str = ""
    skipped: bool = False


@dataclass
class WorkflowResult:
    """Outcome of a full workflow execution."""

    workflow: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all non-skipped steps passed."""
        return all(s.passed or s.skipped for s in self.steps)

    @property
    def failed_steps(self) -> list[str]:
        """Names of steps that failed."""
        return [s.name for s in self.steps if not s.passed and not s.skipped]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_command(
    cmd: list[str],
    cwd: Path,
    *,
    timeout: int = 120,
) -> tuple[bool, str]:
    """Run a shell command and return (success, combined output).

    Args:
        cmd: Command and arguments.
        cwd: Working directory.
        timeout: Maximum seconds to wait.

    Returns:
        Tuple of (passed, output_text).
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s: {' '.join(cmd)}"


def _log_audit(
    project_root: Path,
    *,
    event: str,
    detail: str,
    actor: str = "workflow",
) -> None:
    """Append an audit log entry.

    Args:
        project_root: Root directory of the project.
        event: Event name (e.g. "commit", "pr-created").
        detail: Event detail text.
        actor: Who triggered the event.
    """
    audit_path = project_root / ".ai-engineering" / "state" / "audit-log.ndjson"
    if audit_path.parent.is_dir():
        entry = AuditEntry(
            timestamp=datetime.now(tz=UTC),
            event=event,
            actor=actor,
            detail=detail,
        )
        append_ndjson(audit_path, entry)


def _check_branch_protection(project_root: Path) -> StepResult:
    """Verify current branch is not protected.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        StepResult — fails if on a protected branch.
    """
    branch = current_branch(project_root)
    if branch in PROTECTED_BRANCHES:
        _log_audit(
            project_root,
            event="branch-protection-block",
            detail=f"Blocked commit on protected branch: {branch}",
        )
        return StepResult(
            name="branch-protection",
            passed=False,
            output=f"Direct commits to '{branch}' are blocked.",
        )
    return StepResult(name="branch-protection", passed=True)


# ---------------------------------------------------------------------------
# Commit workflow
# ---------------------------------------------------------------------------


def run_commit_workflow(
    project_root: Path,
    message: str,
    *,
    push: bool = True,
) -> WorkflowResult:
    """Execute the ``/commit`` workflow.

    Steps: stage → format → lint → gitleaks → commit → push.
    Set ``push=False`` for ``/commit --only``.

    Args:
        project_root: Root directory of the project.
        message: Commit message.
        push: Whether to push after commit (True by default).

    Returns:
        WorkflowResult with per-step outcomes.
    """
    result = WorkflowResult(workflow="commit")

    # 0. Branch protection
    branch_check = _check_branch_protection(project_root)
    result.steps.append(branch_check)
    if not branch_check.passed:
        return result

    # 1. Stage
    passed, output = _run_command(["git", "add", "-A"], project_root)
    result.steps.append(StepResult(name="stage", passed=passed, output=output))
    if not passed:
        return result

    # 2. Format
    passed, output = _run_command(["ruff", "format", "."], project_root)
    result.steps.append(StepResult(name="format", passed=passed, output=output))
    if not passed:
        _log_audit(
            project_root,
            event="format-failure",
            detail=output[:500],
        )
        return result

    # 3. Lint (with auto-fix)
    passed, output = _run_command(
        ["ruff", "check", ".", "--fix"],
        project_root,
    )
    result.steps.append(StepResult(name="lint", passed=passed, output=output))
    if not passed:
        _log_audit(
            project_root,
            event="lint-failure",
            detail=output[:500],
        )
        return result

    # 4. Gitleaks (staged secrets detection)
    passed, output = _run_command(
        ["gitleaks", "detect", "--staged", "--no-banner"],
        project_root,
    )
    result.steps.append(
        StepResult(
            name="gitleaks",
            passed=passed,
            output=output,
        )
    )
    if not passed:
        _log_audit(
            project_root,
            event="secret-detection-failure",
            detail="Secrets detected in staged changes",
        )
        return result

    # Re-stage after format/lint fixes
    _run_command(["git", "add", "-A"], project_root)

    # 5. Commit
    passed, output = _run_command(
        ["git", "commit", "-m", message],
        project_root,
    )
    result.steps.append(
        StepResult(
            name="commit",
            passed=passed,
            output=output,
        )
    )
    if not passed:
        return result

    _log_audit(
        project_root,
        event="commit",
        detail=f"Committed: {message}",
    )

    # 6. Push (unless --only)
    if push:
        branch = current_branch(project_root)
        passed, output = _run_command(
            ["git", "push", "origin", branch],
            project_root,
            timeout=30,
        )
        result.steps.append(
            StepResult(
                name="push",
                passed=passed,
                output=output,
            )
        )
        if not passed:
            _log_audit(
                project_root,
                event="push-failure",
                detail=output[:500],
            )
    else:
        result.steps.append(
            StepResult(
                name="push",
                passed=True,
                skipped=True,
                output="Skipped (--only mode)",
            )
        )

    return result


# ---------------------------------------------------------------------------
# PR workflow
# ---------------------------------------------------------------------------


def run_pr_workflow(
    project_root: Path,
    message: str,
) -> WorkflowResult:
    """Execute the ``/pr`` workflow.

    Steps: commit workflow + pre-push checks + create PR + auto-complete.

    Args:
        project_root: Root directory of the project.
        message: Commit message.

    Returns:
        WorkflowResult with per-step outcomes.
    """
    # Run commit workflow first (with push)
    commit_result = run_commit_workflow(project_root, message, push=True)
    result = WorkflowResult(workflow="pr", steps=list(commit_result.steps))

    if not commit_result.passed:
        return result

    # Pre-push checks
    pre_push_steps = _run_pre_push_checks(project_root)
    result.steps.extend(pre_push_steps)
    if any(not s.passed for s in pre_push_steps):
        return result

    # Create PR
    pr_step = _create_pr(project_root)
    result.steps.append(pr_step)
    if not pr_step.passed:
        return result

    # Auto-complete
    autocomplete_step = _enable_auto_complete(project_root)
    result.steps.append(autocomplete_step)

    _log_audit(
        project_root,
        event="pr-created",
        detail=f"PR created with auto-complete: {message}",
    )

    return result


def run_pr_only_workflow(
    project_root: Path,
) -> WorkflowResult:
    """Execute the ``/pr --only`` workflow.

    Creates a PR from the current HEAD without staging or committing.
    If the branch is unpushed, checks decision store for prior decision.

    Args:
        project_root: Root directory of the project.

    Returns:
        WorkflowResult with per-step outcomes.
    """
    result = WorkflowResult(workflow="pr-only")

    # Check if branch is pushed
    branch = current_branch(project_root)
    pushed = is_branch_pushed(project_root, branch)

    if not pushed:
        # Check decision store for prior decision
        decision = _check_unpushed_decision(project_root, branch)
        if decision == "defer-pr":
            result.steps.append(
                StepResult(
                    name="unpushed-check",
                    passed=False,
                    output=f"Branch '{branch}' is unpushed. Deferred by prior decision.",
                )
            )
            return result

        # Auto-push if no prior defer decision
        passed, output = _run_command(
            ["git", "push", "origin", branch],
            project_root,
            timeout=30,
        )
        result.steps.append(
            StepResult(
                name="auto-push",
                passed=passed,
                output=output,
            )
        )
        if not passed:
            return result

    # Create PR
    pr_step = _create_pr(project_root)
    result.steps.append(pr_step)
    if not pr_step.passed:
        return result

    # Auto-complete
    autocomplete_step = _enable_auto_complete(project_root)
    result.steps.append(autocomplete_step)

    _log_audit(
        project_root,
        event="pr-created",
        detail=f"PR created (--only) on branch {branch}",
    )

    return result


# ---------------------------------------------------------------------------
# Pre-push checks
# ---------------------------------------------------------------------------


def _run_pre_push_checks(project_root: Path) -> list[StepResult]:
    """Run pre-push quality gates by delegating to ``run_gate()``.

    This avoids duplicating the tool-check logic already implemented
    in :func:`ai_engineering.policy.gates.run_gate`.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of StepResult for each check.
    """
    gate_result = run_gate(GateHook.PRE_PUSH, project_root)
    steps: list[StepResult] = [
        StepResult(name=c.name, passed=c.passed, output=c.output)
        for c in gate_result.checks
    ]

    # Log failures
    for step in steps:
        if not step.passed:
            _log_audit(
                project_root,
                event=f"pre-push-failure-{step.name}",
                detail=step.output[:500],
            )

    return steps


# ---------------------------------------------------------------------------
# PR operations
# ---------------------------------------------------------------------------


def _create_pr(project_root: Path) -> StepResult:
    """Create a PR using the GitHub CLI.

    Args:
        project_root: Root directory of the project.

    Returns:
        StepResult for PR creation.
    """
    passed, output = _run_command(
        ["gh", "pr", "create", "--fill"],
        project_root,
        timeout=30,
    )
    return StepResult(name="create-pr", passed=passed, output=output)


def _enable_auto_complete(project_root: Path) -> StepResult:
    """Enable auto-complete (auto-merge) on the PR.

    Args:
        project_root: Root directory of the project.

    Returns:
        StepResult for auto-complete setup.
    """
    passed, output = _run_command(
        ["gh", "pr", "merge", "--auto", "--squash", "--delete-branch"],
        project_root,
        timeout=30,
    )
    return StepResult(name="auto-complete", passed=passed, output=output)


def _check_unpushed_decision(
    project_root: Path,
    branch: str,
) -> str | None:
    """Check decision store for a prior unpushed-branch decision.

    Args:
        project_root: Root directory of the project.
        branch: Branch being checked.

    Returns:
        Decision text if found (e.g. "defer-pr"), or None.
    """
    store_path = project_root / ".ai-engineering" / "state" / "decision-store.json"
    if not store_path.exists():
        return None

    try:
        from ai_engineering.state.decision_logic import (
            compute_context_hash,
        )

        store = read_json_model(store_path, DecisionStore)
        context = f"unpushed-branch-pr:{branch}"
        context_hash = compute_context_hash(context)
        decision = store.find_by_context_hash(context_hash)
        if decision is not None:
            return decision.decision
    except Exception:
        pass

    return None
