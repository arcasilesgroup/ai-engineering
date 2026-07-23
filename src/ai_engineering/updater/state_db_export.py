"""spec-148 P5: one-shot ``state.db`` → files export migration.

This is the SOLE sanctioned ``sqlite3`` reader in the package (``ai-eng
update`` calls it; ``tests/architecture/test_no_sqlite.py`` exempts this
module by path). It ingests a legacy ``state.db`` (a pre-spec-148 install)
into the canonical file stores, VERIFIES the export, then DELETES
``state.db`` (+ its WAL/SHM siblings).

Contract (D-148-09):

* No-op when ``state.db`` is absent (idempotent).
* Exports ``install_state`` → ``install-state.json``, ``decisions`` →
  ``decision-store.json``, ``ownership_map`` → ``ownership-map.json`` — but
  only when the file home is ABSENT, so a newer file is never clobbered by
  the stale DB.
* ``tool_capabilities`` is NOT exported — ``framework-capabilities.json`` is
  rebuilt on demand. ``events`` already live in ``framework-events.ndjson``.
* No backup (no ``.bak``): the fail-loud verify gate is the safety net —
  ``state.db`` is never deleted unless every export verifies present.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_STATE_REL = Path(".ai-engineering") / "state"
_DB_NAME = "state.db"
_INSTALL_STATE = "install-state.json"
_DECISION_STORE = "decision-store.json"
_OWNERSHIP_MAP = "ownership-map.json"


def _state_dir(project_root: Path) -> Path:
    return project_root / _STATE_REL


def state_db_path(project_root: Path) -> Path:
    """Return the legacy ``state.db`` path under *project_root*."""
    return _state_dir(project_root) / _DB_NAME


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    """Run *sql* and return rows as dicts; an absent table yields ``[]``."""
    try:
        cursor = conn.execute(sql)
    except sqlite3.OperationalError:
        return []
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def _export_install_state(conn: sqlite3.Connection, state_dir: Path) -> None:
    """Export the ``install_state`` singleton row → install-state.json."""
    if (state_dir / _INSTALL_STATE).exists():
        return
    rows = _read_rows(conn, "SELECT state_json FROM install_state WHERE id = 1")
    if not rows or not rows[0].get("state_json"):
        return
    from ai_engineering.state.service import save_install_state
    from skill_domain.state_models import InstallState

    payload = json.loads(rows[0]["state_json"])
    save_install_state(state_dir, InstallState.model_validate(payload))


def _export_decisions(conn: sqlite3.Connection, project_root: Path, state_dir: Path) -> None:
    """Export the ``decisions`` table → decision-store.json."""
    if (state_dir / _DECISION_STORE).exists():
        return
    rows = _read_rows(
        conn,
        "SELECT decision_id, spec_id, status, title, rationale, context, consequences, "
        "superseded_by, expires_at, details_json, created_at FROM decisions ORDER BY decision_id",
    )
    if not rows:
        return
    from ai_engineering.state.defaults import default_decision_store
    from ai_engineering.state.repository import DurableStateRepository
    from skill_domain.state_models import Decision

    decisions: list[Decision] = []
    for row in rows:
        payload = row.get("details_json")
        if payload:
            try:
                decisions.append(Decision.model_validate_json(payload))
                continue
            except (ValueError, json.JSONDecodeError):
                pass
        try:
            decisions.append(
                Decision.model_validate(
                    {
                        "id": row["decision_id"],
                        "context": row.get("context") or "",
                        "decision": row.get("title") or "",
                        "decidedAt": row.get("created_at") or _now_iso(),
                        "spec": row.get("spec_id") or "",
                        "status": row.get("status") or "active",
                        "expiresAt": row.get("expires_at"),
                        "title": row.get("title") or "",
                        "rationale": row.get("rationale"),
                        "consequences": row.get("consequences"),
                        "superseded_by": row.get("superseded_by"),
                    }
                )
            )
        except (ValueError, TypeError):
            continue

    store = default_decision_store()
    store.decisions = decisions
    DurableStateRepository(project_root).save_decisions(store)


def _ownership_level(value: str | None) -> Any:
    from skill_domain.state_models import OwnershipLevel

    try:
        return OwnershipLevel(value or "")
    except ValueError:
        return OwnershipLevel.TEAM_MANAGED


def _framework_update_policy(value: str | None) -> Any:
    from skill_domain.state_models import FrameworkUpdatePolicy

    try:
        return FrameworkUpdatePolicy(value or "")
    except ValueError:
        return FrameworkUpdatePolicy.DENY


def _export_ownership(conn: sqlite3.Connection, project_root: Path, state_dir: Path) -> None:
    """Export the ``ownership_map`` table → ownership-map.json (collapsed model)."""
    if (state_dir / _OWNERSHIP_MAP).exists():
        return
    rows = _read_rows(
        conn,
        "SELECT path_pattern, owners_json, severity FROM ownership_map ORDER BY rowid",
    )
    if not rows:
        return
    from ai_engineering.state.repository import DurableStateRepository
    from skill_domain.state_models import OwnershipEntry, OwnershipMap

    entries: list[OwnershipEntry] = []
    for row in rows:
        pattern = row.get("path_pattern")
        if not isinstance(pattern, str) or not pattern:
            continue
        owners_raw = row.get("owners_json")
        owners = json.loads(owners_raw) if owners_raw else []
        first = owners[0] if isinstance(owners, list) and owners else None
        first_owner = first if isinstance(first, str) else None
        severity = row.get("severity")
        entries.append(
            OwnershipEntry.model_validate(
                {
                    "pattern": pattern,
                    "owner": _ownership_level(first_owner),
                    "framework_update": _framework_update_policy(
                        severity if isinstance(severity, str) else None
                    ),
                }
            )
        )
    DurableStateRepository(project_root).save_ownership(OwnershipMap(paths=entries))


def _verify_export(project_root: Path, state_dir: Path, *, had_rows: dict[str, bool]) -> bool:
    """Re-read the exported files; return False if any expected export is missing."""
    from ai_engineering.state.service import load_install_state

    try:
        load_install_state(state_dir)
    except (OSError, ValueError):
        return False
    if had_rows.get("install_state") and not (state_dir / _INSTALL_STATE).exists():
        return False
    if had_rows.get("decisions") and not (state_dir / _DECISION_STORE).exists():
        return False
    ownership_missing = (
        bool(had_rows.get("ownership_map")) and not (state_dir / _OWNERSHIP_MAP).exists()
    )
    return not ownership_missing


def migrate_state_db_to_files(project_root: Path) -> dict[str, Any]:
    """Export → verify → delete the legacy ``state.db``.

    Returns ``{"status": "noop"}`` when ``state.db`` is absent, or
    ``{"status": "migrated", ...}`` after a verified export + delete. Raises
    :class:`RuntimeError` (without deleting) when verification fails.
    """
    db = state_db_path(project_root)
    if not db.exists():
        return {"status": "noop"}

    state_dir = _state_dir(project_root)
    conn = sqlite3.connect(db)
    try:
        had_rows = {
            "install_state": bool(_read_rows(conn, "SELECT 1 FROM install_state WHERE id = 1")),
            "decisions": bool(_read_rows(conn, "SELECT 1 FROM decisions LIMIT 1")),
            "ownership_map": bool(_read_rows(conn, "SELECT 1 FROM ownership_map LIMIT 1")),
        }
        _export_install_state(conn, state_dir)
        _export_decisions(conn, project_root, state_dir)
        _export_ownership(conn, project_root, state_dir)
    finally:
        conn.close()

    if not _verify_export(project_root, state_dir, had_rows=had_rows):
        raise RuntimeError(
            "state.db export verification failed; state.db was NOT deleted (fail-loud)"
        )

    for name in (_DB_NAME, f"{_DB_NAME}-wal", f"{_DB_NAME}-shm"):
        (state_dir / name).unlink(missing_ok=True)

    return {"status": "migrated", "exported": [k for k, v in had_rows.items() if v]}


__all__ = ["migrate_state_db_to_files", "state_db_path"]
