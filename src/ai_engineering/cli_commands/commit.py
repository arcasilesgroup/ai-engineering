"""Commit CLI command per spec-132 D-132-23."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.commands import workflows
from ai_engineering.core.output import Renderer
from ai_engineering.paths import resolve_project_root


def commit_cmd(
    message: Annotated[str, typer.Argument(help="Commit message")],
    only: Annotated[bool, typer.Option("--only")] = False,
    target: Annotated[Path | None, typer.Option("--target")] = None,
) -> None:
    """Standalone off-chain commit."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("commit")
    result = workflows.run_commit_workflow(root, message, push=not only)
    _render_result(renderer, result)
    if not result.passed:
        raise typer.Exit(code=1)


def _render_result(renderer: Renderer, result: workflows.WorkflowResult) -> None:
    renderer.header()
    for step in result.steps:
        kind = "skipped" if step.skipped else ("restored" if step.passed else "removed")
        renderer.record(kind, step.name, from_=step.output or None)
    if result.passed:
        renderer.ok("workflow completed")
        return
    renderer.error(
        "workflow failed",
        code="WORKFLOW_FAILED",
        fix="Inspect the failed step and retry.",
    )
