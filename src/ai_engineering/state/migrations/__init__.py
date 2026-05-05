"""Schema migration runner for state.db (spec-122-b D-122-17, D-122-30).

Public surface
--------------
* :func:`run_pending` -- apply all pending migrations in lexicographic
  order. Each migration's body sha256 is compared to the recorded
  ``BODY_SHA256`` constant; mismatch behaviour is gated by
  ``AIENG_HOOK_INTEGRITY_MODE``.
* :func:`verify_integrity` -- walk all already-applied migrations and
  verify their body sha256 against the ledger; same fail/warn/off
  semantics.

Migrations live in ``src/ai_engineering/state/migrations/NNNN_*.py`` and
must export both ``apply(conn: sqlite3.Connection) -> None`` and
``BODY_SHA256: str`` (hex sha256 of the file body, stripping the
``BODY_SHA256`` line itself before hashing).
"""

from __future__ import annotations

from ._runner import (
    MigrationIntegrityError,
    run_pending,
    verify_integrity,
)

__all__ = [
    "MigrationIntegrityError",
    "run_pending",
    "verify_integrity",
]
