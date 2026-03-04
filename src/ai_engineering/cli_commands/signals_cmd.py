"""Signal emission and query CLI commands.

Provides `ai-eng signals emit` and `ai-eng signals query` for
interacting with the single event store (audit-log.ndjson).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.state.io import append_ndjson
from ai_engineering.state.models import AuditEntry


def _project_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


def signals_emit(
    event: Annotated[str, typer.Argument(help="Event type (e.g., scan_complete, gate_result)")],
    actor: Annotated[str, typer.Option(help="Actor that emitted the event")] = "cli",
    detail_json: Annotated[str, typer.Option("--detail", help="JSON detail payload")] = "{}",
    spec: Annotated[str | None, typer.Option(help="Associated spec ID")] = None,
) -> None:
    """Emit a structured event to the audit log."""
    root = _project_root()
    from ai_engineering.lib.signals import audit_log_path

    audit_path = audit_log_path(root)

    try:
        detail = json.loads(detail_json)
    except json.JSONDecodeError:
        typer.echo(f"Invalid JSON in --detail: {detail_json}", err=True)
        raise typer.Exit(code=1) from None

    entry = AuditEntry(
        timestamp=datetime.now(tz=UTC),
        event=event,
        actor=actor,
        spec=spec,
        detail=detail if detail else None,
    )

    append_ndjson(audit_path, entry)
    typer.echo(f"Emitted: {event} by {actor}")


def signals_query(
    event_type: Annotated[str | None, typer.Option("--type", help="Filter by event type")] = None,
    limit: Annotated[int, typer.Option(help="Max events to show")] = 20,
    days: Annotated[int, typer.Option(help="Only events from last N days")] = 30,
) -> None:
    """Query events from the audit log."""
    from ai_engineering.lib.signals import read_events

    root = _project_root()
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
