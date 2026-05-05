"""Migration runner with body-sha256 integrity gate (spec-122-b D-122-30).

The runner enumerates every ``NNNN_*.py`` file in this package, imports it,
and reads its ``BODY_SHA256`` constant + ``apply(conn)`` callable. The
constant is recorded into the ``_migrations`` ledger on first apply; on
subsequent boots, the file body is re-hashed and compared. Mismatches
emit ``framework_error`` events with ``error_code='migration_integrity_violation'``
and behave per the ``AIENG_HOOK_INTEGRITY_MODE`` env contract used by the
hook integrity manifest:

* ``enforce`` (default): raise :class:`MigrationIntegrityError`.
* ``warn``: log + emit telemetry, but proceed.
* ``off``: skip the check entirely.

Body sha256 protocol
--------------------
Migration files declare ``BODY_SHA256 = "<hex>"`` near the top. The hash
covers the file's UTF-8 body **with the BODY_SHA256 line stripped**, so
authors can update the constant in place without chasing their own tail.

Idempotency
-----------
``run_pending`` skips migrations whose ``id`` already appears in the
ledger. ``apply()`` callables themselves are also written to be idempotent
(``CREATE IF NOT EXISTS``, ``ON CONFLICT(...) DO NOTHING``) so partial
failures + reruns are safe.
"""

from __future__ import annotations

import hashlib
import importlib
import logging
import os
import re
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ``_BODY_SHA256_LINE_RE`` strips the constant-declaration line itself
# before hashing so the constant can be updated in place without recursive
# self-reference.
_BODY_SHA256_LINE_RE = re.compile(r"^\s*BODY_SHA256\s*=\s*[\"'][^\"']*[\"']\s*$", re.MULTILINE)

_MIGRATION_FILENAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.py$")

# Env var governing fail/warn/off behaviour. Mirrors
# ``AIENG_HOOK_INTEGRITY_MODE`` so operators have a single knob.
_INTEGRITY_ENV = "AIENG_HOOK_INTEGRITY_MODE"


class MigrationIntegrityError(RuntimeError):
    """Raised in ``enforce`` mode when a migration body sha256 mismatches."""

    def __init__(self, migration_id: str, expected: str, actual: str) -> None:
        super().__init__(
            f"migration body sha256 mismatch for {migration_id!r}: "
            f"recorded {expected!r}, computed {actual!r}"
        )
        self.migration_id = migration_id
        self.expected = expected
        self.actual = actual


def _integrity_mode() -> str:
    """Return the active integrity mode (``enforce``, ``warn``, or ``off``)."""
    return os.environ.get(_INTEGRITY_ENV, "enforce").strip().lower()


def _migrations_dir() -> Path:
    """Path to the migrations package directory."""
    return Path(__file__).resolve().parent


def _enumerate_migration_files() -> Iterator[tuple[str, Path]]:
    """Yield ``(migration_id, path)`` pairs in lexicographic order.

    Skips ``__init__.py`` and ``_runner.py`` and any file not matching
    ``NNNN_*.py``.
    """
    for entry in sorted(_migrations_dir().iterdir()):
        if not entry.is_file():
            continue
        match = _MIGRATION_FILENAME_RE.match(entry.name)
        if not match:
            continue
        # ``id`` is the full stem (e.g. ``0001_initial_schema``) so the
        # ledger remains human-readable.
        yield (entry.stem, entry)


def _hash_migration_body(path: Path) -> str:
    """Return sha256 hex of the migration body with the BODY_SHA256 line stripped."""
    raw = path.read_text(encoding="utf-8")
    stripped = _BODY_SHA256_LINE_RE.sub("", raw)
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def _load_module(path: Path):
    """Import a migration file by its stem under the migrations package."""
    module_name = f"ai_engineering.state.migrations.{path.stem}"
    return importlib.import_module(module_name)


def _ensure_ledger(conn: sqlite3.Connection) -> None:
    """Create the ``_migrations`` STRICT ledger if absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
          id          TEXT PRIMARY KEY,
          sha256      TEXT NOT NULL,
          applied_at  TEXT NOT NULL,
          applied_by  TEXT
        ) STRICT
        """
    )


def _ledger_lookup(conn: sqlite3.Connection, migration_id: str) -> str | None:
    """Return the recorded sha256 for ``migration_id`` or None."""
    row = conn.execute(
        "SELECT sha256 FROM _migrations WHERE id = ?",
        (migration_id,),
    ).fetchone()
    return row[0] if row else None


def _ledger_record(conn: sqlite3.Connection, migration_id: str, sha256: str) -> None:
    """Insert a fresh ledger row (idempotent via ON CONFLICT)."""
    conn.execute(
        """
        INSERT INTO _migrations (id, sha256, applied_at, applied_by)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (
            migration_id,
            sha256,
            datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            os.environ.get("USER") or os.environ.get("USERNAME") or "unknown",
        ),
    )


def _emit_integrity_violation(migration_id: str, expected: str, actual: str) -> None:
    """Emit a ``framework_error`` event for an integrity violation.

    Uses :mod:`ai_engineering.state.observability` if available; falls back
    to a stderr log line so this code path never crashes the migration
    runner.
    """
    try:  # pragma: no cover -- best-effort telemetry path
        from ai_engineering.state.observability import emit_framework_operation

        emit_framework_operation(
            Path.cwd(),
            operation="migration_integrity_check",
            component="state.migrations",
            outcome="failure",
            metadata={
                "error_code": "migration_integrity_violation",
                "migration_id": migration_id,
                "expected": expected,
                "actual": actual,
            },
        )
    except Exception as exc:  # pragma: no cover -- defensive
        logger.warning("could not emit migration_integrity_violation: %s", exc)


def _maybe_raise(migration_id: str, expected: str, actual: str) -> bool:
    """Apply the integrity-mode policy. Return True iff caller may proceed."""
    mode = _integrity_mode()
    if mode == "off":
        return True
    _emit_integrity_violation(migration_id, expected, actual)
    if mode == "warn":
        logger.warning(
            "migration body sha256 drift (warn mode): id=%s expected=%s actual=%s",
            migration_id,
            expected,
            actual,
        )
        return True
    # default + ``enforce`` => raise
    raise MigrationIntegrityError(migration_id, expected, actual)


def run_pending(conn: sqlite3.Connection) -> list[str]:
    """Apply all migrations not yet recorded in ``_migrations``.

    Returns the list of migration ids actually applied this run (in order).
    Always opens a fresh ``BEGIN`` per migration so a failure rolls back
    only the offending body, not previously-applied work.
    """
    _ensure_ledger(conn)
    applied: list[str] = []
    for migration_id, path in _enumerate_migration_files():
        recorded = _ledger_lookup(conn, migration_id)
        body_sha = _hash_migration_body(path)
        if recorded is not None:
            # Already applied -- enforce body sha256 matches the ledger.
            if recorded != body_sha:
                if not _maybe_raise(migration_id, recorded, body_sha):
                    continue
            continue
        # Pending migration. Verify the declared constant matches the
        # body sha256 the runner just computed; mismatch here means the
        # author edited the body but forgot to update BODY_SHA256.
        module = _load_module(path)
        declared = getattr(module, "BODY_SHA256", None)
        if declared is None:
            raise RuntimeError(f"migration {migration_id!r} is missing BODY_SHA256 constant")
        if declared != body_sha:
            if not _maybe_raise(migration_id, declared, body_sha):
                continue
        apply_callable = getattr(module, "apply", None)
        if not callable(apply_callable):
            raise RuntimeError(f"migration {migration_id!r} is missing apply(conn) callable")
        # Apply + record in a single in-process transaction so the ledger
        # row only lands when ``apply`` succeeds.
        try:
            conn.execute("BEGIN IMMEDIATE")
            apply_callable(conn)
            _ledger_record(conn, migration_id, body_sha)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied.append(migration_id)
    return applied


def verify_integrity(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Walk every applied migration and verify body sha256 stability.

    Returns a list of violation dicts; empty list means all good. In
    ``enforce`` mode, the first violation also raises.
    """
    _ensure_ledger(conn)
    violations: list[dict[str, Any]] = []
    for migration_id, path in _enumerate_migration_files():
        recorded = _ledger_lookup(conn, migration_id)
        if recorded is None:
            # Migration declared but never applied; skip integrity check.
            continue
        body_sha = _hash_migration_body(path)
        if recorded == body_sha:
            continue
        violations.append(
            {
                "migration_id": migration_id,
                "expected": recorded,
                "actual": body_sha,
            }
        )
        # ``_maybe_raise`` will emit telemetry + raise in enforce mode.
        if not _maybe_raise(migration_id, recorded, body_sha):
            # warn / off: continue to surface every violation.
            continue
    return violations


__all__ = [
    "MigrationIntegrityError",
    "run_pending",
    "verify_integrity",
]
