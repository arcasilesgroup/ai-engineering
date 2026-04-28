"""RED skeleton for spec-105 Phase 4 — orchestrator-level risk acceptance lookup.

Covers G-2: when the orchestrator runs after a previous ``ai-eng risk
accept-all`` invocation, findings covered by an active risk-acceptance
DEC are partitioned into the ``accepted_findings`` array (no longer
blocking) while uncovered findings remain on the blocking surface.

Status: RED (orchestrator wiring lands in Phase 4 T-4.1 / T-4.2 — the
``apply_risk_acceptances`` lookup module exists from Phase 2 but is not
yet invoked from ``policy/orchestrator.py:run_gate``).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 4 (T-4.11) once the orchestrator wires the
lookup post-Wave 2 collect.

Lesson learned in Phase 1: deferred imports of the target wiring keep
pytest collection green while modules are still missing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _seed_decision_store(root: Path, dec_id: str, finding_rule_id: str) -> None:
    """Persist a single active risk-acceptance covering ``finding_rule_id``."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": "1.1",
        "decisions": [
            {
                "id": dec_id,
                "context": f"finding:{finding_rule_id}",
                "decision": "Accepted for the sprint cutoff.",
                "decidedAt": "2026-04-26T00:00:00Z",
                "spec": "spec-105",
                "severity": "low",
                "status": "active",
                "riskCategory": "risk-acceptance",
                "expiresAt": "2026-12-31T00:00:00Z",
                "findingId": finding_rule_id,
                "renewalCount": 0,
            }
        ],
    }
    (state_dir / "decision-store.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_orchestrator_partitions_accepted_findings_post_wave2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After Wave 2 the orchestrator partitions findings via the lookup."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances
    from ai_engineering.state.io import read_json_model
    from ai_engineering.state.models import DecisionStore, GateFinding, GateSeverity

    _seed_decision_store(tmp_path, dec_id="DEC-2026-04-26-DEAD", finding_rule_id="E501")
    monkeypatch.chdir(tmp_path)
    store = read_json_model(
        tmp_path / ".ai-engineering" / "state" / "decision-store.json", DecisionStore
    )
    findings = [
        GateFinding(
            check="ruff",
            rule_id="E501",
            file="src/long.py",
            line=1,
            severity=GateSeverity.LOW,
            message="line too long",
            auto_fixable=True,
            auto_fix_command="ruff check --fix src/long.py",
        ),
        GateFinding(
            check="ruff",
            rule_id="F841",
            file="src/unused.py",
            line=2,
            severity=GateSeverity.LOW,
            message="unused var",
            auto_fixable=True,
            auto_fix_command="ruff check --fix src/unused.py",
        ),
    ]
    blocking, accepted = apply_risk_acceptances(findings, store, project_root=tmp_path)
    # G-2: the accepted finding leaves the blocking surface, the other remains.
    assert len(blocking) == 1
    assert blocking[0].rule_id == "F841"
    assert len(accepted) == 1
    assert accepted[0].rule_id == "E501"
    assert accepted[0].dec_id == "DEC-2026-04-26-DEAD"


def test_orchestrator_emit_telemetry_per_accepted_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each accepted finding produces a ``finding-bypassed`` telemetry event."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances
    from ai_engineering.state.io import read_json_model
    from ai_engineering.state.models import DecisionStore, GateFinding, GateSeverity

    _seed_decision_store(tmp_path, dec_id="DEC-2026-04-26-FEED", finding_rule_id="E501")
    monkeypatch.chdir(tmp_path)
    store = read_json_model(
        tmp_path / ".ai-engineering" / "state" / "decision-store.json", DecisionStore
    )
    findings = [
        GateFinding(
            check="ruff",
            rule_id="E501",
            file="src/long.py",
            line=1,
            severity=GateSeverity.LOW,
            message="line too long",
            auto_fixable=True,
            auto_fix_command="ruff check --fix src/long.py",
        ),
    ]
    apply_risk_acceptances(findings, store, project_root=tmp_path)
    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    assert events_path.exists()
    events = [
        json.loads(ln) for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert any(
        e.get("detail", {}).get("category") == "risk-acceptance"
        and e.get("detail", {}).get("control") == "finding-bypassed"
        and e.get("detail", {}).get("dec_id") == "DEC-2026-04-26-FEED"
        for e in events
    )


def test_orchestrator_run_gate_invokes_lookup_after_wave2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``run_gate`` calls the lookup post-Wave 2 and emits v1.1 schema.

    Wires a fixture project with one staged file, one active DEC covering
    rule_id E501, mocks ``_run_check`` to return one E501 finding plus one
    F841 finding, and asserts:
      * ``run_gate`` returns a document with ``schema: v1.1``.
      * The accepted finding (E501) is partitioned off the blocking surface.
      * The blocking surface still contains F841.
    """
    from unittest.mock import patch

    from ai_engineering.policy import orchestrator
    from ai_engineering.state.models import GateSeverity

    _seed_decision_store(tmp_path, dec_id="DEC-2026-04-26-AAAA", finding_rule_id="E501")
    monkeypatch.chdir(tmp_path)

    # Stage one file so run_gate dispatches the cache-aware path.
    staged = ["src/example.py"]

    def _fake_run_check(check_name, staged_files=None, *, cache_dir=None, mode="local"):
        # Return findings only for the ruff check; other checks return empty.
        if check_name == "ruff":
            return {
                "outcome": "fail",
                "exit_code": 1,
                "stdout": "",
                "stderr": "",
                "findings": [
                    {
                        "check": "ruff",
                        "rule_id": "E501",
                        "file": "src/example.py",
                        "line": 1,
                        "severity": "low",
                        "message": "line too long",
                        "auto_fixable": True,
                        "auto_fix_command": "ruff check --fix",
                    },
                    {
                        "check": "ruff",
                        "rule_id": "F841",
                        "file": "src/example.py",
                        "line": 2,
                        "severity": "low",
                        "message": "unused var",
                        "auto_fixable": True,
                        "auto_fix_command": "ruff check --fix",
                    },
                ],
            }
        return {"outcome": "pass", "exit_code": 0, "stdout": "", "stderr": "", "findings": []}

    with patch.object(orchestrator, "_run_check", side_effect=_fake_run_check):
        document = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            project_root=tmp_path,
            cache_disabled=True,
            produced_by="ai-pr",
        )

    # G-7: schema v1.1 because accepted_findings is populated.
    assert document.schema_ == "ai-engineering/gate-findings/v1.1"
    # G-2: the E501 finding is partitioned into accepted_findings.
    assert any(a.rule_id == "E501" for a in document.accepted_findings)
    accepted_e501 = next(a for a in document.accepted_findings if a.rule_id == "E501")
    assert accepted_e501.dec_id == "DEC-2026-04-26-AAAA"
    assert accepted_e501.severity == GateSeverity.LOW
    # G-2: the F841 finding remains on the blocking surface.
    assert any(f.rule_id == "F841" for f in document.findings)
    assert not any(f.rule_id == "E501" for f in document.findings)


def test_orchestrator_run_gate_emits_v1_when_no_acceptances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no DECs match findings, ``run_gate`` emits ``schema: v1``."""
    from unittest.mock import patch

    from ai_engineering.policy import orchestrator

    monkeypatch.chdir(tmp_path)
    # No decision-store seeded — every finding is blocking.
    staged = ["src/example.py"]

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
                        "rule_id": "F841",
                        "file": "src/example.py",
                        "line": 2,
                        "severity": "low",
                        "message": "unused var",
                        "auto_fixable": True,
                        "auto_fix_command": "ruff check --fix",
                    },
                ],
            }
        return {"outcome": "pass", "exit_code": 0, "stdout": "", "stderr": "", "findings": []}

    with patch.object(orchestrator, "_run_check", side_effect=_fake_run_check):
        document = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            project_root=tmp_path,
            cache_disabled=True,
            produced_by="ai-pr",
        )

    # No acceptances + no expiring → v1 schema (binary-equivalent).
    assert document.schema_ == "ai-engineering/gate-findings/v1"
    assert document.accepted_findings == []
    assert document.expiring_soon == []
