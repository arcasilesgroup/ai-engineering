"""``TelemetryPort`` — audit-event emit / project / export.

Spec-120 audit observability lives behind this port. Application
layer code emits a structured event payload; the infra adapter
decides whether to append to NDJSON, project to SQLite, ship to
OTLP, or all three. Default consent posture is ``strict-opt-in``;
the no-op adapter is the default unless the operator enables an
exporter.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol


class TelemetryPort(Protocol):
    """Emit and query audit events."""

    def emit(self, event_type: str, payload: Mapping[str, object]) -> None:
        """Record an event. No exception is raised on disabled exporters."""
        ...

    def query(self, sql: str) -> Iterable[Mapping[str, object]]:
        """Read-only SQL over the projected audit index (spec-120)."""
        ...
