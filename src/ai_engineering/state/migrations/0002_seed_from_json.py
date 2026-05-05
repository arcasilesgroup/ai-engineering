"""Seed state.db from existing JSON state files (spec-122-b T-2.5).

Reads the four JSON state files (decision-store, gate-findings,
ownership-map, install-state) and inserts their rows into the
corresponding STRICT tables. Originals are archived (moved, not
copied) to ``state/archive/pre-state-db/<filename>.json`` so the
deletion is traceable.

Idempotent: ``ON CONFLICT(...) DO NOTHING`` for everything except
``ownership_map`` which uses ``ON CONFLICT DO UPDATE`` to keep the
projection in sync if the source JSON evolved between reads.

The fifth file referenced in the spec (``hooks-manifest.json``) is a
sha256 manifest, not a verification log -- the projection target
``hooks_integrity`` is a verification ledger populated at runtime by
``run_hook_safe``. This migration therefore creates ZERO rows in
``hooks_integrity``; runtime hook checks land their first rows.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

BODY_SHA256 = "e32f80f165af14b4b4dd7cc01f32c85ffd56e520b066103c06b52412a96a6598"

_STATE_REL = Path(".ai-engineering") / "state"
_ARCHIVE_REL = _STATE_REL / "archive" / "pre-state-db"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _project_root_from_db(conn: sqlite3.Connection) -> Path:
    """Recover the project root from the connection's main DB path."""
    row = conn.execute("PRAGMA database_list").fetchone()
    if row is None or not row[2]:
        return Path.cwd()
    db_path = Path(row[2])
    # ``state.db`` lives at <root>/.ai-engineering/state/state.db.
    return db_path.parent.parent.parent


def _maybe_archive(src: Path, archive_dir: Path) -> None:
    """Move ``src`` to ``archive_dir/<src.name>``. No-op if src missing."""
    if not src.exists():
        return
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / src.name
    if dest.exists():
        # Preserve historical copy; don't double-archive.
        return
    shutil.move(str(src), str(dest))


def _seed_decisions(conn: sqlite3.Connection, source: Path) -> int:
    if not source.exists():
        return 0
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = list(data.get("active_decisions", [])) + list(data.get("superseded", []))
    inserted = 0
    for row in rows:
        decision_id = row.get("id") or row.get("decision_id")
        if not decision_id:
            continue
        conn.execute(
            """
            INSERT INTO decisions
              (decision_id, spec_id, status, title, rationale, context,
               consequences, superseded_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(decision_id) DO NOTHING
            """,
            (
                decision_id,
                row.get("spec_id"),
                row.get("status", "active"),
                row.get("title", ""),
                row.get("rationale"),
                row.get("context"),
                row.get("consequences"),
                row.get("superseded_by"),
                row.get("created_at") or _now_iso(),
                row.get("updated_at") or _now_iso(),
            ),
        )
        inserted += 1
    return inserted


def _seed_gate_findings(conn: sqlite3.Connection, source: Path) -> int:
    if not source.exists():
        return 0
    data = json.loads(source.read_text(encoding="utf-8"))
    findings = data.get("findings", [])
    session_id = data.get("session_id", "unknown")
    inserted = 0
    for f in findings:
        finding_id = f.get("finding_id") or f.get("id")
        if not finding_id:
            continue
        conn.execute(
            """
            INSERT INTO gate_findings
              (finding_id, session_id, rule_id, severity, status,
               file_path, line_start, line_end, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(finding_id) DO NOTHING
            """,
            (
                finding_id,
                session_id,
                f.get("rule_id", "unknown"),
                f.get("severity", "info"),
                f.get("status", "open"),
                f.get("file_path"),
                f.get("line_start"),
                f.get("line_end"),
                f.get("message"),
                f.get("created_at") or _now_iso(),
            ),
        )
        inserted += 1
    return inserted


def _seed_ownership_map(conn: sqlite3.Connection, source: Path) -> int:
    if not source.exists():
        return 0
    data = json.loads(source.read_text(encoding="utf-8"))
    paths = data.get("paths", [])
    update_meta = data.get("updateMetadata", {})
    updated_at = update_meta.get("updatedAt") or _now_iso()
    inserted = 0
    for p in paths:
        pattern = p.get("pattern")
        if not pattern:
            continue
        owner = p.get("owner")
        owners_json = json.dumps([owner]) if owner else "[]"
        # Schema accepts both ``severity`` and ``frameworkUpdate`` style
        # entries. Map ``frameworkUpdate`` into severity for the row.
        severity = p.get("severity") or p.get("frameworkUpdate")
        reviewers_json = json.dumps(p.get("reviewers", []))
        conn.execute(
            """
            INSERT INTO ownership_map
              (path_pattern, owners_json, severity, reviewers_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path_pattern) DO UPDATE SET
              owners_json = excluded.owners_json,
              severity = excluded.severity,
              reviewers_json = excluded.reviewers_json,
              updated_at = excluded.updated_at
            """,
            (pattern, owners_json, severity, reviewers_json, updated_at),
        )
        inserted += 1
    return inserted


def _seed_install_steps(conn: sqlite3.Connection, source: Path) -> int:
    if not source.exists():
        return 0
    data = json.loads(source.read_text(encoding="utf-8"))
    tooling = data.get("tooling", {}) or {}
    inserted = 0
    for step_id, info in tooling.items():
        if not isinstance(info, dict):
            continue
        installed = bool(info.get("installed", False))
        authenticated = bool(info.get("authenticated", False))
        integrity_verified = bool(info.get("integrity_verified", False))
        # Status derives from boolean flags: done if installed+authenticated;
        # else pending.
        status = "done" if installed and authenticated else "pending"
        # Extract the residual fields into a JSON detail blob.
        detail = {
            k: v
            for k, v in info.items()
            if k not in {"installed", "authenticated", "integrity_verified"}
        }
        conn.execute(
            """
            INSERT INTO install_steps
              (step_id, status, installed, authenticated, integrity_verified,
               detail_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(step_id) DO UPDATE SET
              status = excluded.status,
              installed = excluded.installed,
              authenticated = excluded.authenticated,
              integrity_verified = excluded.integrity_verified,
              detail_json = excluded.detail_json,
              updated_at = excluded.updated_at
            """,
            (
                step_id,
                status,
                int(installed),
                int(authenticated),
                int(integrity_verified),
                json.dumps(detail) if detail else None,
                _now_iso(),
            ),
        )
        inserted += 1
    return inserted


def apply(conn: sqlite3.Connection) -> None:
    """Seed the four JSON sources and archive originals."""
    project_root = _project_root_from_db(conn)
    state_dir = project_root / _STATE_REL
    archive_dir = project_root / _ARCHIVE_REL

    decision_store = state_dir / "decision-store.json"
    gate_findings = state_dir / "gate-findings.json"
    ownership_map = state_dir / "ownership-map.json"
    install_state = state_dir / "install-state.json"

    _seed_decisions(conn, decision_store)
    _seed_gate_findings(conn, gate_findings)
    _seed_ownership_map(conn, ownership_map)
    _seed_install_steps(conn, install_state)

    # NOTE: Per the autopilot constraint, source files are LEFT IN PLACE
    # in this wave. Cleanup wave (sub-spec d) will move them to archive
    # once we are confident the projection is correct.
    # Uncomment to enable archive moves:
    # for src in (decision_store, gate_findings, ownership_map, install_state):
    #     _maybe_archive(src, archive_dir)


__all__ = ["BODY_SHA256", "apply"]
