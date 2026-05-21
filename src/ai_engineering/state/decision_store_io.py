"""spec-148 P2: file-backed decision-store row adapter.

`decision-store.json` is the single source of truth for governance
decisions (and risk acceptances, which are decision records). This module
replaces the retired SQLite ``decisions`` table helpers
(``state_db.list_decisions`` / ``state_db.upsert_decision_rows_raw``) used
by the row-oriented CLI surfaces (``ai-eng decision record/list/backfill``)
and by ``brainstorm.spec_approval``.

The CLI vocabulary is a flat row dict
(``decision_id``/``spec_id``/``status``/``title``/``rationale``/``context``/
``consequences``/``superseded_by``/``expires_at``); the canonical store holds
:class:`~ai_engineering.state.models.Decision` models. The row-only fields
(``rationale``/``consequences``/``superseded_by``/``title``/``updated_at``)
have no first-class ``Decision`` field, so they ride as ledger extras —
``Decision`` is declared ``extra="allow"`` and preserves them verbatim across
load/save round-trips.

All reads and writes funnel through
:class:`~ai_engineering.state.repository.DurableStateRepository` so there is
exactly one accessor for the file.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_engineering.state.models import Decision

if TYPE_CHECKING:
    from ai_engineering.state.repository import DurableStateRepository


def _repository(project_root: Path) -> DurableStateRepository:
    """Return the durable-state repository (single decision-store accessor)."""
    # Lazy import: repository pulls in install-state helpers at module scope.
    from ai_engineering.state.repository import DurableStateRepository

    return DurableStateRepository(project_root)


def decision_store_path(project_root: Path) -> Path:
    """Return the canonical ``decision-store.json`` path."""
    return _repository(project_root).decision_store_path


def _now_iso() -> str:
    """Return an ISO-8601 UTC timestamp (``...Z``), seconds precision."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _iso(value: Any) -> str | None:
    """Render a datetime/str timestamp to ISO, or ``None``."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_from_decision(decision: Decision) -> dict[str, str | None]:
    """Project a :class:`Decision` back into the flat CLI row vocabulary."""
    extra = decision.__pydantic_extra__ or {}
    status = decision.status
    status_value = status.value if hasattr(status, "value") else str(status)
    decided_iso = _iso(decision.decided_at)
    return {
        "decision_id": decision.id,
        "spec_id": decision.spec or "",
        "status": status_value,
        "title": extra.get("title") or decision.decision or "",
        "rationale": extra.get("rationale"),
        "context": decision.context,
        "consequences": extra.get("consequences"),
        "superseded_by": extra.get("superseded_by"),
        "expires_at": _iso(decision.expires_at),
        "created_at": decided_iso,
        "updated_at": extra.get("updated_at") or decided_iso,
    }


def _decision_from_row(row: dict[str, str | None], *, prev: Decision | None) -> Decision:
    """Build a :class:`Decision` from a CLI row, preserving extras.

    On an UPSERT into an existing id (*prev* set) the original
    ``decided_at`` is kept so re-records do not rewrite the creation
    timestamp (parity with the SQL ``created_at`` preservation).
    """
    now = _now_iso()
    decided_at = row.get("created_at") or (_iso(prev.decided_at) if prev else now)
    payload: dict[str, Any] = {
        "id": row.get("decision_id"),
        "spec": row.get("spec_id") or "",
        "decision": row.get("title") or "",
        "context": row.get("context") or "",
        "status": row.get("status") or "active",
        "decidedAt": decided_at,
        "expiresAt": row.get("expires_at"),
        # Ledger extras (extra="allow"): row-only fields with no model field.
        "title": row.get("title") or "",
        "rationale": row.get("rationale"),
        "consequences": row.get("consequences"),
        "superseded_by": row.get("superseded_by"),
        "updated_at": now,
    }
    return Decision.model_validate(payload)


def list_decision_rows(
    project_root: Path, *, status: str | None = None
) -> list[dict[str, str | None]]:
    """List decisions as CLI row dicts, ``decision_id`` ASC.

    Mirrors the retired ``state_db.list_decisions``: an optional ``status``
    filter, ascending ``decision_id`` order, and an empty list when the
    store is absent.
    """
    store = _repository(project_root).load_decisions()
    rows = [_row_from_decision(d) for d in store.decisions]
    if status is not None:
        rows = [row for row in rows if row.get("status") == status]
    rows.sort(key=lambda row: row.get("decision_id") or "")
    return rows


def upsert_decision_rows_raw(project_root: Path, rows: list[dict[str, str | None]]) -> int:
    """UPSERT CLI row dicts into ``decision-store.json`` (merge by ``decision_id``).

    Returns the count of rows attempted (rows lacking ``decision_id`` are
    skipped). An empty input ensures the store file exists and returns 0,
    matching the retired ``state_db.upsert_decision_rows_raw`` contract.
    """
    repo = _repository(project_root)
    store = repo.load_decisions()
    if not rows:
        repo.save_decisions(store)
        return 0

    by_id: dict[str, Decision] = {d.id: d for d in store.decisions}
    attempted = 0
    for row in rows:
        decision_id = row.get("decision_id")
        if not decision_id:
            continue
        by_id[decision_id] = _decision_from_row(row, prev=by_id.get(decision_id))
        attempted += 1

    store.decisions = list(by_id.values())
    repo.save_decisions(store)
    return attempted


__all__ = [
    "decision_store_path",
    "list_decision_rows",
    "upsert_decision_rows_raw",
]
