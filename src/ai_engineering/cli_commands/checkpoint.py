"""Session checkpoint save/load CLI commands.

Implements Hamilton's design-for-failure principle: every session
can die mid-work, and the system must recover gracefully.
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.state.audit import emit_session_event


def _project_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


def _checkpoint_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "session-checkpoint.json"


def checkpoint_save(
    spec_id: Annotated[str, typer.Option(help="Current spec ID")] = "",
    current_task: Annotated[str, typer.Option(help="Current task ID (e.g., 3.2)")] = "",
    progress: Annotated[str, typer.Option(help="Progress (e.g., 17/24)")] = "",
    reasoning: Annotated[str, typer.Option(help="Last reasoning/context")] = "",
    blocked_on: Annotated[
        str | None, typer.Option(help="What is blocking (null if nothing)")
    ] = None,
) -> None:
    """Save a session checkpoint for recovery."""
    root = _project_root()
    path = _checkpoint_path(root)

    checkpoint = {
        "spec_id": spec_id,
        "current_task": current_task,
        "progress": progress,
        "last_reasoning": reasoning,
        "blocked_on": blocked_on,
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")

    # Emit session metric event (fail-open)
    with contextlib.suppress(Exception):
        emit_session_event(root, checkpoint_saved=True)

    typer.echo(f"Checkpoint saved: spec={spec_id} task={current_task} progress={progress}")


def checkpoint_load() -> None:
    """Load the last session checkpoint."""
    root = _project_root()
    path = _checkpoint_path(root)

    if not path.exists():
        typer.echo("No checkpoint found. Starting fresh session.")
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        typer.echo(f"Failed to load checkpoint: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo("# Session Checkpoint")
    typer.echo("")
    typer.echo(f"- Spec: {data.get('spec_id', 'none')}")
    typer.echo(f"- Task: {data.get('current_task', 'none')}")
    typer.echo(f"- Progress: {data.get('progress', 'unknown')}")
    typer.echo(f"- Last reasoning: {data.get('last_reasoning', 'none')}")
    typer.echo(f"- Blocked on: {data.get('blocked_on', 'nothing')}")
    typer.echo(f"- Saved at: {data.get('timestamp', 'unknown')}")
