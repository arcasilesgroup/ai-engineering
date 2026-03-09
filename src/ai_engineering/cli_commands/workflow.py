"""Workflow CLI commands: commit, PR, and PR-only.

Provides ``ai-eng workflow commit``, ``ai-eng workflow pr``, and
``ai-eng workflow pr-only`` as thin CLI wrappers around the programmatic
workflow functions in :mod:`ai_engineering.commands.workflows`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, info, status_line, success
from ai_engineering.commands.workflows import (
    WorkflowResult,
    run_commit_workflow,
    run_pr_only_workflow,
    run_pr_workflow,
)
from ai_engineering.paths import resolve_project_root


def _render_result(result: WorkflowResult) -> None:
    """Render a WorkflowResult to the terminal or JSON output.

    Args:
        result: The workflow result to render.
    """
    if is_json_mode():
        from ai_engineering.cli_envelope import emit_error, emit_success

        payload = {
            "workflow": result.workflow,
            "passed": result.passed,
            "steps": [
                {
                    "name": s.name,
                    "passed": s.passed,
                    "skipped": s.skipped,
                    "output": s.output,
                }
                for s in result.steps
            ],
            "failed_steps": result.failed_steps,
        }
        if result.passed:
            emit_success(f"ai-eng workflow {result.workflow}", payload)
        else:
            emit_error(
                f"ai-eng workflow {result.workflow}",
                f"Failed steps: {', '.join(result.failed_steps)}",
                "WORKFLOW_FAILED",
                "Fix the failed step(s) and retry.",
            )
        return

    info(f"Workflow: {result.workflow}")
    for step in result.steps:
        if step.skipped:
            status_line("ok", f"{step.name} (skipped)", step.output or "skipped")
        elif step.passed:
            status_line("ok", step.name, step.output or "passed")
        else:
            status_line("fail", step.name, step.output or "failed")

    if result.passed:
        success(f"Workflow '{result.workflow}' completed successfully.")
    else:
        error(f"Workflow '{result.workflow}' failed at: {', '.join(result.failed_steps)}")


def workflow_commit(
    message: Annotated[str, typer.Argument(help="Commit message")],
    only: Annotated[
        bool,
        typer.Option("--only", help="Commit only — skip push."),
    ] = False,
    target: Annotated[Path | None, typer.Option("--target", "-t", help="Project root.")] = None,
) -> None:
    """Stage, format, lint, check secrets, commit, and push."""
    root = resolve_project_root(target)
    result = run_commit_workflow(root, message, push=not only)
    _render_result(result)
    if not result.passed:
        raise typer.Exit(code=1)


def workflow_pr(
    message: Annotated[str, typer.Argument(help="Commit message for the PR")],
    target: Annotated[Path | None, typer.Option("--target", "-t", help="Project root.")] = None,
) -> None:
    """Full PR workflow: commit + pre-push checks + create PR + auto-complete."""
    root = resolve_project_root(target)
    result = run_pr_workflow(root, message)
    _render_result(result)
    if not result.passed:
        raise typer.Exit(code=1)


def workflow_pr_only(
    target: Annotated[Path | None, typer.Option("--target", "-t", help="Project root.")] = None,
) -> None:
    """Create a PR from the current HEAD without staging or committing."""
    root = resolve_project_root(target)
    result = run_pr_only_workflow(root)
    _render_result(result)
    if not result.passed:
        raise typer.Exit(code=1)
