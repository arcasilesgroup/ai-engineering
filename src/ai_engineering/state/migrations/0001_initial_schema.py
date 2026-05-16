"""Initial schema migration -- 7 STRICT tables + indexes + decisions FTS5.

spec-122-b T-2.2 / D-122-06.

The seven tables map one-to-one to a named consumer surface:

* ``events``           -- audit CLI replay/query/index targets
* ``decisions``        -- /ai-plan + /ai-explain decision-store projection
* ``risk_acceptances`` -- /ai-release-gate risk decisions
* ``gate_findings``    -- /ai-pr code-review surface
* ``hooks_integrity``  -- /ai-security hook verification ledger
* ``ownership_map``    -- /ai-governance CODEOWNERS analogue
* ``install_steps``    -- ai-eng install per-step state

The ``_migrations`` ledger is created by the runner (idempotent
``CREATE TABLE IF NOT EXISTS``); this migration just creates the
business tables + indexes + FTS5 virtual table.
"""

from __future__ import annotations

import sqlite3

BODY_SHA256 = "23d3a7b241f6c91c884fdd6539f2586614a9ed76b3566f0e80412d35000d7c91"


def apply(conn: sqlite3.Connection) -> None:
    """Create the seven STRICT business tables + indexes + decisions_fts."""
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # events -- canonical projection of framework-events.ndjson
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
          span_id          TEXT PRIMARY KEY,
          trace_id         TEXT,
          parent_span_id   TEXT,
          correlation_id   TEXT,
          session_id       TEXT,
          timestamp        TEXT NOT NULL,
          ts_unix_ms       INTEGER GENERATED ALWAYS AS
            (CAST((julianday(timestamp) - 2440587.5) * 86400000 AS INTEGER)) STORED,
          archive_month    TEXT GENERATED ALWAYS AS (substr(timestamp, 1, 7)) STORED,
          engine           TEXT NOT NULL,
          kind             TEXT NOT NULL,
          component        TEXT NOT NULL,
          outcome          TEXT NOT NULL,
          source           TEXT,
          prev_event_hash  TEXT,
          genai_system     TEXT,
          genai_model      TEXT,
          input_tokens     INTEGER,
          output_tokens    INTEGER,
          total_tokens     INTEGER,
          cost_usd         REAL,
          detail_json      TEXT NOT NULL
        ) STRICT
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts_unix_ms)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_ts_session ON events(ts_unix_ms, session_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_session_ts ON events(session_id, ts_unix_ms)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_kind_ts ON events(kind, ts_unix_ms)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_archive_month ON events(archive_month)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_outcome ON events(ts_unix_ms) "
        "WHERE outcome = 'failure'"
    )

    # ------------------------------------------------------------------
    # decisions -- /ai-plan + /ai-explain decision-store projection
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
          decision_id  TEXT PRIMARY KEY,
          spec_id      TEXT,
          status       TEXT NOT NULL,
          title        TEXT NOT NULL,
          rationale    TEXT,
          context      TEXT,
          consequences TEXT,
          superseded_by TEXT,
          created_at   TEXT NOT NULL,
          updated_at   TEXT NOT NULL
        ) STRICT
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_decisions_status "
        "ON decisions(decision_id) WHERE status = 'active'"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_decisions_spec "
        "ON decisions(spec_id) WHERE spec_id IS NOT NULL"
    )

    # FTS5 virtual table over decision text for fast substring search.
    cur.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
          decision_id UNINDEXED,
          title,
          rationale,
          context,
          consequences,
          content='decisions',
          content_rowid='rowid'
        )
        """
    )

    # ------------------------------------------------------------------
    # risk_acceptances -- /ai-release-gate risk lifecycle
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_acceptances (
          risk_id      TEXT PRIMARY KEY,
          category     TEXT NOT NULL,
          status       TEXT NOT NULL,
          severity     TEXT NOT NULL,
          accepted_by  TEXT,
          rationale    TEXT,
          expires_at   TEXT,
          created_at   TEXT NOT NULL,
          updated_at   TEXT NOT NULL
        ) STRICT
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_risk_active "
        "ON risk_acceptances(risk_id) WHERE status = 'accepted'"
    )

    # ------------------------------------------------------------------
    # gate_findings -- /ai-pr code-review surface
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gate_findings (
          finding_id   TEXT PRIMARY KEY,
          session_id   TEXT NOT NULL,
          rule_id      TEXT NOT NULL,
          severity     TEXT NOT NULL,
          status       TEXT NOT NULL,
          file_path    TEXT,
          line_start   INTEGER,
          line_end     INTEGER,
          message      TEXT,
          created_at   TEXT NOT NULL
        ) STRICT
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gate_session ON gate_findings(session_id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_gate_open "
        "ON gate_findings(finding_id) WHERE status = 'open'"
    )

    # ------------------------------------------------------------------
    # hooks_integrity -- /ai-security hook verification ledger
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hooks_integrity (
          row_id          INTEGER PRIMARY KEY AUTOINCREMENT,
          hook_path       TEXT NOT NULL,
          recorded_sha256 TEXT NOT NULL,
          observed_sha256 TEXT NOT NULL,
          mode            TEXT NOT NULL,
          outcome         TEXT NOT NULL,
          checked_at      TEXT NOT NULL
        ) STRICT
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hooks_recent ON hooks_integrity(checked_at)")

    # ------------------------------------------------------------------
    # ownership_map -- /ai-governance CODEOWNERS analogue
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ownership_map (
          path_pattern   TEXT PRIMARY KEY,
          owners_json    TEXT NOT NULL,
          severity       TEXT,
          reviewers_json TEXT,
          updated_at     TEXT NOT NULL
        ) STRICT
        """
    )

    # ------------------------------------------------------------------
    # install_steps -- ai-eng install per-step state
    # ------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS install_steps (
          step_id            TEXT PRIMARY KEY,
          status             TEXT NOT NULL,
          installed          INTEGER NOT NULL DEFAULT 0,
          authenticated      INTEGER NOT NULL DEFAULT 0,
          integrity_verified INTEGER NOT NULL DEFAULT 0,
          detail_json        TEXT,
          updated_at         TEXT NOT NULL
        ) STRICT
        """
    )


__all__ = ["BODY_SHA256", "apply"]
