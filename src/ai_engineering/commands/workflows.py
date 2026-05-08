"""Commit/PR workflow helper functions.

Provides programmatic building blocks for the ``/commit`` and ``/pr``
flows described in ``skills/commit/``, ``skills/pr/``.

Flow summary:

- ``run_commit_workflow`` — stage, format, lint, gitleaks, commit, push.
- ``run_pr_workflow`` — commit flow + pre-push checks + create PR + auto-complete.
- ``run_pr_only_workflow`` — create PR from current HEAD (no stage/commit).

These are **helper functions**, not CLI entry points.
The CLI invokes them from ``cli_commands/``.
Workflow skills (``/commit``, ``/pr``) are markdown documents
AI agents read — these Python functions are the implementation backing.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.git.operations import (
    PROTECTED_BRANCHES,
    current_branch,
    is_branch_pushed,
)
from ai_engineering.policy import orchestrator as orchestrator_module
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore, GateFindingsDocument, GateSeverity
from ai_engineering.state.observability import emit_framework_operation
from ai_engineering.vcs.factory import get_provider
from ai_engineering.vcs.pr_description import build_pr_description, build_pr_title
from ai_engineering.vcs.protocol import VcsContext

logger = logging.getLogger(__name__)

_FAILURE_SEVERITIES: frozenset[GateSeverity] = frozenset(
    {GateSeverity.CRITICAL, GateSeverity.HIGH, GateSeverity.MEDIUM}
)

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


def _staged_files_from_git(project_root: Path) -> list[str]:
    """Return staged files relative to ``project_root`` for kernel parity."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def run_orchestrator_pre_push_gate(project_root: Path) -> GateFindingsDocument:
    """Run the shared kernel fast slice for workflow pre-push checks."""
    cache_dir = project_root / ".ai-engineering" / "state" / "gate-cache"
    return orchestrator_module.run_gate(
        staged_files=_staged_files_from_git(project_root),
        mode="local",
        cache_dir=cache_dir,
        project_root=project_root,
        cache_disabled=False,
        produced_by="ai-pr",
        auto_stage_enabled=False,
    )


def _workflow_steps_from_gate_document(
    project_root: Path,
    document: GateFindingsDocument,
) -> list[StepResult]:
    """Translate the kernel findings envelope into workflow-friendly step results."""
    contract = orchestrator_module.resolve_kernel_contract(project_root, mode="local")
    findings_by_check: dict[str, list[object]] = {}
    for finding in document.findings:
        findings_by_check.setdefault(finding.check, []).append(finding)

    steps: list[StepResult] = []
    for check_name in contract.check_registration:
        findings = findings_by_check.get(check_name, [])
        blocking = [f for f in findings if f.severity in _FAILURE_SEVERITIES]  # ty:ignore[unresolved-attribute]
        output = "ok"
        if findings:
            messages = sorted({str(f.message) for f in findings})  # ty:ignore[unresolved-attribute]
            output = "; ".join(messages)
        steps.append(
            StepResult(
                name=check_name,
                passed=not blocking,
                output=output,
            )
        )
    return steps


def _log_audit(
    project_root: Path,
    *,
    event: str,
    detail: str,
    actor: str = "workflow",
) -> None:
    """Emit a framework operation event for workflow activity."""
    state_dir = project_root / ".ai-engineering" / "state"
    if state_dir.is_dir():
        emit_framework_operation(
            project_root,
            operation=event,
            component=f"workflow.{actor}",
            source="cli",
            metadata={"message": detail},
        )


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
        ["gitleaks", "protect", "--staged", "--no-banner"],
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

    # Create or update PR
    pr_steps = _upsert_pr(project_root)
    result.steps.extend(pr_steps)
    if any(not step.passed for step in pr_steps):
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

    # Create or update PR
    pr_steps = _upsert_pr(project_root)
    result.steps.extend(pr_steps)
    if any(not step.passed for step in pr_steps):
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
    """Run pre-push quality gates through the shared kernel-backed authority.

    Args:
        project_root: Root directory of the project.

    Returns:
        List of StepResult for each check.
    """
    document = run_orchestrator_pre_push_gate(project_root)
    steps = _workflow_steps_from_gate_document(project_root, document)

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
    """Create a PR using the configured VCS provider.

    Generates a structured title and description from the active spec
    and recent commits, then delegates to the provider.

    Args:
        project_root: Root directory of the project.

    Returns:
        StepResult for PR creation.
    """
    provider = get_provider(project_root)
    branch = current_branch(project_root)
    title = build_pr_title(project_root)
    body = build_pr_description(project_root)
    ctx = VcsContext(
        project_root=project_root,
        title=title,
        body=body,
        branch=branch,
    )
    result = provider.create_pr(ctx)
    return StepResult(name="create-pr", passed=result.success, output=result.output)


def _upsert_pr(project_root: Path) -> list[StepResult]:
    """Create a new PR or extend an existing PR description.

    Existing PR behavior is append-only:
    current body is preserved, then a new ``Additional Changes``
    section is appended with the latest generated summary.
    """
    provider = get_provider(project_root)
    branch = current_branch(project_root)
    title = build_pr_title(project_root)
    body = build_pr_description(project_root)
    ctx = VcsContext(
        project_root=project_root,
        title=title,
        body=body,
        branch=branch,
    )

    existing = provider.find_open_pr(ctx)
    lookup_step = StepResult(
        name="check-existing-pr",
        passed=existing.success,
        output=existing.output,
    )
    if not existing.success:
        return [lookup_step]
    if not existing.output:
        create = provider.create_pr(ctx)
        return [
            lookup_step,
            StepResult(name="create-pr", passed=create.success, output=create.output),
        ]

    try:
        pr_data = json.loads(existing.output)
    except json.JSONDecodeError:
        return [
            lookup_step,
            StepResult(
                name="update-pr",
                passed=False,
                output="Failed to parse existing PR response",
            ),
        ]

    if not isinstance(pr_data, dict):
        return [
            lookup_step,
            StepResult(
                name="update-pr",
                passed=False,
                output="Invalid existing PR payload",
            ),
        ]

    existing_body = str(pr_data.get("body", "") or "").strip()
    new_changes = body.strip()
    if existing_body:
        extended_body = f"{existing_body}\n\n---\n\n## Additional Changes\n\n{new_changes}"
    else:
        extended_body = new_changes

    pr_number = str(pr_data.get("number", "") or "")
    if not pr_number:
        return [
            lookup_step,
            StepResult(
                name="update-pr",
                passed=False,
                output="Existing PR is missing identifier",
            ),
        ]

    update_ctx = VcsContext(
        project_root=project_root,
        title=str(pr_data.get("title", "") or title),
        body=extended_body,
        branch=branch,
    )
    update = provider.update_pr(
        update_ctx,
        pr_number=pr_number,
        title=str(pr_data.get("title", "") or ""),
    )
    return [lookup_step, StepResult(name="update-pr", passed=update.success, output=update.output)]


def _enable_auto_complete(project_root: Path) -> StepResult:
    """Enable auto-complete / auto-merge on the current PR.

    Delegates to the configured VCS provider.

    Args:
        project_root: Root directory of the project.

    Returns:
        StepResult for auto-complete setup.
    """
    provider = get_provider(project_root)
    branch = current_branch(project_root)
    ctx = VcsContext(project_root=project_root, branch=branch)
    result = provider.enable_auto_complete(ctx)
    return StepResult(name="auto-complete", passed=result.success, output=result.output)


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
    except Exception:  # fail-open: missing store is not fatal
        logger.debug("Could not read decision store", exc_info=True)

    return None
