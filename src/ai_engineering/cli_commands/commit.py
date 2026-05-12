"""Commit CLI command per spec-132 D-132-23 (commit workflow runner)."""

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
    _render_result(renderer, result, command_label="commit")
    if not result.passed:
        raise typer.Exit(code=1)


def _trim_detail(output: str, *, max_chars: int = 120) -> str | None:
    """Collapse multi-line tool output into a single short detail line."""
    if not output:
        return None
    lines = output.strip().splitlines()
    first = lines[0] if lines else ""
    if len(first) > max_chars:
        first = first[: max_chars - 1] + "…"
    return first or None


def _render_result(
    renderer: Renderer,
    result: workflows.WorkflowResult,
    *,
    command_label: str = "commit",
) -> None:
    renderer.header()
    renderer.action("Verifying", f"{command_label} pipeline")
    passed = failed = skipped = 0
    for step in result.steps:
        detail = _trim_detail(step.output)
        if step.skipped:
            renderer.check_result(step.name, True, detail=detail, skipped=True)
            skipped += 1
        elif step.passed:
            renderer.check_result(step.name, True, detail=detail)
            passed += 1
        else:
            renderer.check_result(step.name, False, detail=detail)
            failed += 1
    renderer.kv("Steps", f"{passed} passed, {failed} failed, {skipped} skipped")
    if result.passed:
        renderer.ok(f"{command_label} workflow completed")
        return
    failed_names = ", ".join(result.failed_steps) or "(unknown step)"
    renderer.error(
        f"{command_label} workflow failed at: {failed_names}",
        code="WORKFLOW_FAILED",
        fix="Inspect the failed step above and re-run after addressing it.",
    )
