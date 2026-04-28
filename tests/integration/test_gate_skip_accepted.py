"""RED skeleton for spec-105 Phase 4 — gate skip-accepted full E2E.

Covers G-2 end-to-end: after an ``ai-eng risk accept`` invocation, the
next ``ai-eng gate run`` partitions the accepted finding off the
blocking surface, prints a compact "ACCEPTED" annotation, and emits a
matching telemetry event to ``framework-events.ndjson``.

Status: RED (orchestrator wiring + CLI compact output land in Phase 4
T-4.1 / T-4.2 / T-4.4). Today the orchestrator emits all findings as
blocking and the CLI compact format is only sketched in spec D-105-08.
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 4 (T-4.11) once both wiring + output land.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _runner_invoke(args: list[str]):
    """Invoke the CLI app. Deferred imports per Phase 1 lesson."""
    from typer.testing import CliRunner

    from ai_engineering.cli_factory import create_app

    return CliRunner().invoke(create_app(), args)


def _seed_decision_for_finding(root: Path, dec_id: str, rule_id: str) -> None:
    """Write a single active risk-acceptance keyed by finding context."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": "1.1",
        "decisions": [
            {
                "id": dec_id,
                "context": f"finding:{rule_id}",
                "decision": "Accepted via spec-105 E2E test.",
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


def test_gate_run_emits_accepted_finding_after_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gate run after `ai-eng risk accept` partitions the matching finding.

    Full E2E: invoke ``ai-eng risk accept --finding-id G2-RULE``, then
    drive ``orchestrator.run_gate`` with a finding whose ``rule_id`` matches.
    Assert the gate-findings.json document carries v1.1 schema and the
    matching finding lands in ``accepted_findings`` (not ``findings``).
    """
    from unittest.mock import patch

    from ai_engineering.policy import orchestrator

    monkeypatch.chdir(tmp_path)
    accept_result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "G2-RULE",
            "--severity",
            "low",
            "--justification",
            "E2E acceptance for the gate-skip flow.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan refactor.",
        ]
    )
    assert accept_result.exit_code == 0, accept_result.output

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
                        "rule_id": "G2-RULE",
                        "file": "src/example.py",
                        "line": 1,
                        "severity": "low",
                        "message": "fixture finding",
                        "auto_fixable": False,
                        "auto_fix_command": None,
                    },
                ],
            }
        return {"outcome": "pass", "exit_code": 0, "stdout": "", "stderr": "", "findings": []}

    with patch.object(orchestrator, "_run_check", side_effect=_fake_run_check):
        document = orchestrator.run_gate(
            staged_files=["src/example.py"],
            mode="local",
            project_root=tmp_path,
            cache_disabled=True,
            produced_by="ai-pr",
        )

    assert document.schema_ == "ai-engineering/gate-findings/v1.1"
    assert any(a.rule_id == "G2-RULE" for a in document.accepted_findings)
    assert not any(f.rule_id == "G2-RULE" for f in document.findings)


def test_gate_run_emits_telemetry_for_accepted_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gate run emits a ``finding-bypassed`` event per accepted finding.

    Drives ``orchestrator.run_gate`` directly with a mocked checker; asserts
    the framework-events.ndjson stream contains a control_outcome event
    with ``category=risk-acceptance`` + ``control=finding-bypassed`` whose
    metadata.dec_id matches the seeded DEC.
    """
    from unittest.mock import patch

    from ai_engineering.policy import orchestrator

    monkeypatch.chdir(tmp_path)
    _seed_decision_for_finding(tmp_path, dec_id="DEC-2026-04-26-G02A", rule_id="G2-A")

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
                        "rule_id": "G2-A",
                        "file": "src/example.py",
                        "line": 5,
                        "severity": "low",
                        "message": "telemetry fixture",
                        "auto_fixable": False,
                        "auto_fix_command": None,
                    },
                ],
            }
        return {"outcome": "pass", "exit_code": 0, "stdout": "", "stderr": "", "findings": []}

    with patch.object(orchestrator, "_run_check", side_effect=_fake_run_check):
        orchestrator.run_gate(
            staged_files=["src/example.py"],
            mode="local",
            project_root=tmp_path,
            cache_disabled=True,
            produced_by="ai-pr",
        )

    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    assert events_path.exists()
    events = [
        json.loads(ln) for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    bypass_events = [
        e
        for e in events
        if e.get("detail", {}).get("category") == "risk-acceptance"
        and e.get("detail", {}).get("control") == "finding-bypassed"
    ]
    assert bypass_events, f"expected at least one bypass event, got: {events}"
    assert any(e.get("detail", {}).get("dec_id") == "DEC-2026-04-26-G02A" for e in bypass_events)


def test_gate_compact_output_renders_accepted_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compact CLI output exposes the ``ACCEPTED`` section per D-105-08.

    Calls ``format_gate_result_compact`` directly with a partitioned set;
    asserts the rendered output contains the BLOCKING + ACCEPTED sections
    + a Next-step line.
    """
    from datetime import UTC, datetime

    from ai_engineering.policy import orchestrator
    from ai_engineering.state.models import (
        AcceptedFinding,
        GateFinding,
        GateSeverity,
    )

    monkeypatch.chdir(tmp_path)
    _seed_decision_for_finding(tmp_path, dec_id="DEC-2026-04-26-G02C", rule_id="G2-C")

    blocking = [
        GateFinding(
            check="ruff",
            rule_id="F841",
            file="src/blk.py",
            line=2,
            severity=GateSeverity.LOW,
            message="unused var",
            auto_fixable=True,
            auto_fix_command="ruff check --fix",
        ),
    ]
    accepted = [
        AcceptedFinding(
            check="ruff",
            rule_id="G2-C",
            file="src/acc.py",
            line=3,
            severity=GateSeverity.LOW,
            message="line too long",
            dec_id="DEC-2026-04-26-G02C",
            expires_at=datetime(2026, 12, 31, tzinfo=UTC),
        ),
    ]

    text = orchestrator.format_gate_result_compact(
        blocking, accepted, expiring_soon=[], no_color=True
    )
    assert "Gate run: 2 findings (1 blocking, 1 accepted via decision-store)" in text
    assert "BLOCKING (1):" in text
    assert "F841" in text
    assert "ACCEPTED (1)" in text
    assert "G2-C" in text
    assert "DEC-2026-04-26-G02C" in text
    assert "Next: fix blockers" in text
