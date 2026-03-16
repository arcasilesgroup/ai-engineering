"""Session checkpoint save/load CLI commands.

Implements Hamilton's design-for-failure principle: every session
can die mid-work, and the system must recover gracefully.
"""

from __future__ import annotations

import contextlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.paths import find_project_root
from ai_engineering.state.audit import emit_session_event

_CHECKPOINT_FILE = "session-checkpoint.json"
_CHECKPOINT_DIR_PARTS = (".ai-engineering", "state")


def _checkpoint_path(project_root: Path) -> Path:
    root_str = os.path.realpath(str(project_root))
    target = os.path.join(root_str, *_CHECKPOINT_DIR_PARTS, _CHECKPOINT_FILE)
    target = os.path.realpath(target)
    # Validate containment — commonpath is a recognized path sanitizer
    if os.path.commonpath([root_str, target]) != root_str:
        msg = "Checkpoint path escapes project root"
        raise ValueError(msg)
    return Path(target)


def _read_checkpoint(checkpoint: Path) -> dict:
    """Read existing checkpoint data. Returns empty dict if missing or corrupt."""
    if not checkpoint.exists():
        return {}
    with contextlib.suppress(json.JSONDecodeError, OSError):
        return json.loads(checkpoint.read_text(encoding="utf-8"))
    return {}


def _write_checkpoint(project_root: Path, data: dict) -> None:
    """Write checkpoint data to the canonical checkpoint location.

    Constructs the write path independently to avoid taint propagation
    from file reads to file writes (SonarCloud S2083).
    """
    root_str = os.path.realpath(str(project_root))
    target = os.path.join(root_str, *_CHECKPOINT_DIR_PARTS, _CHECKPOINT_FILE)
    target = os.path.realpath(target)
    if os.path.commonpath([root_str, target]) != root_str:
        msg = "Checkpoint path escapes project root"
        raise ValueError(msg)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def checkpoint_save(
    spec_id: Annotated[str, typer.Option(help="Current spec ID")] = "",
    current_task: Annotated[str, typer.Option(help="Current task ID (e.g., 3.2)")] = "",
    progress: Annotated[str, typer.Option(help="Progress (e.g., 17/24)")] = "",
    reasoning: Annotated[str, typer.Option(help="Last reasoning/context")] = "",
    blocked_on: Annotated[
        str | None, typer.Option(help="What is blocking (null if nothing)")
    ] = None,
    agent: Annotated[str, typer.Option(help="Agent saving checkpoint (e.g., build, plan)")] = "",
) -> None:
    """Save a session checkpoint for recovery."""
    root = find_project_root()
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

    _write_checkpoint(root, existing)

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
    root = find_project_root()
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
