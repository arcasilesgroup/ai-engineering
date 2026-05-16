"""Status CLI command.

``ai-eng status`` prints a read-only summary of the installed framework
via the shared ``render_config`` helper (single source of truth for the
posture view across install, config, and status).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_commands._render_config import render_config, render_config_payload
from ai_engineering.core.output import NextAction, Renderer
from ai_engineering.installer.operations import InstallerError, list_status
from ai_engineering.paths import resolve_project_root


def status_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Show summary of the installed framework configuration."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("status")
    try:
        manifest = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="STATUS_FAILED",
            fix="Run 'ai-eng install' first.",
            next_actions=[
                NextAction(
                    label="Install the framework here",
                    command="ai-eng install",
                ),
            ],
        )
        return

    renderer.header()
    renderer.action("Verifying", "framework status", detail=str(root))
    render_config(manifest, renderer)
    renderer.next(
        [
            NextAction(label="Run health diagnostics", command="ai-eng doctor"),
            NextAction(label="Run content-integrity check", command="ai-eng check"),
        ]
    )
    renderer.ok("framework status", result=render_config_payload(manifest))
