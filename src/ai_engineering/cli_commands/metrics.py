"""Metrics collection commands.

Aggregates signal/event data into a compact machine-readable summary.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated

import typer

from ai_engineering.lib.signals import (
    count_events_by_type,
    data_quality_from,
    filter_events,
    gate_pass_rate_from,
    load_all_events,
)
from ai_engineering.paths import find_project_root


def metrics_collect(
    days: Annotated[
        int,
        typer.Option("--days", help="Number of days in metrics window"),
    ] = 30,
) -> None:
    """Collect aggregated metrics from audit events."""
    root = find_project_root()
    since = datetime.now(tz=UTC) - timedelta(days=days)

    all_events = load_all_events(root)
    windowed = filter_events(all_events, since=since)
    quality = data_quality_from(all_events)
    gates = gate_pass_rate_from(all_events, days=days)

    payload = {
        "window_days": days,
        "generated_at": datetime.now(tz=UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ",
        ),
        "data_quality": quality,
        "events": {
            "total": len(windowed),
            "scan_complete": count_events_by_type(windowed, "scan_complete"),
            "build_complete": count_events_by_type(windowed, "build_complete"),
            "gate_result": gates["total"],
            "deploy_complete": count_events_by_type(
                windowed,
                "deploy_complete",
            ),
            "session_metric": count_events_by_type(
                windowed,
                "session_metric",
            ),
        },
        "gate_health": {
            "pass_rate": gates["pass_rate"],
            "failed": gates["failed"],
            "most_failed_check": gates["most_failed_check"],
            "most_failed_count": gates["most_failed_count"],
        },
    }

    typer.echo(json.dumps(payload, indent=2))
