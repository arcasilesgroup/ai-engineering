"""Policy decision log emitter (spec-122 Phase C, T-3.7).

Writes ``kind='policy_decision'`` events to
``.ai-engineering/state/framework-events.ndjson`` and (when present) to
the SQLite ``state.db.events`` projection landed by sub-002. The dual-
write is gated on capability detection so sub-003 ships without
sub-002.

Sample mask
-----------

Decision-log volume scales with hook invocation frequency, so we
record:

* 100% of ``outcome='blocked'`` rows -- never sampled, every deny is
  audit-load-bearing.
* ~10% of ``outcome='allow'`` rows -- deterministic sampling via
  ``sha256(correlation_id) % 10 == 0`` so retries with the same
  correlation id stay in/out together (no flap on a flaky retry).

Sensitive fields (``input.subject`` for commit policies and
``input.justification`` for risk-accept) are masked to a stable hash
prefix to preserve cardinality without leaking content.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_engineering.state.models import FrameworkEvent
from ai_engineering.state.observability import (
    append_framework_event,
)

__all__ = [
    "STATE_DB_REL",
    "emit_policy_decision",
    "should_sample",
]

STATE_DB_REL: Path = Path(".ai-engineering") / "state" / "state.db"

# Sensitive fields masked before persisting. Keys map to the input dict
# under `data.input`. Values are replaced with `sha256(value)[:12]`
# prefixed by `sha256:` so debuggers can see "this value is masked, here
# is its stable id" without seeing the value itself.
_SENSITIVE_INPUT_FIELDS: frozenset[str] = frozenset({"subject", "justification"})


def should_sample(correlation_id: str) -> bool:
    """Return True for ~10% of correlation ids deterministically.

    The sampling key is ``sha256(correlation_id) mod 10 == 0``.
    Same correlation id -> same answer, so a retried hook call is not
    flapped between sampled / not-sampled.
    """
    digest = hashlib.sha256(correlation_id.encode("utf-8")).digest()
    return digest[0] % 10 == 0


def _mask_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``payload`` with sensitive values hashed."""
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _SENSITIVE_INPUT_FIELDS and isinstance(value, str):
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
            masked[key] = f"sha256:{digest}"
        else:
            masked[key] = value
    return masked


def _events_table_present(db_path: Path) -> bool:
    """Probe the SQLite projection for the ``events`` table.

    Returns ``False`` on any error: missing file, locked database, missing
    table. The dual-write is best-effort; the NDJSON stream is the
    immutable source-of-truth.
    """
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(db_path, timeout=0.5)
    except sqlite3.Error:
        return False
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'",
        )
        row = cur.fetchone()
        return row is not None
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _project_name(project_root: Path) -> str:
    """Best-effort project name -- falls back to the directory name."""
    try:
        from ai_engineering.config.loader import load_manifest_config

        config = load_manifest_config(project_root)
        return config.name or project_root.name
    except Exception:
        return project_root.name


def _insert_events_row(
    db_path: Path,
    event: dict[str, Any],
) -> None:
    """Insert a row into the ``events`` table when present.

    The schema landed by sub-002 is a thin projection over the NDJSON
    stream. We aim at the columns the projection is documented to expose
    (``kind``, ``timestamp``, ``component``, ``outcome``,
    ``correlation_id``, ``project``, ``detail_json``); any column-set
    drift falls through to a no-op rather than raising.
    """
    detail_json = json.dumps(event.get("detail", {}), sort_keys=True)
    try:
        conn = sqlite3.connect(db_path, timeout=0.5)
    except sqlite3.Error:
        return
    try:
        try:
            conn.execute(
                """
                INSERT INTO events (
                    kind, timestamp, component, outcome, correlation_id,
                    project, detail_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["kind"],
                    event["timestamp"],
                    event["component"],
                    event["outcome"],
                    event["correlationId"],
                    event["project"],
                    detail_json,
                ),
            )
            conn.commit()
        except sqlite3.Error:
            # Schema drift / locked DB / missing column -> skip silently;
            # NDJSON is the source of truth.
            return
    finally:
        conn.close()


def emit_policy_decision(
    *,
    project_root: Path,
    policy: str,
    query: str,
    input_data: dict[str, Any],
    decision: str,
    deny_messages: list[str] | None = None,
    component: str = "policy-engine",
    source: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Emit a ``policy_decision`` event after an OPA evaluation.

    Parameters
    ----------
    project_root:
        Repository root (used to locate ``framework-events.ndjson`` and
        ``state.db``).
    policy:
        Short policy package name (``branch_protection``, ...).
    query:
        Full OPA query string (``data.<package>.<rule>``).
    input_data:
        The dict passed to ``opa eval --input``. Sensitive values are
        masked before persisting.
    decision:
        Either ``"allow"`` or ``"blocked"``. Anything else is normalised
        to ``"allow"`` (best-effort; we never silently log a deny as an
        allow).
    deny_messages:
        Deny strings extracted from the OPA result. Empty for allow
        decisions. Persisted under ``detail.deny_messages``.
    component:
        Logical component owning the call site. Defaults to
        ``"policy-engine"``; gates pass ``"gate-engine"`` and the
        risk-cmd surface passes ``"risk-cmd"``.
    source:
        Optional source label (e.g. ``"pre-commit"``, ``"pre-push"``).
    correlation_id:
        Optional pre-allocated correlation id; one is generated from
        ``uuid4`` when omitted.
    """
    outcome = "blocked" if decision == "blocked" else "allow"
    cid = correlation_id or uuid4().hex

    # Sample mask: 100% of blocks, ~10% of allows.
    if outcome == "allow" and not should_sample(cid):
        return

    deny = list(deny_messages or [])
    detail = {
        "policy": policy,
        "query": query,
        "input": _mask_input(input_data),
        "decision": outcome,
        "deny_messages": deny,
    }

    timestamp = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    project_name = _project_name(project_root)

    event = FrameworkEvent(
        engine="ai_engineering",
        kind="policy_decision",
        component=component,
        outcome=outcome,
        source=source,
        correlation_id=cid,
        project=project_name,
        detail=detail,
    )

    # NDJSON is always written -- immutable source of truth.
    try:
        append_framework_event(project_root, event)
    except Exception:
        # Audit emission must not raise on the hot path; the upstream
        # caller is the gate hook which has its own framework_error
        # surface for I/O failures.
        return

    # Optional dual-write to SQLite projection (sub-002).
    db_path = project_root / STATE_DB_REL
    if _events_table_present(db_path):
        wire = {
            "kind": "policy_decision",
            "timestamp": timestamp,
            "component": component,
            "outcome": outcome,
            "correlationId": cid,
            "project": project_name,
            "detail": detail,
        }
        _insert_events_row(db_path, wire)
