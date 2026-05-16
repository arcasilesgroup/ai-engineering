"""SQLite projection of the framework-events NDJSON stream.

spec-123 T-3.10 / D-123-22 redirect
-----------------------------------
Originally (spec-120 §4.3) the projection lived at
``.ai-engineering/state/audit-index.sqlite`` with its own schema. After
spec-122/123 consolidation the index is folded into the unified
``state.db`` so a single SQLite file carries every framework projection
(events, decisions, gate findings, ownership, etc.). The public API
shape is preserved so audit CLI verbs and external consumers don't need
to relearn anything:

* :class:`IndexResult` -- frozen dataclass returned by :func:`build_index`.
* :func:`index_path` -- now points to ``state.db`` rather than
  ``audit-index.sqlite``.
* :func:`build_index` -- read the NDJSON, write into ``state.db.events``.
  Idempotent and incremental via the per-row ``span_id`` PK
  (``ON CONFLICT DO NOTHING``); ``rebuild=True`` deletes existing rows
  before re-reading.
* :func:`open_index_readonly` -- read-only :class:`sqlite3.Connection`
  on ``state.db`` for query callers (CLI ``audit query``, ``audit
  tokens``, ``audit replay``).

The legacy ``audit-index.sqlite`` is removed lazily on the first call
through :func:`build_index` / :func:`open_index_readonly`.

Robustness contract
-------------------
* Missing NDJSON file -> soft success (empty :class:`IndexResult`).
* Malformed JSON line -> stderr warning, skip the line, continue.
* DB lock / WAL contention -> ``timeout=10.0`` plus ``PRAGMA
  journal_mode=WAL`` (already enforced by ``state_db.connect``).

Stdlib-only by design (``sqlite3`` + ``json`` + ``hashlib`` + ``pathlib``
+ ``time`` + ``sys`` + ``datetime``). No third-party dependencies.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths + schema constants
# ---------------------------------------------------------------------------

NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
# spec-123 D-123-22: index path now points at the unified state.db. The
# legacy audit-index.sqlite is deleted on first use.
INDEX_REL = Path(".ai-engineering") / "state" / "state.db"
_LEGACY_INDEX_REL = Path(".ai-engineering") / "state" / "audit-index.sqlite"

# Spec-120 §4.3 schema. CREATE statements are IF NOT EXISTS so the writer
# can run on a fresh DB or an existing one without an explicit migration
# step. Drop-and-recreate behaviour is opt-in via ``rebuild=True``.
_DDL_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
  span_id            TEXT PRIMARY KEY,
  trace_id           TEXT,
  parent_span_id     TEXT,
  correlation_id     TEXT NOT NULL,
  session_id         TEXT,
  timestamp          TEXT NOT NULL,
  ts_unix_ms         INTEGER NOT NULL,
  engine             TEXT NOT NULL,
  kind               TEXT NOT NULL,
  component          TEXT NOT NULL,
  outcome            TEXT NOT NULL,
  source             TEXT,
  prev_event_hash    TEXT,
  genai_system       TEXT,
  genai_model        TEXT,
  input_tokens       INTEGER,
  output_tokens      INTEGER,
  total_tokens       INTEGER,
  cost_usd           REAL,
  detail_json        TEXT NOT NULL
)
"""

_DDL_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_events_trace      ON events(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_session    ON events(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_kind       ON events(kind)",
    "CREATE INDEX IF NOT EXISTS idx_events_component  ON events(component)",
    "CREATE INDEX IF NOT EXISTS idx_events_ts         ON events(ts_unix_ms)",
)

_DDL_INDEXED_LINES = """
CREATE TABLE IF NOT EXISTS indexed_lines (
  last_offset INTEGER PRIMARY KEY,
  last_hash   TEXT,
  indexed_at  TEXT
)
"""

_DDL_VIEW_SKILL_ROLLUP = """
CREATE VIEW IF NOT EXISTS skill_token_rollup AS
  SELECT json_extract(detail_json, '$.skill') AS skill,
         COUNT(*)              AS invocations,
         SUM(input_tokens)     AS input_tokens,
         SUM(output_tokens)    AS output_tokens,
         SUM(total_tokens)     AS total_tokens,
         SUM(cost_usd)         AS cost_usd
    FROM events
   WHERE kind = 'skill_invoked'
   GROUP BY skill
"""

_DDL_VIEW_AGENT_ROLLUP = """
CREATE VIEW IF NOT EXISTS agent_token_rollup AS
  SELECT json_extract(detail_json, '$.agent') AS agent,
         COUNT(*)              AS dispatches,
         SUM(input_tokens)     AS input_tokens,
         SUM(output_tokens)    AS output_tokens,
         SUM(total_tokens)     AS total_tokens,
         SUM(cost_usd)         AS cost_usd
    FROM events
   WHERE kind = 'agent_dispatched'
   GROUP BY agent
"""

_DDL_VIEW_SESSION_ROLLUP = """
CREATE VIEW IF NOT EXISTS session_token_rollup AS
  SELECT session_id,
         MIN(timestamp)        AS started_at,
         MAX(timestamp)        AS ended_at,
         COUNT(*)              AS events,
         SUM(input_tokens)     AS input_tokens,
         SUM(output_tokens)    AS output_tokens,
         SUM(total_tokens)     AS total_tokens,
         SUM(cost_usd)         AS cost_usd
    FROM events
   WHERE session_id IS NOT NULL
   GROUP BY session_id
"""


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexResult:
    """Outcome of a :func:`build_index` run.

    Attributes
    ----------
    rows_indexed:
        Number of NDJSON lines successfully INSERTed in this run. Skipped
        malformed lines are NOT counted here.
    rows_total:
        Total number of rows in the ``events`` table after this run
        completes. Equal to ``rows_indexed`` when ``rebuilt=True`` (the
        table was dropped first); larger on incremental runs.
    last_offset:
        Byte offset of the end of the last successfully processed line.
        Persisted to ``indexed_lines.last_offset`` so the next call can
        seek and resume.
    elapsed_ms:
        Wall-clock duration of the run in milliseconds (rounded down).
    rebuilt:
        ``True`` when the call dropped and recreated the schema before
        reading; ``False`` for incremental / first-time builds.
    """

    rows_indexed: int
    rows_total: int
    last_offset: int
    elapsed_ms: int
    rebuilt: bool


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def index_path(project_root: Path) -> Path:
    """Return the canonical SQLite index path for ``project_root``."""
    return project_root / INDEX_REL


def _ndjson_path(project_root: Path) -> Path:
    """Return the canonical NDJSON source path for ``project_root``."""
    return project_root / NDJSON_REL


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def _delete_legacy_index(project_root: Path) -> None:
    """Best-effort cleanup of the pre-spec-123 audit-index.sqlite.

    The redirect lands every consumer on ``state.db``; the legacy file
    becomes dead state. We delete it (and its WAL/SHM siblings) on the
    first call through this module so a stale projection doesn't quietly
    drift away from the unified DB.
    """
    legacy = project_root / _LEGACY_INDEX_REL
    for suffix in ("", "-wal", "-shm"):
        candidate = legacy.with_name(legacy.name + suffix) if suffix else legacy
        if candidate.exists():
            with contextlib.suppress(OSError):
                candidate.unlink()


def _connect_writer(project_root: Path) -> sqlite3.Connection:
    """Open a writer connection on ``state.db`` (lazy bootstrap aware).

    Routes through :func:`ai_engineering.state.state_db.connect` so the
    PRAGMA suite, lazy migration runner, and connection lifetime stay in
    one place. Lazy bootstrap means a fresh project picks up the schema
    transparently before the first write.
    """
    from ai_engineering.state import state_db as _state_db

    _delete_legacy_index(project_root)
    return _state_db.connect(project_root)


def open_index_readonly(project_root: Path) -> sqlite3.Connection:
    """Open ``state.db`` in read-only mode for query consumers.

    Uses the ``file:?mode=ro`` URI so the OS-level filesystem still
    enforces write rejection -- attempting to ``INSERT`` / ``UPDATE`` /
    ``DELETE`` on the returned connection raises
    :class:`sqlite3.OperationalError`. Read paths (CLI ``query``,
    ``tokens``, ``replay``) are expected to use this entry point.

    On first invocation, ensures ``state.db`` is bootstrapped so a
    read-only caller on a fresh project still gets a populated DB. The
    bootstrap is performed via a brief writer connection and then
    discarded.
    """
    from ai_engineering.state import state_db as _state_db

    _delete_legacy_index(project_root)
    path = index_path(project_root)
    if not path.exists() or path.stat().st_size == 0:
        # Lazy bootstrap from the writer side so the read URI below has
        # a populated DB to attach to.
        bootstrap = _state_db.connect(project_root)
        bootstrap.close()
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=10.0)


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------


def _create_schema(conn: sqlite3.Connection) -> None:
    """Ensure the rollup views and resume-offset table exist on ``state.db``.

    ``state.db`` ships with the ``events`` table and indexes from migration
    ``0001_initial_schema``. The three rollup views and the
    ``indexed_lines`` resume-offset table are ``audit_index``-specific
    additive surfaces, idempotent ``CREATE ... IF NOT EXISTS``.
    """
    conn.execute(_DDL_INDEXED_LINES)
    conn.execute(_DDL_VIEW_SKILL_ROLLUP)
    conn.execute(_DDL_VIEW_AGENT_ROLLUP)
    conn.execute(_DDL_VIEW_SESSION_ROLLUP)
    conn.commit()


def _drop_schema(conn: sqlite3.Connection) -> None:
    """Truncate the audit_index-specific projection state for a clean rebuild.

    Drops the views and the resume-offset table, then ``DELETE FROM events``
    so the ``ON CONFLICT DO NOTHING`` insert path treats every NDJSON line
    as new. The events table itself is **not** dropped because state.db
    schema is owned by the migration runner.
    """
    conn.execute("DROP VIEW IF EXISTS skill_token_rollup")
    conn.execute("DROP VIEW IF EXISTS agent_token_rollup")
    conn.execute("DROP VIEW IF EXISTS session_token_rollup")
    conn.execute("DROP TABLE IF EXISTS indexed_lines")
    conn.execute("DELETE FROM events")
    conn.commit()


# ---------------------------------------------------------------------------
# Event extraction
# ---------------------------------------------------------------------------


def _parse_iso_to_unix_ms(iso: str) -> int:
    """Parse an ISO-8601 timestamp into integer unix milliseconds.

    Many existing events have ``timestamp = ""``; the caller passes the
    empty string straight through and this helper returns 0 so the row
    still indexes (legacy events are not skipped). Unparseable values
    likewise fall back to 0 -- the raw ``timestamp`` text is still
    preserved in the ``timestamp`` column for forensic queries.
    """
    if not iso:
        return 0
    # Tolerate a trailing 'Z' (most events) or an explicit offset.
    candidate = iso.replace("Z", "+00:00") if iso.endswith("Z") else iso
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _extract_columns(event: dict[str, Any], line_bytes: bytes) -> dict[str, Any]:
    """Map a parsed event dict to the spec-120 §4.3 column tuple.

    See module docstring for the per-field rules. ``line_bytes`` is the
    raw NDJSON line (without trailing newline) used to synthesise a
    deterministic span_id when the event lacks one -- legacy events
    written before spec-120 had no ``spanId`` and would otherwise
    collide on the PRIMARY KEY.
    """
    # spec-123 D-123-22: align synthetic span_id with migration 0003
    # (replay_ndjson) so the lazy-bootstrap path and audit_index path
    # produce identical PKs for the same legacy event. Otherwise the
    # ``ON CONFLICT(span_id) DO NOTHING`` no-op is missed and we would
    # double-insert each pre-spec-120 event.
    span_id_raw = event.get("spanId") or event.get("span_id")
    if isinstance(span_id_raw, str) and span_id_raw:
        span_id = span_id_raw
    else:
        canonical = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        span_id = "synthetic:" + hashlib.sha256(canonical).hexdigest()[:24]

    trace_id = event.get("traceId") if isinstance(event.get("traceId"), str) else None
    parent_span_id_raw = event.get("parentSpanId")
    parent_span_id = parent_span_id_raw if isinstance(parent_span_id_raw, str) else None

    correlation_id_raw = event.get("correlationId")
    if isinstance(correlation_id_raw, str) and correlation_id_raw:
        correlation_id = correlation_id_raw
    else:
        # Schema declares correlation_id NOT NULL. Synthesise a stable
        # placeholder rather than refusing the row -- legacy events that
        # somehow lost the field still go in for forensic completeness.
        correlation_id = f"missing-{span_id}"

    session_id_raw = event.get("sessionId")
    session_id = session_id_raw if isinstance(session_id_raw, str) and session_id_raw else None

    timestamp_raw = event.get("timestamp")
    timestamp = timestamp_raw if isinstance(timestamp_raw, str) else ""
    ts_unix_ms = _parse_iso_to_unix_ms(timestamp)

    engine = _str_or_unknown(event.get("engine"))
    kind = _str_or_unknown(event.get("kind"))
    component = _str_or_unknown(event.get("component"))
    outcome = _str_or_unknown(event.get("outcome"))

    source_raw = event.get("source")
    source = source_raw if isinstance(source_raw, str) and source_raw else None

    # Tolerate both spec-110 canonical (``prev_event_hash``) and the
    # camelCase alias (``prevEventHash``) the Pydantic models emit when
    # serialised with ``by_alias=True``.
    prev_hash_raw = event.get("prev_event_hash", event.get("prevEventHash"))
    prev_event_hash = prev_hash_raw if isinstance(prev_hash_raw, str) else None

    detail_obj = event.get("detail")
    if not isinstance(detail_obj, dict):
        detail_obj = {}

    genai = detail_obj.get("genai")
    if not isinstance(genai, dict):
        genai = {}

    genai_system_raw = genai.get("system")
    genai_system = (
        genai_system_raw if isinstance(genai_system_raw, str) and genai_system_raw else None
    )

    request = genai.get("request")
    if not isinstance(request, dict):
        request = {}
    model_raw = request.get("model")
    genai_model = model_raw if isinstance(model_raw, str) and model_raw else None

    usage = genai.get("usage")
    if not isinstance(usage, dict):
        usage = {}

    input_tokens = _int_or_none(usage.get("input_tokens"))
    output_tokens = _int_or_none(usage.get("output_tokens"))
    total_tokens = _int_or_none(usage.get("total_tokens"))
    cost_usd = _float_or_none(usage.get("cost_usd"))

    detail_json = json.dumps(detail_obj, sort_keys=True, separators=(",", ":"))

    return {
        "span_id": span_id,
        "trace_id": trace_id,
        "parent_span_id": parent_span_id,
        "correlation_id": correlation_id,
        "session_id": session_id,
        "timestamp": timestamp,
        "ts_unix_ms": ts_unix_ms,
        "engine": engine,
        "kind": kind,
        "component": component,
        "outcome": outcome,
        "source": source,
        "prev_event_hash": prev_event_hash,
        "genai_system": genai_system,
        "genai_model": genai_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "detail_json": detail_json,
    }


def _str_or_unknown(value: Any) -> str:
    """Coerce ``value`` to a string, falling back to ``"unknown"`` on miss.

    Schema declares ``engine`` / ``kind`` / ``component`` / ``outcome``
    NOT NULL. Legacy or malformed events occasionally drop one of them;
    we record ``"unknown"`` rather than refuse the row so the index
    surface stays auditable end-to-end.
    """
    if isinstance(value, str) and value:
        return value
    return "unknown"


def _int_or_none(value: Any) -> int | None:
    """Coerce to int when possible; otherwise None.

    Booleans are not treated as ints (they're a subclass in Python but
    nonsense as token counts).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _float_or_none(value: Any) -> float | None:
    """Coerce to float when possible; otherwise None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


# ---------------------------------------------------------------------------
# Insert path
# ---------------------------------------------------------------------------


_INSERT_SQL = """
INSERT INTO events (
  span_id, trace_id, parent_span_id, correlation_id, session_id,
  timestamp, engine, kind, component, outcome,
  source, prev_event_hash, genai_system, genai_model,
  input_tokens, output_tokens, total_tokens, cost_usd, detail_json
) VALUES (
  :span_id, :trace_id, :parent_span_id, :correlation_id, :session_id,
  :timestamp, :engine, :kind, :component, :outcome,
  :source, :prev_event_hash, :genai_system, :genai_model,
  :input_tokens, :output_tokens, :total_tokens, :cost_usd, :detail_json
)
ON CONFLICT(span_id) DO NOTHING
"""


# ---------------------------------------------------------------------------
# Resume offset
# ---------------------------------------------------------------------------


def _read_resume_offset(conn: sqlite3.Connection) -> int:
    """Return the largest ``last_offset`` recorded by a prior run, or 0."""
    cur = conn.execute("SELECT MAX(last_offset) FROM indexed_lines")
    row = cur.fetchone()
    if row is None or row[0] is None:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


def _persist_offset(conn: sqlite3.Connection, last_offset: int, last_hash: str | None) -> None:
    """Record the new ``last_offset`` for the next incremental run.

    The PK is ``last_offset`` itself; a fresh INSERT each run is fine
    (rows are tiny, single-int PK) and avoids a separate UPSERT path.
    The most recent row is the one ``_read_resume_offset`` returns.
    """
    conn.execute(
        "INSERT OR REPLACE INTO indexed_lines (last_offset, last_hash, indexed_at) "
        "VALUES (?, ?, ?)",
        (last_offset, last_hash, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")),
    )


# ---------------------------------------------------------------------------
# Public build entry point
# ---------------------------------------------------------------------------


def build_index(project_root: Path, *, rebuild: bool = False) -> IndexResult:
    """Build (or incrementally update) the SQLite projection.

    Reads ``.ai-engineering/state/framework-events.ndjson`` line by line,
    tracking byte offset, and writes rows into the SQLite database at
    ``.ai-engineering/state/audit-index.sqlite``.

    Parameters
    ----------
    project_root:
        Project root directory. The NDJSON source and SQLite target
        paths are derived from this via :data:`NDJSON_REL` /
        :data:`INDEX_REL`.
    rebuild:
        When ``True``, drop and recreate every table / index / view
        before re-reading from offset 0. When ``False`` (default), seek
        to the prior ``last_offset`` and only ingest new lines.

    Returns
    -------
    IndexResult
        Summary of the run. ``rows_indexed`` counts newly INSERTed rows
        (skipped malformed lines do not count); ``rows_total`` is the
        cardinality of the ``events`` table after the run.
    """
    started_ns = time.monotonic_ns()
    ndjson = _ndjson_path(project_root)
    index_path(project_root)

    # Soft-success on missing source file -- a brand-new project root has
    # no events yet; that's not an error, just an empty index.
    if not ndjson.exists():
        return IndexResult(
            rows_indexed=0,
            rows_total=0,
            last_offset=0,
            elapsed_ms=0,
            rebuilt=rebuild,
        )

    conn = _connect_writer(project_root)
    try:
        if rebuild:
            _drop_schema(conn)
        _create_schema(conn)

        resume_offset = 0 if rebuild else _read_resume_offset(conn)

        rows_indexed = 0
        last_good_hash: str | None = None
        # We open in binary mode so byte offsets match the on-disk file
        # exactly (text-mode line endings can drift on Windows). Each
        # line is decoded explicitly as UTF-8 with replacement so a
        # rogue byte does not abort the whole indexing run.
        with ndjson.open("rb") as fh:
            if resume_offset:
                fh.seek(resume_offset)
            cur = conn.cursor()
            cur.execute("BEGIN")
            try:
                while True:
                    raw = fh.readline()
                    if not raw:
                        break
                    line_bytes = raw.rstrip(b"\n").rstrip(b"\r")
                    if not line_bytes:
                        # Tolerate blank trailing lines without bumping
                        # the row counter.
                        continue
                    try:
                        text = line_bytes.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        sys.stderr.write(
                            f"audit_index: skipping non-UTF-8 line at offset {fh.tell()}: {exc}\n"
                        )
                        continue
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError as exc:
                        sys.stderr.write(
                            f"audit_index: skipping malformed JSON at offset "
                            f"{fh.tell()}: {exc.msg}\n"
                        )
                        continue
                    if not isinstance(event, dict):
                        sys.stderr.write(
                            f"audit_index: skipping non-dict JSON at offset {fh.tell()}\n"
                        )
                        continue
                    columns = _extract_columns(event, line_bytes)
                    cur.execute(_INSERT_SQL, columns)
                    rows_indexed += 1
                    last_good_hash = hashlib.sha256(line_bytes).hexdigest()
                final_offset = fh.tell()
                _persist_offset(conn, final_offset, last_good_hash)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        rows_total = _row_count(conn)
        last_offset = _latest_offset(conn)
    finally:
        conn.close()

    elapsed_ms = (time.monotonic_ns() - started_ns) // 1_000_000
    return IndexResult(
        rows_indexed=rows_indexed,
        rows_total=rows_total,
        last_offset=last_offset,
        elapsed_ms=int(elapsed_ms),
        rebuilt=rebuild,
    )


def _row_count(conn: sqlite3.Connection) -> int:
    """Return the number of rows in ``events``."""
    cur = conn.execute("SELECT COUNT(*) FROM events")
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _latest_offset(conn: sqlite3.Connection) -> int:
    """Return the most recently persisted ``last_offset``."""
    return _read_resume_offset(conn)


__all__ = [
    "INDEX_REL",
    "NDJSON_REL",
    "IndexResult",
    "build_index",
    "index_path",
    "open_index_readonly",
]
