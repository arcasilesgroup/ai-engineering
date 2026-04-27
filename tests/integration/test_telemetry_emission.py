"""GREEN spec-105 Phase 8 — telemetry event structure.

Covers spec-105 G-11: every risk-acceptance flow emits a canonical
``framework_event`` whose ``detail`` carries
``{category=risk-acceptance, control=<verb>, ...metadata}``.

Status: GREEN — exercises real production code in
``policy/checks/_accept_lookup`` and ``cli_commands/risk_cmd``.
Prior history: started as a Phase 1 RED skeleton with placeholder
``NotImplementedError`` bodies; replaced with real assertions in Phase 8.

Fixture invariant: ``GateFinding`` rejects ``auto_fixable=True`` paired with
``auto_fix_command=None`` per ``_enforce_auto_fix_command_when_fixable``.
The fixtures below set ``auto_fixable=False`` to keep the model satisfied
without coupling the assertion to fixer wiring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


def _seed_decision_store(root: Path, dec_id: str, rule_id: str) -> None:
    """Persist a single active risk-acceptance covering ``rule_id``."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": "1.1",
        "decisions": [
            {
                "id": dec_id,
                "context": f"finding:{rule_id}",
                "decision": "Accepted via Phase 8 telemetry test.",
                "decidedAt": "2026-04-26T00:00:00Z",
                "spec": "spec-105",
                "severity": "low",
                "status": "active",
                "riskCategory": "risk-acceptance",
                "expiresAt": "2026-12-31T00:00:00Z",
                "findingId": rule_id,
                "renewalCount": 0,
            }
        ],
    }
    (state_dir / "decision-store.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_events(events_path: Path) -> list[dict]:
    """Return every line of ``framework-events.ndjson`` parsed as JSON."""
    if not events_path.exists():
        return []
    return [
        json.loads(ln) for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]


def _seed_findings_doc(root: Path, rule_id: str = "P8-RULE") -> Path:
    """Write a minimal gate-findings.json with one accept-eligible finding."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    findings_path = state_dir / "gate-findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "schema": "ai-engineering/gate-findings/v1",
                "session_id": "00000000-0000-4000-8000-000000000007",
                "produced_by": "ai-pr",
                "produced_at": "2026-04-27T12:00:00Z",
                "branch": "feat/spec-101-installer-robustness",
                "commit_sha": "deadbeef",
                "findings": [
                    {
                        "check": "ruff",
                        "rule_id": rule_id,
                        "file": "src/p8.py",
                        "line": 1,
                        "column": None,
                        "severity": "low",
                        "message": "telemetry fixture",
                        "auto_fixable": False,
                        "auto_fix_command": None,
                    }
                ],
                "auto_fixed": [],
                "cache_hits": [],
                "cache_misses": [],
                "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
            }
        ),
        encoding="utf-8",
    )
    return findings_path


def test_risk_acceptance_emits_canonical_framework_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepting a finding emits one event with category=risk-acceptance."""
    from ai_engineering.cli_factory import create_app

    monkeypatch.chdir(tmp_path)
    app = create_app()

    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "P8-SOLO",
            "--severity",
            "low",
            "--justification",
            "Phase 8 single-accept telemetry check.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan refactor.",
        ],
    )
    assert result.exit_code == 0, result.output

    events = _read_events(tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson")
    risk_events = [e for e in events if e.get("detail", {}).get("category") == "risk-acceptance"]
    assert risk_events, f"expected at least one risk-acceptance event, got: {events}"
    accept_events = [e for e in risk_events if e["detail"].get("control") == "finding-accepted"]
    assert accept_events, "expected a finding-accepted control event"
    assert accept_events[0]["detail"].get("finding_id") == "P8-SOLO"


def test_accept_all_emits_batch_event_with_dec_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bulk accept emits one event per finding sharing a single ``batch_id``."""
    from ai_engineering.cli_factory import create_app

    findings_path = _seed_findings_doc(tmp_path, rule_id="P8-BATCH")
    monkeypatch.chdir(tmp_path)
    app = create_app()

    result = runner.invoke(
        app,
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Phase 8 batch telemetry check.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Refactor in 2026-Q3.",
        ],
    )
    assert result.exit_code == 0, result.output

    events = _read_events(tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson")
    accept_all_events = [
        e
        for e in events
        if e.get("detail", {}).get("category") == "risk-acceptance"
        and e["detail"].get("control") == "finding-accepted"
        and e.get("source") == "risk-accept-all"
    ]
    assert accept_all_events, f"expected batch accept event, got: {events}"
    batch_ids = {e["detail"].get("batch_id") for e in accept_all_events}
    assert len(batch_ids) == 1, "all batch acceptances must share a batch_id"
    assert next(iter(batch_ids))


def test_telemetry_event_includes_finding_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per-finding telemetry includes rule_id, severity, dec_id, expires_at."""
    from unittest.mock import patch

    from ai_engineering.policy import orchestrator

    _seed_decision_store(tmp_path, dec_id="DEC-2026-04-26-P8M0", rule_id="P8-META")
    monkeypatch.chdir(tmp_path)

    def _fake_run_check(check_name, staged_files=None, *, cache_dir=None, mode="local"):
        if check_name == "ruff":
            return {
                "outcome": "fail",
                "exit_code": 1,
                "stdout": "",
                "stderr": "",
                "findings": [
                    {
                        "check": "ruff",
                        "rule_id": "P8-META",
                        "file": "src/p8meta.py",
                        "line": 9,
                        "severity": "low",
                        "message": "metadata fixture",
                        "auto_fixable": False,
                        "auto_fix_command": None,
                    }
                ],
            }
        return {"outcome": "pass", "exit_code": 0, "stdout": "", "stderr": "", "findings": []}

    with patch.object(orchestrator, "_run_check", side_effect=_fake_run_check):
        orchestrator.run_gate(
            staged_files=["src/p8meta.py"],
            mode="local",
            project_root=tmp_path,
            cache_disabled=True,
            produced_by="ai-pr",
        )

    events = _read_events(tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson")
    bypass_events = [
        e
        for e in events
        if e.get("detail", {}).get("category") == "risk-acceptance"
        and e["detail"].get("control") == "finding-bypassed"
    ]
    assert bypass_events, f"expected finding-bypassed event, got: {events}"
    detail = bypass_events[0]["detail"]
    assert detail.get("dec_id") == "DEC-2026-04-26-P8M0"
    assert detail.get("finding_id") == "P8-META"
    assert detail.get("severity") == "low"
    # ``expires_at`` should be carried through as ISO-8601.
    assert isinstance(detail.get("expires_at"), str)
    assert detail["expires_at"].startswith("2026-12-31")


def test_telemetry_event_well_formed_json_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each line in framework-events.ndjson is valid JSON with mandatory keys."""
    from ai_engineering.cli_factory import create_app

    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "P8-WELL",
            "--severity",
            "low",
            "--justification",
            "Phase 8 well-formed-NDJSON telemetry assertion.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan refactor.",
        ],
    )
    assert result.exit_code == 0, result.output

    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    assert events_path.exists(), "telemetry stream must be created on first emit"
    raw_lines = [ln for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert raw_lines, "at least one telemetry event must be persisted"
    risk_events = []
    for line in raw_lines:
        event = json.loads(line)  # raises if malformed.
        assert "kind" in event
        assert "detail" in event
        if event.get("detail", {}).get("category") == "risk-acceptance":
            risk_events.append(event)
            assert "control" in event["detail"]
    assert risk_events, "expected at least one risk-acceptance event in the stream"
