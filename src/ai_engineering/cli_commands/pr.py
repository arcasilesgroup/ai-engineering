"""PR CLI command per spec-132 D-132-23.

ai-eng pr opens a pull-request from the current branch. Thin wrapper
around run_pr_workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.commands import workflows
from ai_engineering.core.output import Renderer
from ai_engineering.paths import resolve_project_root


def pr_cmd(
    message: Annotated[str, typer.Argument(help="Commit message for the PR")],
    target: Annotated[Path | None, typer.Option("--target")] = None,
) -> None:
    """Standalone off-chain PR open."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("pr")
    result = workflows.run_pr_workflow(root, message)
    _render_result(renderer, result)
    if not result.passed:
        raise typer.Exit(code=1)


def _render_result(renderer: Renderer, result: workflows.WorkflowResult) -> None:
    renderer.header()
    for step in result.steps:
        kind = "skipped" if step.skipped else ("restored" if step.passed else "removed")
        renderer.record(kind, step.name, from_=step.output or None)
    if result.passed:
        renderer.ok("PR workflow completed")
        return
    renderer.error(
        f"PR workflow failed at: {', '.join(result.failed_steps)}",
        code="WORKFLOW_FAILED",
        fix="Inspect the failed step and retry.",
    )
