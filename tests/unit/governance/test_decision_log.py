"""Tests for ``governance.decision_log`` (spec-122 Phase C, T-3.8).

Covers:

(a) NDJSON-only path when state.db is absent.
(b) Dual-write when state.db + events table are present.
(c) Sample mask: 100/100 blocked recorded, ~10/100 allow recorded.
(d) Field redaction for `subject` / `justification`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from ai_engineering.governance import decision_log


def _build_project(tmp_path: Path) -> Path:
    """Create the minimum project skeleton emit_policy_decision needs."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    # Minimal manifest.yml so _project_name doesn't blow up on load.
    manifest = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest.write_text("name: opa-test\nversion: 1.0.0\n", encoding="utf-8")
    return tmp_path


def _read_events(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# ---------------------------------------------------------------------------
# (a) NDJSON-only path
# ---------------------------------------------------------------------------


def test_ndjson_only_when_state_db_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = _build_project(tmp_path)
    # state.db does not exist -> dual-write must be skipped silently.
    monkeypatch.setattr(decision_log, "should_sample", lambda _: True)

    decision_log.emit_policy_decision(
        project_root=project_root,
        policy="commit_conventional",
        query="data.commit_conventional.deny",
        input_data={"subject": "feat: ok"},
        decision="blocked",
        deny_messages=["bad subject"],
        component="gate-engine",
        source="pre-commit",
        correlation_id="cid-1",
    )

    events = _read_events(project_root)
    assert len(events) == 1
    assert events[0]["kind"] == "policy_decision"
    assert events[0]["outcome"] == "blocked"
    assert events[0]["detail"]["deny_messages"] == ["bad subject"]
    # Subject is sensitive -> masked.
    assert events[0]["detail"]["input"]["subject"].startswith("sha256:")


# ---------------------------------------------------------------------------
# (b) Dual-write path
# ---------------------------------------------------------------------------


def test_dual_write_when_events_table_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = _build_project(tmp_path)
    db_path = project_root / decision_log.STATE_DB_REL
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE events (
            kind TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            component TEXT NOT NULL,
            outcome TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            project TEXT NOT NULL,
            detail_json TEXT NOT NULL
        )
        """,
    )
    conn.commit()
    conn.close()

    decision_log.emit_policy_decision(
        project_root=project_root,
        policy="branch_protection",
        query="data.branch_protection.deny",
        input_data={"branch": "main", "action": "push"},
        decision="blocked",
        deny_messages=["push to protected branch denied"],
        component="gate-engine",
        source="pre-push",
        correlation_id="cid-2",
    )

    events = _read_events(project_root)
    assert len(events) == 1

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT kind, outcome, correlation_id, project, detail_json FROM events"
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    kind, outcome, cid, project, detail_json = rows[0]
    assert kind == "policy_decision"
    assert outcome == "blocked"
    assert cid == "cid-2"
    assert project == "opa-test"
    assert json.loads(detail_json)["deny_messages"] == ["push to protected branch denied"]


# ---------------------------------------------------------------------------
# (c) Sample mask
# ---------------------------------------------------------------------------


def test_sample_mask_records_all_blocks(tmp_path: Path) -> None:
    project_root = _build_project(tmp_path)

    for i in range(100):
        decision_log.emit_policy_decision(
            project_root=project_root,
            policy="commit_conventional",
            query="data.commit_conventional.deny",
            input_data={"subject": "no good"},
            decision="blocked",
            deny_messages=["bad"],
            correlation_id=f"block-{i}",
        )

    events = _read_events(project_root)
    assert len(events) == 100, "every blocked decision must be persisted"


def test_sample_mask_records_subset_of_allows(tmp_path: Path) -> None:
    project_root = _build_project(tmp_path)

    for i in range(100):
        decision_log.emit_policy_decision(
            project_root=project_root,
            policy="branch_protection",
            query="data.branch_protection.deny",
            input_data={"branch": f"feat/x-{i}"},
            decision="allow",
            deny_messages=[],
            correlation_id=f"allow-{i}",
        )

    events = _read_events(project_root)
    # Sampling is deterministic -- expected hit rate ~10% with sha256 mod 10.
    # Across 100 ids the ratio should land in [3, 25] (very loose bounds);
    # a tighter window would risk a flake on a hash distribution swing.
    assert 3 <= len(events) <= 25, f"sample mask should keep ~10% of allows, got {len(events)}"


# ---------------------------------------------------------------------------
# (d) Field redaction
# ---------------------------------------------------------------------------


def test_redacts_subject_and_justification(tmp_path: Path) -> None:
    project_root = _build_project(tmp_path)

    decision_log.emit_policy_decision(
        project_root=project_root,
        policy="risk_acceptance_ttl",
        query="data.risk_acceptance_ttl.deny",
        input_data={
            "ttl_expires_at": "2026-06-01T00:00:00Z",
            "now": "2026-05-05T00:00:00Z",
            "justification": "production incident remediation pending",
            "subject": "feat: foo",
        },
        decision="blocked",
        deny_messages=["expired"],
        correlation_id="redact-1",
    )

    events = _read_events(project_root)
    assert len(events) == 1
    masked = events[0]["detail"]["input"]
    assert masked["justification"].startswith("sha256:")
    assert "production incident" not in json.dumps(masked)
    assert masked["subject"].startswith("sha256:")
    # Non-sensitive fields stay verbatim.
    assert masked["now"] == "2026-05-05T00:00:00Z"
    assert masked["ttl_expires_at"] == "2026-06-01T00:00:00Z"


def test_should_sample_is_deterministic() -> None:
    cid = "abc123"
    assert decision_log.should_sample(cid) == decision_log.should_sample(cid)
