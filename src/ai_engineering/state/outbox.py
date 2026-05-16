"""Transactional outbox for state.db projection mutations (D-122-18).

Pattern (Microservices.io transactional-outbox + at-least-once emit):

1. Open ``BEGIN IMMEDIATE`` on state.db.
2. Caller executes its projection-write SQL inside the transaction.
3. Caller buffers the framework event payload via :meth:`OutboxRecorder.queue`.
4. On clean exit, the SQL commits; **after** commit, queued events are
   appended to ``framework-events.ndjson``.
5. If the SQL fails mid-context, the rollback discards the SQL changes
   AND the buffered events (no NDJSON emit).
6. If the SQL commits but the NDJSON emit later fails, the row stays
   committed (Article-III says NDJSON is the SoT, so we surface the
   error to the caller -- the buffered events can be retried).

D-122-18 in this repo treats the in-process queue as sufficient (single-
binary CLI; no cross-process workers). The DB-backed _outbox table
alternative is deferred for future scale per the spec ``confidence`` block.
"""

from __future__ import annotations

import contextlib
import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ai_engineering.state.state_db import connect

logger = logging.getLogger(__name__)

# Thread-local re-entry guard. Calling ``projection_write`` inside another
# active ``projection_write`` is almost always a programmer error (it
# silently nests transactions which BEGIN IMMEDIATE doesn't actually
# nest). We surface the bug rather than papering over it.
_LOCAL = threading.local()


class OutboxReentrantError(RuntimeError):
    """Raised when ``projection_write`` is called inside another active call."""


class OutboxRecorder:
    """Buffer for events that should be emitted after the SQL commit."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._queue: list[tuple[str, dict[str, Any]]] = []

    def queue(self, kind: str, payload: dict[str, Any]) -> None:
        """Buffer a ``(kind, payload)`` event for post-commit emit."""
        self._queue.append((kind, payload))

    def drain(self, *, emitter: Callable[[Path, str, dict[str, Any]], None]) -> int:
        """Emit all buffered events. Returns the count emitted.

        Each emit is independent: a failure on one does not skip the rest.
        Failures are surfaced as the first exception encountered. Callers
        own retry semantics.
        """
        emitted = 0
        first_exc: Exception | None = None
        for kind, payload in self._queue:
            try:
                emitter(self._project_root, kind, payload)
                emitted += 1
            except Exception as exc:
                logger.warning("outbox emit failed kind=%s: %s", kind, exc)
                if first_exc is None:
                    first_exc = exc
        self._queue.clear()
        if first_exc is not None:
            raise first_exc
        return emitted


def _default_emitter(project_root: Path, kind: str, payload: dict[str, Any]) -> None:
    """Default emit path -- call into observability.emit_framework_operation."""
    # Lazy import to keep this module light at import time.
    from ai_engineering.state.observability import emit_framework_operation

    component = (
        payload.pop("component", "state.outbox") if isinstance(payload, dict) else "state.outbox"
    )
    operation = payload.pop("operation", kind) if isinstance(payload, dict) else kind
    outcome = payload.pop("outcome", "success") if isinstance(payload, dict) else "success"
    emit_framework_operation(
        project_root,
        operation=operation,
        component=component,
        outcome=outcome,
        metadata=payload if isinstance(payload, dict) else {"value": payload},
    )


@contextmanager
def projection_write(
    project_root: Path,
    *,
    emitter: Callable[[Path, str, dict[str, Any]], None] | None = None,
) -> Iterator[tuple[sqlite3.Connection, OutboxRecorder]]:
    """Open a writer connection + outbox recorder under a single transaction.

    On clean exit:
      1. ``COMMIT`` the SQL.
      2. Drain the buffered events via the emitter.
    On exception inside the ``with`` body:
      1. ``ROLLBACK`` the SQL.
      2. Discard the buffered events.
    Re-entry on the same thread raises :class:`OutboxReentrantError` so
    bugs surface loudly instead of nesting BEGINs.
    """
    if getattr(_LOCAL, "active", False):
        raise OutboxReentrantError(
            "projection_write() called inside another active projection_write(); "
            "consolidate the writes into a single transaction"
        )
    _LOCAL.active = True
    conn = connect(project_root, read_only=False, apply_migrations=False)
    recorder = OutboxRecorder(project_root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield (conn, recorder)
            conn.commit()
        except Exception:
            conn.rollback()
            recorder._queue.clear()
            raise
        # Post-commit: drain events. If this fails the SQL is still
        # committed (NDJSON is at-least-once after a successful commit).
        chosen_emitter = emitter or _default_emitter
        recorder.drain(emitter=chosen_emitter)
    finally:
        with contextlib.suppress(Exception):
            conn.close()
        _LOCAL.active = False


__all__ = [
    "OutboxRecorder",
    "OutboxReentrantError",
    "projection_write",
]
