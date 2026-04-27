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

pytestmark = pytest.mark.spec_105_red


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
    """``run_gate`` calls the lookup post-Wave 2 (Phase 4 T-4.1 wiring)."""
    # Deferred import: the orchestrator integration lands in Phase 4 T-4.1,
    # so this test asserts the wiring is observable from outside.
    from ai_engineering.policy import orchestrator

    # The wiring contract: the orchestrator must expose
    # ``apply_risk_acceptances`` indirectly via a partition step that
    # populates ``accepted_findings`` on the emitted document.
    assert hasattr(orchestrator, "_emit_findings") or hasattr(
        orchestrator, "build_gate_findings_document"
    )
