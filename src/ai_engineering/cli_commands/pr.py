"""PR CLI command per spec-132 D-132-23.

``ai-eng pr`` opens a pull-request from the current branch. Thin wrapper
around :func:`workflows.run_pr_workflow` that reuses the ``commit``
pipeline renderer so the output contract stays uniform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_commands.commit import _render_result
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
    _render_result(renderer, result, command_label="PR")
    if not result.passed:
        raise typer.Exit(code=1)
