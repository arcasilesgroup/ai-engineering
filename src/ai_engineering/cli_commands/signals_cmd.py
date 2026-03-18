"""Signal emission and query CLI commands.

Provides `ai-eng signals emit` and `ai-eng signals query` for
interacting with the single event store (audit-log.ndjson).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

import typer

from ai_engineering.git.context import get_git_context
from ai_engineering.paths import find_project_root
from ai_engineering.state.models import AuditEntry
from ai_engineering.state.service import StateService
from ai_engineering.vcs.repo_context import get_repo_context


def signals_emit(
    event: Annotated[str, typer.Argument(help="Event type (e.g., scan_complete, gate_result)")],
    actor: Annotated[str, typer.Option(help="Actor that emitted the event")] = "cli",
    detail_json: Annotated[str, typer.Option("--detail", help="JSON detail payload")] = "{}",
    source: Annotated[
        str | None, typer.Option("--source", help="Event source: hook, cli, gate-engine, ci")
    ] = None,
) -> None:
    """Emit a structured event to the audit log."""
    root = find_project_root()

    try:
        detail = json.loads(detail_json)
    except json.JSONDecodeError:
        typer.echo(f"Invalid JSON in --detail: {detail_json}", err=True)
        raise typer.Exit(code=1) from None

    repo_ctx = get_repo_context(root)
    git_ctx = get_git_context(root)

    from ai_engineering.state.audit import _read_active_spec, _read_active_stack

    entry = AuditEntry(
        timestamp=datetime.now(tz=UTC),
        event=event,
        actor=actor,
        detail=detail if detail else None,
        source=source,
        spec_id=_read_active_spec(root),
        stack=_read_active_stack(root),
        vcs_provider=repo_ctx.provider if repo_ctx else None,
        vcs_organization=repo_ctx.organization if repo_ctx else None,
        vcs_project=repo_ctx.project if repo_ctx else None,
        vcs_repository=repo_ctx.repository if repo_ctx else None,
        branch=git_ctx.branch if git_ctx else None,
        commit_sha=git_ctx.commit_sha if git_ctx else None,
    )

    StateService(root).append_audit(entry)
    typer.echo(f"Emitted: {event} by {actor}")


def signals_query(
    event_type: Annotated[str | None, typer.Option("--type", help="Filter by event type")] = None,
    limit: Annotated[int, typer.Option(help="Max events to show")] = 20,
    days: Annotated[int, typer.Option(help="Only events from last N days")] = 30,
) -> None:
    """Query events from the audit log."""
    from ai_engineering.lib.signals import read_events

    root = find_project_root()
    from datetime import timedelta

    since = datetime.now(tz=UTC) - timedelta(days=days)

    events = read_events(root, event_type=event_type, since=since, limit=limit)

    if not events:
        typer.echo("No events found matching criteria.")
        return

    typer.echo(f"# Events ({len(events)} shown, last {days} days)")
    typer.echo("")
    for event in events:
        ts = event.get("timestamp", "?")
        evt = event.get("event", "?")
        actor = event.get("actor", "?")
        detail = event.get("detail", "")
        detail_summary = ""
        if isinstance(detail, dict):
            detail_summary = f" | {json.dumps(detail, default=str)[:100]}"
        elif isinstance(detail, str) and detail:
            detail_summary = f" | {detail[:100]}"
        typer.echo(f"  {ts} | {evt} | {actor}{detail_summary}")
