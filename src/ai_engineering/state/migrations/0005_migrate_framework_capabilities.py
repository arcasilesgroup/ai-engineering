"""Migrate framework-capabilities.json to the tool_capabilities table (spec-125 T-1.11).

Creates a STRICT singleton table keyed by ``id = 1`` that stores the
canonical :class:`ai_engineering.state.models.FrameworkCapabilitiesCatalog`
payload as JSON in the ``catalog_json`` column. Frequently-queried
scalar fields (``schema_version``, ``generated_at``, ``agents_count``,
``skills_count``, ``capability_cards_count``) are mirrored as columns
for indexing without requiring SQLite JSON1.

Idempotent contract
-------------------
* ``CREATE TABLE IF NOT EXISTS`` ensures schema creation is safe to
  re-run.
* The singleton row uses ``INSERT INTO tool_capabilities (id, ...)
  VALUES (1, ...) ON CONFLICT(id) DO UPDATE`` so re-applying the
  migration with the same source JSON yields exactly one row.
* When ``framework-capabilities.json`` is absent, a default
  ``FrameworkCapabilitiesCatalog`` is ingested so downstream readers
  always find a valid singleton row.

Source-JSON contract
--------------------
* When ``framework-capabilities.json`` is missing, the migration
  writes a fresh ``FrameworkCapabilitiesCatalog()`` payload.
* When the JSON exists and is structurally valid (a dict), we ingest
  it as-is into the ``catalog_json`` column. Validation against the
  canonical Pydantic model happens at read time so the migration stays
  schema-tolerant during the cutover.

Per spec-125 D-125-02, the JSON file is **left in place** by this
migration. Deletion is the responsibility of T-1.21 once the readers
are refactored and verification passes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

BODY_SHA256 = "5e93391a980fcf95dd403ae10685581fc250f2437267799a04ed9eddd81f0db1"

_STATE_REL = Path(".ai-engineering") / "state"
_CAPABILITIES_FILENAME = "framework-capabilities.json"


def _now_iso() -> str:
    """Return an ISO-8601 UTC timestamp suitable for the updated_at column."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _project_root_from_db(conn: sqlite3.Connection) -> Path:
    """Recover the project root from the connection's main DB path.

    state.db lives at ``<root>/.ai-engineering/state/state.db``; walking
    three parents up yields the project root. Falls back to ``cwd``
    when the connection is in-memory.
    """
    row = conn.execute("PRAGMA database_list").fetchone()
    if row is None or not row[2]:
        return Path.cwd()
    db_path = Path(row[2])
    return db_path.parent.parent.parent


def _load_capabilities_payload(state_dir: Path) -> dict:
    """Return the framework-capabilities payload.

    Resolution order:
    1. Legacy JSON snapshot at ``framework-capabilities.json`` (kept
       for the spec-125 cutover window; ingested as-is when present).
    2. Live computation from the project's manifest + skills/agents on
       disk via :func:`build_framework_capabilities`. This keeps
       ``tool_capabilities`` in sync with manifest changes — without
       it the validator's ``framework-capabilities-snapshot`` check
       drifts on every CI run that builds state.db fresh.
    3. Empty :class:`FrameworkCapabilitiesCatalog` fallback only when
       the live computation cannot resolve the project root.
    """
    from ai_engineering.state.models import FrameworkCapabilitiesCatalog

    path = state_dir / _CAPABILITIES_FILENAME
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass

    # Live build: state_dir is `<root>/.ai-engineering/state`; the
    # project root is two parents up.
    project_root = state_dir.parent.parent
    try:
        from ai_engineering.state.observability import build_framework_capabilities

        catalog = build_framework_capabilities(project_root)
        return catalog.model_dump(mode="json", by_alias=True)
    except Exception:
        # Defensive: never let a build failure abort the migration. The
        # validator will surface the empty catalog as a separate finding
        # via ``framework-capabilities-snapshot`` so the issue is visible.
        return FrameworkCapabilitiesCatalog().model_dump(mode="json", by_alias=True)


def _ingest_payload(conn: sqlite3.Connection, payload: dict) -> None:
    """UPSERT the singleton tool_capabilities row from *payload*."""
    schema_version = str(payload.get("schemaVersion", payload.get("schema_version", "1.0")))
    generated_at = payload.get("generatedAt", payload.get("generated_at", ""))
    if not isinstance(generated_at, str):
        generated_at = str(generated_at)

    agents = payload.get("agents") or []
    skills = payload.get("skills") or []
    capability_cards = payload.get("capabilityCards") or payload.get("capability_cards") or []

    agents_count = len(agents) if isinstance(agents, list) else 0
    skills_count = len(skills) if isinstance(skills, list) else 0
    cards_count = len(capability_cards) if isinstance(capability_cards, list) else 0

    catalog_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    updated_at = _now_iso()

    conn.execute(
        """
        INSERT INTO tool_capabilities
          (id, schema_version, generated_at, agents_count,
           skills_count, capability_cards_count, catalog_json, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          schema_version          = excluded.schema_version,
          generated_at            = excluded.generated_at,
          agents_count            = excluded.agents_count,
          skills_count            = excluded.skills_count,
          capability_cards_count  = excluded.capability_cards_count,
          catalog_json            = excluded.catalog_json,
          updated_at              = excluded.updated_at
        """,
        (
            schema_version,
            generated_at,
            agents_count,
            skills_count,
            cards_count,
            catalog_json,
            updated_at,
        ),
    )


def apply(conn: sqlite3.Connection) -> None:
    """Create the tool_capabilities table and seed the singleton row."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_capabilities (
          id                       INTEGER PRIMARY KEY CHECK (id = 1),
          schema_version           TEXT NOT NULL,
          generated_at             TEXT NOT NULL,
          agents_count             INTEGER NOT NULL,
          skills_count             INTEGER NOT NULL,
          capability_cards_count   INTEGER NOT NULL,
          catalog_json             TEXT NOT NULL,
          updated_at               TEXT NOT NULL
        ) STRICT
        """
    )

    project_root = _project_root_from_db(conn)
    state_dir = project_root / _STATE_REL
    payload = _load_capabilities_payload(state_dir)
    _ingest_payload(conn, payload)


__all__ = ["BODY_SHA256", "apply"]
