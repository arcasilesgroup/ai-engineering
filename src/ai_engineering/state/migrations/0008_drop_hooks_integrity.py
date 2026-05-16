"""Drop the ``hooks_integrity`` table (spec-138 M5.T1, D-138-01).

Rationale
---------
The ``hooks_integrity`` table was declared by ``0001_initial_schema`` as a
"verification ledger populated at runtime by ``run_hook_safe``", but no
consumer ever materialised:

* :file:`.ai-engineering/state/hooks-manifest.json` carries the sha256
  source of truth for every registered hook script.
* :file:`.ai-engineering/state/framework-events.ndjson` carries the
  ``integrity_violation`` event stream (mirrored via
  ``state.db.events`` after the SessionEnd rebuild added in spec-138 M4).

The intended dual-write to ``hooks_integrity`` never landed, and per
SSOT-PD (CONSTITUTION.md Prohibition #8 added in spec-138 M2) every
datum has exactly one canonical writable store. The manifest + NDJSON
already cover the surface; the table is dead schema.

D-138-01 ratifies the drop: hard delete, no shim, the table is removed
from every fresh DB on the next bootstrap.

Idempotent contract
-------------------
``DROP TABLE IF EXISTS`` and ``DROP INDEX IF EXISTS`` make this migration
safe to re-run on a fresh DB (where the table never existed) and on an
existing DB (where ``0001_initial_schema`` had already created it).
"""

from __future__ import annotations

import sqlite3

BODY_SHA256 = "deab195b0abd517f25b08e5811028201b5c67bcd486a3d6de4323bc62457b9a0"


def apply(conn: sqlite3.Connection) -> None:
    """Drop ``hooks_integrity`` and its index.

    The index ``idx_hooks_recent`` was declared alongside the table in
    ``0001_initial_schema``. ``DROP TABLE`` removes both the table and
    any indexes built on it; the explicit ``DROP INDEX`` is a belt-and-
    braces guard in case a future migration recreated the index without
    the table.
    """
    cur = conn.cursor()
    cur.execute("DROP INDEX IF EXISTS idx_hooks_recent")
    cur.execute("DROP TABLE IF EXISTS hooks_integrity")


__all__ = ["BODY_SHA256", "apply"]
