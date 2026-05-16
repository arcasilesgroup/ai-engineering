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


_FAIL_HINT_KEYWORDS: tuple[str, ...] = (
    "leak",
    "warn",
    "wrn",
    "error",
    "err",
    "fail",
    "blocked",
    "denied",
    "violation",
    "rejected",
    "fatal",
)


def _summary_line(output: str, *, max_chars: int = 200) -> str | None:
    """Pick the most informative single-line summary from raw tool output.

    Tools like ``gitleaks`` print boilerplate first (``INF 0 commits
    scanned``) and the actual signal (``WRN leaks found: 1``) on a later
    line. The summary line is the first line whose content matches a
    well-known severity keyword, with a fall-back to the last non-empty
    line, then to the first non-empty line.
    """
    if not output:
        return None
    lines = [line.rstrip() for line in output.strip().splitlines() if line.strip()]
    if not lines:
        return None
    for line in lines:
        haystack = line.lower()
        if any(token in haystack for token in _FAIL_HINT_KEYWORDS):
            return _clip(line, max_chars)
    return _clip(lines[-1], max_chars)


def _clip(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _format_failure_block(output: str) -> str:
    """Format the full failing-step output as an indented diagnostic block.

    Every line is preserved verbatim — the user explicitly asked for full
    detail on failure so they can diagnose without re-running.
    """
    stripped = output.strip()
    if not stripped:
        return "(no output captured)"
    return "\n".join(f"    {line}" for line in stripped.splitlines())


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
        detail = _summary_line(step.output)
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

    renderer.section("Failure detail")
    for step in result.steps:
        if step.passed or step.skipped:
            continue
        renderer.kv("Step", step.name)
        renderer.step(_format_failure_block(step.output))

    failed_names = ", ".join(result.failed_steps) or "(unknown step)"
    renderer.error(
        f"{command_label} workflow failed at: {failed_names}",
        code="WORKFLOW_FAILED",
        fix="Inspect the failure detail block above and re-run after addressing it.",
    )
