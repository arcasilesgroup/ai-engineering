"""NDJSON signal read/write/query for the single event store.

The audit-log.ndjson is the single source of truth for all events
(gates, scans, builds, deploys, sessions). This module provides
query and aggregation utilities on top of state.io primitives.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

AUDIT_LOG_REL = Path(".ai-engineering") / "state" / "audit-log.ndjson"


def audit_log_path(project_root: Path) -> Path:
    """Return the canonical audit-log.ndjson path."""
    return project_root / AUDIT_LOG_REL


def load_all_events(project_root: Path) -> list[dict[str, Any]]:
    """Load all events from audit-log.ndjson once.

    Returns:
        List of event dicts in file order (oldest first).
    """
    path = audit_log_path(project_root)
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def filter_events(
    events: list[dict[str, Any]],
    *,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Filter pre-loaded events in memory (no I/O).

    Args:
        events: Pre-loaded event list from load_all_events().
        event_type: Filter by event type.
        since: Only include events after this timestamp.
        limit: Max events to return (0 = unlimited).

    Returns:
        Filtered events, newest first.
    """
    result: list[dict[str, Any]] = []
    for event in events:
        if event_type and event.get("event") != event_type:
            continue
        if since:
            ts_str = event.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(
                    ts_str.replace("Z", "+00:00"),
                )
                if ts < since:
                    continue
            except (ValueError, AttributeError):
                continue
        result.append(event)

    result.reverse()  # newest first
    if limit > 0:
        result = result[:limit]
    return result


def read_events(
    project_root: Path,
    *,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Read events from audit-log.ndjson with optional filtering.

    Convenience wrapper: loads + filters in one call.
    For multiple queries, use load_all_events() + filter_events().
    """
    return filter_events(
        load_all_events(project_root),
        event_type=event_type,
        since=since,
        limit=limit,
    )


def _extract_timestamps(
    events: list[dict[str, Any]],
) -> list[datetime]:
    """Extract valid timestamps from events."""
    timestamps: list[datetime] = []
    for event in events:
        ts_str = event.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(
                ts_str.replace("Z", "+00:00"),
            )
            timestamps.append(ts)
        except (ValueError, AttributeError):
            continue
    return timestamps


def event_date_range_from(
    events: list[dict[str, Any]],
) -> tuple[datetime | None, datetime | None]:
    """Get date range from pre-loaded events (no I/O)."""
    timestamps = _extract_timestamps(events)
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def event_date_range(
    project_root: Path,
) -> tuple[datetime | None, datetime | None]:
    """Get the date range of events in the audit log."""
    return event_date_range_from(load_all_events(project_root))


def data_quality_from(
    events: list[dict[str, Any]],
) -> str:
    """Compute data quality level from pre-loaded events (no I/O).

    Returns:
        "HIGH" (>=500 events, >=60 days),
        "MEDIUM" (>=100, >=14 days), or "LOW".
    """
    total = len(events)
    oldest, newest = event_date_range_from(events)
    if oldest is None or newest is None:
        return "LOW"
    days = (newest - oldest).days
    if total >= 500 and days >= 60:
        return "HIGH"
    if total >= 100 and days >= 14:
        return "MEDIUM"
    return "LOW"


def data_quality_level(project_root: Path) -> str:
    """Compute data quality level for dashboard confidence."""
    return data_quality_from(load_all_events(project_root))


def count_events(
    project_root: Path,
    *,
    since: datetime | None = None,
) -> int:
    """Count total events in the audit log."""
    return len(read_events(project_root, since=since))


def gate_pass_rate_from(
    events: list[dict[str, Any]],
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Compute gate pass rate from pre-loaded events (no I/O)."""
    since = datetime.now(tz=UTC) - timedelta(days=days)
    gate_events = filter_events(
        events,
        event_type="gate_result",
        since=since,
    )
    total = len(gate_events)
    passed = sum(1 for e in gate_events if _detail_field(e, "result") == "pass")
    failed = total - passed

    check_failures: dict[str, int] = {}
    for event in gate_events:
        detail = event.get("detail")
        if isinstance(detail, dict):
            for name in detail.get("failed_checks", []):
                check_failures[name] = check_failures.get(name, 0) + 1

    most_failed = (
        max(check_failures, key=check_failures.get)  # type: ignore[arg-type]
        if check_failures
        else "none"
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": (round(passed / total * 100, 1) if total > 0 else 0.0),
        "most_failed_check": most_failed,
        "most_failed_count": check_failures.get(most_failed, 0),
    }


def gate_pass_rate(
    project_root: Path,
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Compute gate pass rate over the last N days."""
    return gate_pass_rate_from(
        load_all_events(project_root),
        days=days,
    )


def _detail_field(event: dict[str, Any], field: str) -> Any:
    """Extract a field from the detail dict of an event."""
    detail = event.get("detail")
    if isinstance(detail, dict):
        return detail.get(field)
    return None
