"""HOT-tier retention for state.db ``events`` (spec-123 D-123-26).

Retention ladder per D-123-26:

  HOT  (state.db ``events``)            90 days
  WARM (NDJSON archive plaintext)       12 months
  COLD (zstd archive)                   24 months
  PURGE                                 > 24 months

NDJSON is the immutable Article-III source-of-truth, so deleting from the
``events`` projection table is loss-free: the rows can be rebuilt from
the warm/cold archives at any time. The :func:`apply_hot_cutoff` helper
takes an open writer connection, deletes rows with ``ts_unix_ms < cutoff``
in a single transaction, and emits a ``framework_event`` of
``kind='retention_applied'`` so the audit chain captures the prune.

The module is a thin operational helper -- the caller (audit CLI verb,
scheduled job, install pipeline) owns transaction boundaries and event
emission cadence.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 90 days (D-123-26 HOT cutoff). Operators can override via the public
# ``days`` parameter for one-off larger sweeps.
DEFAULT_HOT_CUTOFF_DAYS = 90

_DAY_MS = 86_400_000


def _project_root_from_db(conn: sqlite3.Connection) -> Path | None:
    """Recover the project root from the writer's main DB path.

    Returns ``None`` for anonymous in-memory DBs (which is fine -- we
    skip the framework-event emit in that case so tests stay hermetic).
    """
    row = conn.execute("PRAGMA database_list").fetchone()
    if row is None or not row[2]:
        return None
    db_path = Path(row[2])
    # ``state.db`` lives at <root>/.ai-engineering/state/state.db.
    if db_path.parent.name != "state" or db_path.parent.parent.name != ".ai-engineering":
        return None
    return db_path.parent.parent.parent


def apply_hot_cutoff(
    conn: sqlite3.Connection,
    *,
    days: int = DEFAULT_HOT_CUTOFF_DAYS,
) -> dict[str, Any]:
    """Delete ``events`` older than ``now - days`` from the HOT projection.

    Args:
        conn: Open writer connection on ``state.db``. The caller owns
            the connection lifecycle; this helper does not commit/close.
        days: Cutoff window in days (default :data:`DEFAULT_HOT_CUTOFF_DAYS`).
            Must be positive.

    Returns:
        A dict carrying ``deleted`` (int), ``cutoff_days`` (int),
        ``cutoff_ts_unix_ms`` (int), and ``status`` (``'ok'`` |
        ``'noop'``).

    Raises:
        ValueError: when ``days`` is non-positive.
    """
    if days <= 0:
        raise ValueError(f"days must be positive, got {days!r}")

    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - days * _DAY_MS

    cur = conn.execute(
        "DELETE FROM events WHERE ts_unix_ms < ?",
        (cutoff_ms,),
    )
    deleted = int(cur.rowcount or 0)
    conn.commit()

    status = "ok" if deleted else "noop"
    payload: dict[str, Any] = {
        "status": status,
        "deleted": deleted,
        "cutoff_days": days,
        "cutoff_ts_unix_ms": cutoff_ms,
    }

    if deleted > 0:
        project_root = _project_root_from_db(conn)
        if project_root is not None:
            try:
                # Lazy import: keep the retention module light and avoid
                # circular imports through observability -> state_db.
                from ai_engineering.state.observability import (
                    append_framework_event,
                    build_framework_event,
                )

                event = build_framework_event(
                    project_root,
                    engine="ai_engineering",
                    kind="retention_applied",
                    component="state.retention",
                    source="audit-cli",
                    detail={
                        "operation": "apply_hot_cutoff",
                        "deleted": deleted,
                        "cutoff_days": days,
                        "cutoff_ts_unix_ms": cutoff_ms,
                        "tier": "hot",
                    },
                )
                append_framework_event(project_root, event)
            except Exception as exc:  # pragma: no cover -- defensive
                logger.warning("retention: failed to emit framework_event: %s", exc)

    return payload


__all__ = [
    "DEFAULT_HOT_CUTOFF_DAYS",
    "apply_hot_cutoff",
]
