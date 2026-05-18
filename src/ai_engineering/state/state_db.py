"""Unified ``state.db`` connection manager (spec-122-b D-122-06, D-122-16).

The framework's persistence is consolidated into a single SQLite database at
``.ai-engineering/state/state.db``. Six STRICT tables (events, decisions,
risk_acceptances, gate_findings, ownership_map, install_steps) plus a
``_migrations`` ledger live here (the legacy ``hooks_integrity`` table was
dropped in migration 0008 per spec-138 D-138-01). The NDJSON
``framework-events.ndjson`` file remains the immutable Article-III
source-of-truth (CQRS read-model split); this DB is a derived projection
that can be rebuilt by replay.

Key contract
------------
* ``connect(project_root, *, read_only=False)`` -- opens (or creates) the
  database with the nine PRAGMAs listed in D-122-16. ``auto_vacuum`` is
  set to ``INCREMENTAL`` (mode 2) only on first creation; subsequent
  connects leave it alone (PRAGMA writes for ``auto_vacuum`` after the
  first page is written are silently ignored, but we explicitly skip
  the no-op for clarity).
* ``projection_write(project_root)`` -- context manager wrapping a
  ``BEGIN IMMEDIATE`` transaction. Commits on clean exit, rolls back
  on exception. Use this for any state-mutating CLI flow.

PRAGMA list (D-122-16)
----------------------
| PRAGMA              | Value      | Rationale                              |
|---------------------|------------|----------------------------------------|
| journal_mode        | WAL        | Concurrent reads + crash-safe writes   |
| synchronous         | NORMAL     | Durable across power loss with WAL     |
| foreign_keys        | ON         | Enforce referential integrity          |
| busy_timeout        | 10000 (ms) | Tolerate ~10s of contention            |
| cache_size          | -65536     | 64 MB negative = KiB                   |
| temp_store          | MEMORY     | RAM-only temp tables                   |
| mmap_size           | 268435456  | 256 MB memory-mapped I/O               |
| auto_vacuum         | INCREMENTAL| Reclaim space without rebuild          |
| journal_size_limit  | 67108864   | 64 MB cap on WAL                       |
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_logger = logging.getLogger(__name__)

# Canonical relative path. Callers compose with their ``project_root``.
STATE_DB_REL = Path(".ai-engineering") / "state" / "state.db"

# spec-124 D-124-12 + spec-125 D-125-03: JSON state files migrated to
# state.db. Their presence on disk indicates either a pre-spec-125
# install or a manual write that bypasses the canonical projection. The
# startup assertion warns when we detect lingering fallbacks so
# operators can replay or remove them before the next migration cycle.
#
# NOTE: ``gate-findings.json`` is intentionally EXCLUDED from this list.
# The dual-emit document is the canonical sibling artifact per spec-104
# D-104-06 (consumed by ``/ai-commit`` and ``/ai-pr``); the state.db
# ``gate_findings`` table is a structural placeholder only (audit-cmd
# integrity check) and is never read by the orchestrator. Treating the
# file as deprecated produced false-positive warnings on every CLI run.
_DEPRECATED_JSON_FALLBACKS = (
    "decision-store.json",
    "ownership-map.json",
    "install-state.json",
    "framework-capabilities.json",
)

# spec-132 D-132-07: dedup the deprecated-JSON warning so a single
# ``ai-eng install`` does not emit ~34 duplicate lines per stale file.
# Keyed on the absolute (state_dir / filename) Path so two different
# project roots each get their own one-shot warning.
_WARNED_FALLBACKS: set[Path] = set()


def _reset_fallback_warnings() -> None:
    """Clear the dedup set so subsequent calls re-emit warnings.

    Test hook -- callers in production never need this, but the unit
    suite for D-132-07 must exercise both the deduped path and the
    re-emit path. Keeping the helper public-but-underscored mirrors the
    rest of the test-only surface in ``state_db``.
    """
    _WARNED_FALLBACKS.clear()


def state_db_path(project_root: Path) -> Path:
    """Return the absolute ``state.db`` path under ``project_root``."""
    return project_root / STATE_DB_REL


def _apply_pragmas(conn: sqlite3.Connection, *, fresh_db: bool) -> None:
    """Apply the D-122-16 PRAGMA suite. Some are one-shot (auto_vacuum)."""
    cur = conn.cursor()
    # ``auto_vacuum`` only takes effect on a fresh DB (before the first
    # page is written). We set it before any other writes happen.
    if fresh_db:
        cur.execute("PRAGMA auto_vacuum = INCREMENTAL")
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA busy_timeout = 10000")
    cur.execute("PRAGMA cache_size = -65536")
    cur.execute("PRAGMA temp_store = MEMORY")
    cur.execute("PRAGMA mmap_size = 268435456")
    cur.execute("PRAGMA journal_size_limit = 67108864")


def _is_bootstrapped(conn: sqlite3.Connection) -> bool:
    """Return ``True`` when ``state.db`` already carries the migration ledger.

    Idempotency hinges on detecting whether a previous boot already ran
    the migration runner. We check for the ``_migrations`` ledger table
    (created by :func:`ai_engineering.state.migrations._runner._ensure_ledger`)
    rather than any business table so the check stays decoupled from the
    specific schema migrations (additions and re-orderings of business
    tables remain safe).
    """
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='_migrations' LIMIT 1"
    )
    return cur.fetchone() is not None


def connect(
    project_root: Path,
    *,
    read_only: bool = False,
    apply_migrations: bool | None = None,
) -> sqlite3.Connection:
    """Open a connection to ``state.db`` with the D-122-16 PRAGMA suite.

    Lazy bootstrap (spec-123 D-123-13)
    ----------------------------------
    On the first writer call against a missing or empty ``state.db``, the
    connection helper transparently runs the migration runner so the
    seven STRICT business tables, the ``_migrations`` ledger, and the
    NDJSON replay all land before the connection is returned. Subsequent
    calls observe the ledger and skip the runner.

    Args:
        project_root: Project root holding ``.ai-engineering/``.
        read_only: When ``True``, opens the DB via ``mode=ro`` URI so
            concurrent writers cannot accidentally corrupt the read side.
            Read-only mode never triggers the bootstrap; callers expect
            an existing DB.
        apply_migrations: Force-on (``True``) or force-off (``False``) the
            migration runner. Default ``None`` opts into the lazy
            bootstrap: run migrations only when the ledger is missing.

    Returns:
        A configured :class:`sqlite3.Connection`.
    """
    db_path = state_db_path(project_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Treat both 'file missing' and 'file present but 0 bytes' (e.g.
    # touched-by-installer placeholder) as 'fresh DB' so the bootstrap
    # branch fires and PRAGMA auto_vacuum can still take effect before
    # the first write.
    fresh_db = (not db_path.exists()) or db_path.stat().st_size == 0

    if read_only:
        # Use URI form so SQLite honours the read-only flag. Read-only
        # callers never bootstrap; they expect an existing DB.
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    else:
        conn = sqlite3.connect(db_path, timeout=10.0)

    _apply_pragmas(conn, fresh_db=fresh_db and not read_only)
    conn.row_factory = sqlite3.Row

    if read_only:
        return conn

    # Decide whether to invoke the migration runner.
    #
    # * ``apply_migrations=True``  -> always run (legacy callers).
    # * ``apply_migrations=False`` -> never run (tests / explicit skip).
    # * ``apply_migrations=None``  -> lazy: run iff ledger missing.
    should_run = not _is_bootstrapped(conn) if apply_migrations is None else bool(apply_migrations)

    if should_run:
        from ai_engineering.state.migrations import run_pending

        run_pending(conn)

    # spec-124 D-124-12: warn (not block) when deprecated JSON
    # fallbacks reappear post-migration. Source-of-truth is state.db.
    _warn_on_deprecated_fallbacks(db_path.parent)
    return conn


def _warn_on_deprecated_fallbacks(state_dir: Path) -> None:
    """Log a one-line WARNING per stale JSON fallback (spec-124 D-124-12,
    extended in spec-125 D-125-03; deduped per spec-132 D-132-07).

    Called from :func:`connect` after the migration runner. The check
    is best-effort: missing directory or ``OSError`` are swallowed so
    state.db bootstrap never blocks on filesystem oddities.

    Dedup contract: each (state_dir, filename) pair warns at most once
    per process lifetime via :data:`_WARNED_FALLBACKS`. Tests reset the
    set via :func:`_reset_fallback_warnings`.
    """
    try:
        if not state_dir.is_dir():
            return
        for name in _DEPRECATED_JSON_FALLBACKS:
            stale = state_dir / name
            if not stale.is_file():
                continue
            if stale in _WARNED_FALLBACKS:
                continue
            _WARNED_FALLBACKS.add(stale)
            _logger.warning(
                "stale state JSON fallback found at %s; "
                "state.db is canonical (spec-124 D-124-12, spec-125). "
                "Remove the file -- state.db tables are the source of truth.",
                stale,
            )
    except OSError:
        # Filesystem quirks should never block state.db bootstrap.
        return


@contextmanager
def projection_write(project_root: Path) -> Iterator[sqlite3.Connection]:
    """Context manager opening a write transaction on ``state.db``.

    Begins ``BEGIN IMMEDIATE`` so the writer claims the lock up-front,
    avoiding read-write contention surprises mid-transaction. Commits on
    clean exit, rolls back on exception. Connection is closed at the end.
    """
    conn = connect(project_root, read_only=False, apply_migrations=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


def _now_iso() -> str:
    """Return an ISO-8601 timestamp suitable for state.db row columns."""
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def upsert_ownership_rows(project_root: Path, ownership_map: object) -> int:
    """UPSERT every ``OwnershipEntry`` from ``ownership_map`` into state.db.

    Spec-132 D-132-08: replaces the legacy ``ownership-map.json`` write
    path. The function accepts the loosely-typed ``ownership_map`` object
    (a Pydantic ``OwnershipMap``) and projects its ``paths`` list into
    ``ownership_map`` rows. Idempotent: re-running with the same input
    is a no-op once the rows already match.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        ownership_map: A model exposing ``paths`` with ``pattern``,
            ``owner``, and ``framework_update`` attributes.

    Returns:
        Count of rows attempted (one per ``OwnershipEntry``).
    """
    import json

    paths = getattr(ownership_map, "paths", []) or []
    updated_at = _now_iso()

    with projection_write(project_root) as conn:
        attempted = 0
        for entry in paths:
            pattern = getattr(entry, "pattern", None)
            if not pattern:
                continue
            owner = getattr(entry, "owner", None)
            owner_value = owner.value if hasattr(owner, "value") else (owner or "")
            owners_json = json.dumps([owner_value]) if owner_value else "[]"
            policy = getattr(entry, "framework_update", None)
            severity = policy.value if hasattr(policy, "value") else (policy or None)
            conn.execute(
                """
                INSERT INTO ownership_map
                  (path_pattern, owners_json, severity, reviewers_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path_pattern) DO UPDATE SET
                  owners_json    = excluded.owners_json,
                  severity       = excluded.severity,
                  reviewers_json = excluded.reviewers_json,
                  updated_at     = excluded.updated_at
                """,
                (pattern, owners_json, severity, "[]", updated_at),
            )
            attempted += 1
        return attempted


def upsert_decision_rows(project_root: Path, decision_store: object) -> int:
    """UPSERT every ``Decision`` from ``decision_store`` into state.db.

    Spec-132 D-132-08: replaces the legacy ``decision-store.json`` write
    path. Default-empty stores (``decisions=[]``) UPSERT zero rows and
    return ``0`` -- the table simply stays untouched, which is correct
    behaviour for a fresh install.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        decision_store: A model exposing ``decisions`` (list of
            ``Decision`` instances with ``id``, ``decision``, ``context``,
            ``spec``, ``decided_at``).

    Returns:
        Count of rows attempted.
    """
    decisions = getattr(decision_store, "decisions", []) or []

    # Lazy bootstrap: ensure the decisions schema exists before any
    # write. Idempotent — the migration runner short-circuits on the
    # ``_migrations`` ledger.
    bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap.close()

    if not decisions:
        # Fresh install: ensure the table exists by opening a write
        # transaction (a no-op commit), so the table is present for
        # later writers without seeding any synthetic rows.
        with projection_write(project_root):
            pass
        return 0

    now = _now_iso()
    with projection_write(project_root) as conn:
        attempted = 0
        for entry in decisions:
            decision_id = getattr(entry, "id", None)
            if not decision_id:
                continue
            decided_at = getattr(entry, "decided_at", None)
            decided_iso = (
                decided_at.isoformat() if hasattr(decided_at, "isoformat") else (decided_at or now)
            )
            spec_id = getattr(entry, "spec", None) or ""
            status = getattr(entry, "status", None)
            status_value = status.value if hasattr(status, "value") else (status or "active")
            expires_at_attr = getattr(entry, "expires_at", None)
            expires_iso = (
                expires_at_attr.isoformat()
                if hasattr(expires_at_attr, "isoformat")
                else (expires_at_attr or None)
            )
            # Serialize the full Pydantic payload into ``details_json``
            # so the view-model round-trip (load_decisions) reconstructs
            # every field (risk_category, severity, finding_id, ...).
            details_payload: str | None = None
            if hasattr(entry, "model_dump"):
                import json as _json

                details_payload = _json.dumps(
                    entry.model_dump(mode="json", by_alias=True),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            conn.execute(
                """
                INSERT INTO decisions
                  (decision_id, spec_id, status, title, rationale, context,
                   consequences, superseded_by, expires_at, details_json,
                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                  spec_id       = excluded.spec_id,
                  status        = excluded.status,
                  title         = excluded.title,
                  rationale     = excluded.rationale,
                  context       = excluded.context,
                  consequences  = excluded.consequences,
                  superseded_by = excluded.superseded_by,
                  expires_at    = excluded.expires_at,
                  details_json  = excluded.details_json,
                  updated_at    = excluded.updated_at
                """,
                (
                    decision_id,
                    spec_id,
                    status_value,
                    getattr(entry, "decision", "") or "",
                    None,
                    getattr(entry, "context", None),
                    None,
                    None,
                    expires_iso,
                    details_payload,
                    decided_iso,
                    now,
                ),
            )
            attempted += 1
        return attempted


def list_decisions(project_root: Path, *, status: str | None = None) -> list[dict[str, str | None]]:
    """Read decisions from ``state.db``.

    Canonical reader for CLI surfaces (`ai-eng decision list`) per
    CLAUDE.md §0 bootstrap. Returns rows as dicts so callers do not
    need to import any Pydantic model -- the table is the source of
    truth.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        status: Optional filter (``active`` / ``expired`` / ``revoked``
            / ``superseded`` / ``remediated``). When ``None``, all
            statuses are returned.

    Returns:
        List of row dicts ordered by ``decision_id`` ascending. Empty
        list when the table has no matching rows or the database is
        missing.
    """
    db_path = state_db_path(project_root)
    if not db_path.exists():
        return []
    # Lazy bootstrap: ensure the schema exists. This is a no-op on
    # already-bootstrapped DBs (the ``_migrations`` ledger short-circuits).
    bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap.close()
    conn = connect(project_root, read_only=True, apply_migrations=None)
    try:
        try:
            if status is None:
                cursor = conn.execute(
                    "SELECT decision_id, spec_id, status, title, rationale, context,"
                    " consequences, superseded_by, expires_at, created_at, updated_at"
                    " FROM decisions ORDER BY decision_id ASC"
                )
            else:
                cursor = conn.execute(
                    "SELECT decision_id, spec_id, status, title, rationale, context,"
                    " consequences, superseded_by, expires_at, created_at, updated_at"
                    " FROM decisions WHERE status = ? ORDER BY decision_id ASC",
                    (status,),
                )
        except sqlite3.OperationalError:
            return []
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def upsert_decision_rows_raw(project_root: Path, rows: list[dict[str, str | None]]) -> int:
    """UPSERT raw row dicts into ``decisions``.

    Complements :func:`upsert_decision_rows` (which takes a Pydantic
    DecisionStore). Used by surfaces that work directly with the
    canonical state.db schema -- e.g. ``ai-eng decision record`` and
    ``ai-eng decision backfill`` -- without needing the legacy JSON
    DecisionStore shape.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        rows: List of row dicts. Required keys: ``decision_id``,
            ``status``, ``title``. Optional: ``spec_id``,
            ``rationale``, ``context``, ``consequences``,
            ``superseded_by``.

    Returns:
        Count of rows attempted.
    """
    # Lazy bootstrap: ensure the schema exists before any write.
    bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap.close()

    if not rows:
        with projection_write(project_root):
            pass
        return 0

    now = _now_iso()
    with projection_write(project_root) as conn:
        attempted = 0
        for row in rows:
            decision_id = row.get("decision_id")
            if not decision_id:
                continue
            conn.execute(
                """
                INSERT INTO decisions
                  (decision_id, spec_id, status, title, rationale, context,
                   consequences, superseded_by, expires_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                  spec_id       = excluded.spec_id,
                  status        = excluded.status,
                  title         = excluded.title,
                  rationale     = excluded.rationale,
                  context       = excluded.context,
                  consequences  = excluded.consequences,
                  superseded_by = excluded.superseded_by,
                  expires_at    = excluded.expires_at,
                  updated_at    = excluded.updated_at
                """,
                (
                    decision_id,
                    row.get("spec_id") or "",
                    row.get("status") or "active",
                    row.get("title") or "",
                    row.get("rationale"),
                    row.get("context"),
                    row.get("consequences"),
                    row.get("superseded_by"),
                    row.get("expires_at"),
                    row.get("created_at") or now,
                    now,
                ),
            )
            attempted += 1
        return attempted


def list_full_decisions(project_root: Path) -> list[dict[str, str | None]]:
    """Read decisions including the ``details_json`` blob.

    Companion to :func:`list_decisions` for callers that need every
    Pydantic-shaped field (risk_category, severity, finding_id, ...).
    The blob is returned verbatim; deserialization is the caller's
    responsibility (avoids importing ``state.models`` from here, which
    would create a circular dependency).

    Returns:
        Row dicts ordered by ``decision_id`` ascending. Empty list on
        a missing database or absent table.
    """
    db_path = state_db_path(project_root)
    if not db_path.exists():
        return []
    bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap.close()
    conn = connect(project_root, read_only=True, apply_migrations=None)
    try:
        try:
            cursor = conn.execute(
                "SELECT decision_id, spec_id, status, title, rationale, context,"
                " consequences, superseded_by, expires_at, details_json,"
                " created_at, updated_at"
                " FROM decisions ORDER BY decision_id ASC"
            )
        except sqlite3.OperationalError:
            return []
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def upsert_install_step(
    project_root: Path,
    step_id: str,
    *,
    status: str,
    installed: bool = False,
    authenticated: bool = False,
    integrity_verified: bool = False,
    detail: dict[str, object] | None = None,
    updated_at: str | None = None,
) -> int:
    """UPSERT a single ``install_steps`` row.

    Spec-138 M3.T4: installer-phase autopopulation. The installer pipeline
    calls this helper once per completed phase so the canonical
    ``install_steps`` table reflects per-step state without the legacy
    ``install-state.json`` JSON sidecar (already retired by spec-125).

    Idempotent: re-running with the same ``step_id`` UPSERTs in place. The
    function lazily bootstraps the schema so a fresh ``state.db`` (test or
    first install) gets the ``install_steps`` table before the INSERT.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        step_id: Stable identifier for the install step (typically the
            phase name -- ``detect`` / ``governance`` / ``state`` / ...).
        status: Outcome string -- ``done`` / ``pending`` / ``failed`` /
            ``skipped`` (no enum, the column is plain TEXT).
        installed: True when the step's artefact is on disk.
        authenticated: True when the step required auth and it succeeded.
        integrity_verified: True when the step ran the post-write
            integrity check successfully.
        detail: Optional structured payload serialised into ``detail_json``.
        updated_at: Override the timestamp (test hook); defaults to now.

    Returns:
        ``1`` on a successful UPSERT.
    """
    import json as _json

    # Lazy bootstrap so a fresh state.db has the schema before INSERT.
    bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap.close()

    timestamp = updated_at or _now_iso()
    detail_json = _json.dumps(detail, sort_keys=True) if detail else None

    with projection_write(project_root) as conn:
        conn.execute(
            """
            INSERT INTO install_steps
              (step_id, status, installed, authenticated, integrity_verified,
               detail_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(step_id) DO UPDATE SET
              status              = excluded.status,
              installed           = excluded.installed,
              authenticated       = excluded.authenticated,
              integrity_verified  = excluded.integrity_verified,
              detail_json         = excluded.detail_json,
              updated_at          = excluded.updated_at
            """,
            (
                step_id,
                status,
                int(installed),
                int(authenticated),
                int(integrity_verified),
                detail_json,
                timestamp,
            ),
        )
    return 1


def upsert_ownership_rows_raw(
    project_root: Path,
    rows: list[dict[str, object | None]],
) -> int:
    """UPSERT raw ownership rows parsed from ``.github/CODEOWNERS``.

    Spec-138 M3.T5: complements :func:`upsert_ownership_rows` (which takes
    a Pydantic ``OwnershipMap``). The CODEOWNERS importer works with
    plain row dicts (``path_pattern`` + ``owners`` list) so we keep the
    helper free of legacy model imports.

    Args:
        project_root: Repository root holding ``.ai-engineering/``.
        rows: List of row dicts. Required keys: ``path_pattern``,
            ``owners`` (a list of owner strings or a single string).
            Optional: ``severity``, ``reviewers`` (list).

    Returns:
        Count of rows attempted (one per non-empty pattern).
    """
    import json as _json

    bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap.close()

    if not rows:
        with projection_write(project_root):
            pass
        return 0

    updated_at = _now_iso()
    with projection_write(project_root) as conn:
        attempted = 0
        for row in rows:
            pattern = row.get("path_pattern")
            if not pattern:
                continue
            owners_raw = row.get("owners") or []
            if isinstance(owners_raw, str):
                owners: list[str] = [owners_raw]
            elif isinstance(owners_raw, list):
                owners = [str(item) for item in owners_raw]
            else:
                owners = []
            owners_json = _json.dumps(owners)
            severity = row.get("severity")
            reviewers_raw = row.get("reviewers") or []
            if isinstance(reviewers_raw, str):
                reviewers: list[str] = [reviewers_raw]
            elif isinstance(reviewers_raw, list):
                reviewers = [str(item) for item in reviewers_raw]
            else:
                reviewers = []
            reviewers_json = _json.dumps(reviewers)
            conn.execute(
                """
                INSERT INTO ownership_map
                  (path_pattern, owners_json, severity, reviewers_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path_pattern) DO UPDATE SET
                  owners_json    = excluded.owners_json,
                  severity       = excluded.severity,
                  reviewers_json = excluded.reviewers_json,
                  updated_at     = excluded.updated_at
                """,
                (pattern, owners_json, severity, reviewers_json, updated_at),
            )
            attempted += 1
        return attempted


__all__ = [
    "STATE_DB_REL",
    "connect",
    "list_decisions",
    "list_full_decisions",
    "projection_write",
    "state_db_path",
    "upsert_decision_rows",
    "upsert_decision_rows_raw",
    "upsert_install_step",
    "upsert_ownership_rows",
    "upsert_ownership_rows_raw",
]
