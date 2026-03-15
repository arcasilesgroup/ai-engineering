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


_CHECKPOINT_PARTS = (".ai-engineering", "state", "session-checkpoint.json")


def _checkpoint_path(project_root: Path) -> Path:
    root_resolved = project_root.resolve()
    # Build from constant literal components — no user data in path segments
    checkpoint = root_resolved.joinpath(*_CHECKPOINT_PARTS).resolve()
    # Defense-in-depth: verify result stays within project root
    checkpoint.relative_to(root_resolved)  # Raises ValueError if escape
    return checkpoint


def _read_checkpoint(path: Path) -> dict:
    """Read existing checkpoint data. Returns empty dict if missing or corrupt."""
    if not path.exists():
        return {}
    with contextlib.suppress(json.JSONDecodeError, OSError):
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _write_checkpoint(path: Path, data: dict) -> None:
    """Write checkpoint data to a validated path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def checkpoint_save(
    spec_id: Annotated[str, typer.Option(help="Current spec ID")] = "",
    current_task: Annotated[str, typer.Option(help="Current task ID (e.g., 3.2)")] = "",
    progress: Annotated[str, typer.Option(help="Progress (e.g., 17/24)")] = "",
    reasoning: Annotated[str, typer.Option(help="Last reasoning/context")] = "",
    blocked_on: Annotated[
        str | None, typer.Option(help="What is blocking (null if nothing)")
    ] = None,
    agent: Annotated[
        str, typer.Option(help="Agent saving checkpoint (e.g., execute, release)")
    ] = "",
) -> None:
    """Save a session checkpoint for recovery."""
    root = _project_root()
    path = _checkpoint_path(root)

    entry = {
        "spec_id": spec_id,
        "current_task": current_task,
        "progress": progress,
        "last_reasoning": reasoning,
        "blocked_on": blocked_on,
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Namespaced checkpoint: each agent writes to its own section
    # while preserving other agents' data. Backward-compatible with flat schema.
    existing = _read_checkpoint(path)

    if agent:
        # Namespaced write: store under agents.<agent>
        agents_section = existing.get("agents", {})
        agents_section[agent] = entry
        existing["agents"] = agents_section
        # Also update top-level for backward compatibility
        existing.update(entry)
    else:
        # Legacy flat write
        existing.update(entry)

    _write_checkpoint(path, existing)

    # Emit session metric event with checkpoint context (fail-open)
    with contextlib.suppress(Exception):
        # Parse progress for decisions/skills context
        completed = 0
        if progress and "/" in progress:
            parts = progress.split("/")
            with contextlib.suppress(ValueError, IndexError):
                completed = int(parts[0])

        emit_session_event(
            root,
            checkpoint_saved=True,
            tokens_used=0,  # LLM has no token introspection at CLI level
            decisions_reused=completed,  # tasks completed ≈ decisions executed
            skills_loaded=[s for s in [spec_id] if s],  # track active spec
        )

    typer.echo(f"Checkpoint saved: spec={spec_id} task={current_task} progress={progress}")


def checkpoint_load(
    agent: Annotated[str, typer.Option(help="Load checkpoint for specific agent")] = "",
) -> None:
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

    # If agent-specific checkpoint requested, use namespaced data
    found_agent_data = False
    if agent and "agents" in data and agent in data["agents"]:
        data = data["agents"][agent]
        found_agent_data = True

    typer.echo("# Session Checkpoint")
    typer.echo("")
    if found_agent_data:
        typer.echo(f"- Agent: {agent}")
    typer.echo(f"- Spec: {data.get('spec_id', 'none')}")
    typer.echo(f"- Task: {data.get('current_task', 'none')}")
    typer.echo(f"- Progress: {data.get('progress', 'unknown')}")
    typer.echo(f"- Last reasoning: {data.get('last_reasoning', 'none')}")
    typer.echo(f"- Blocked on: {data.get('blocked_on', 'nothing')}")
    typer.echo(f"- Saved at: {data.get('timestamp', 'unknown')}")

    # Show all agent checkpoints if no specific agent requested
    if not agent and "agents" in data:
        typer.echo("")
        typer.echo("## Agent Checkpoints")
        for agent_name, agent_data in data["agents"].items():
            task = agent_data.get("current_task", "?")
            prog = agent_data.get("progress", "?")
            typer.echo(f"- {agent_name}: task={task} progress={prog}")
