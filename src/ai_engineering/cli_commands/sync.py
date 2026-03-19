"""CLI command for syncing command mirrors across IDE surfaces.

Provides the ``ai-eng sync`` command that regenerates all IDE-adapted
mirrors from canonical ``.claude/skills/`` and ``.claude/agents/``
sources into ``.agents/``, ``.github/``, and project templates,
or verifies they are in sync (``--check`` mode).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import result_header, status_line, suggest_next
from ai_engineering.paths import resolve_project_root


def sync_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Verify mirrors are in sync; exit 1 if drift detected."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed diff and hash information."),
    ] = False,
) -> None:
    """Sync command mirrors across all IDE surfaces.

    Regenerates skill and agent mirrors from canonical .claude/skills/
    and .claude/agents/ sources into .agents/, .github/, and project
    templates.

    Use --check to verify without writing changes.
    """
    root = resolve_project_root(target)
    script = root / "scripts" / "sync_command_mirrors.py"

    if not script.is_file():
        if is_json_mode():
            emit_error(
                command="ai-eng sync",
                message=f"Sync script not found: {script}",
                code="SCRIPT_NOT_FOUND",
                fix="Ensure scripts/sync_command_mirrors.py exists in the project root.",
            )
        else:
            typer.echo(f"Error: sync script not found: {script}", err=True)
        raise typer.Exit(code=1)

    cmd = [sys.executable, str(script)]
    if check:
        cmd.append("--check")
    if verbose:
        cmd.append("--verbose")

    action = "Checking mirror sync..." if check else "Syncing mirrors..."
    with spinner(action):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))

    exit_code = result.returncode

    if exit_code == 0:
        if is_json_mode():
            emit_success(
                "ai-eng sync",
                {"status": "in_sync", "check": check},
                [NextAction(command="ai-eng validate", description="Run content integrity checks")],
            )
        else:
            status = "in sync" if check else "synced"
            result_header("Sync", "PASS", str(root))
            status_line("ok", "Mirrors", status)
    elif exit_code == 1:
        if is_json_mode():
            emit_error(
                command="ai-eng sync",
                message="Mirror drift detected",
                code="DRIFT",
                fix="Run 'ai-eng sync' without --check to apply changes.",
                next_actions=[
                    NextAction(command="ai-eng sync", description="Apply sync to fix drift")
                ],
            )
        else:
            result_header("Sync", "FAIL", str(root))
            status_line("fail", "Mirrors", "drift detected")
            if result.stdout:
                typer.echo(result.stdout, err=True)
            suggest_next([("ai-eng sync", "Apply sync to fix drift")])
        raise typer.Exit(code=1)
    else:
        if is_json_mode():
            emit_error(
                command="ai-eng sync",
                message="Canonical source validation failed",
                code="VALIDATION_ERROR",
                fix="Check .claude/skills/ and .claude/agents/ for errors.",
            )
        else:
            result_header("Sync", "FAIL", str(root))
            status_line("fail", "Canonical validation", "failed")
            if result.stderr:
                typer.echo(result.stderr, err=True)
            if result.stdout:
                typer.echo(result.stdout, err=True)
        raise typer.Exit(code=1)
