"""Unit tests for spec-105 D-105-07 — `apply_risk_acceptances` core logic.

Covers partition logic, expiry handling, telemetry emission, and edge
cases (NULL ``rule_id``, empty store, all-accepted, none-accepted).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Imports of the target module are deferred inside each test (kept from the
# RED scaffold) to keep test files robust to module-rename refactors and to
# minimise import-time side effects in the unit-test layer.


def _make_finding(
    *,
    check: str = "ruff",
    rule_id: str = "E501",
    file: str = "src/long.py",
    line: int = 120,
    severity: str = "low",
    message: str = "line too long",
    auto_fixable: bool = False,
):
    """Build a ``GateFinding`` for tests."""
    from ai_engineering.state.models import GateFinding

    return GateFinding(
        check=check,
        rule_id=rule_id,
        file=file,
        line=line,
        column=None,
        severity=severity,
        message=message,
        auto_fixable=auto_fixable,
        auto_fix_command=("noop" if auto_fixable else None),
    )


def _make_store(decisions=None):
    """Build a ``DecisionStore`` for tests."""
    from ai_engineering.state.models import DecisionStore

    return DecisionStore(decisions=decisions or [])


def _accept_decision(
    rule_id: str,
    *,
    dec_id: str = "DEC-2026-04-27-T0001",
    expires_in_days: int | None = 30,
    severity: str = "low",
    status: str = "active",
):
    """Build an active risk-acceptance ``Decision`` covering ``rule_id``."""
    from ai_engineering.state.decision_logic import compute_context_hash
    from ai_engineering.state.models import Decision, DecisionStatus, RiskCategory, RiskSeverity

    expires_at = (
        None if expires_in_days is None else datetime.now(tz=UTC) + timedelta(days=expires_in_days)
    )
    return Decision(
        id=dec_id,
        context=f"finding:{rule_id}",
        decision="Accepted for sprint cutoff",
        decidedAt=datetime.now(tz=UTC),
        spec="spec-105",
        context_hash=compute_context_hash(f"finding:{rule_id}"),
        expires_at=expires_at,
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=RiskSeverity(severity),
        accepted_by="dev@example.com",
        follow_up_action="Refactor in 2026-Q3",
        status=DecisionStatus(status),
    )


def test_apply_partitions_findings_into_blocking_and_accepted() -> None:
    """`apply_risk_acceptances` returns (blocking, accepted) tuples respecting active DEC."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    blocking, accepted = apply_risk_acceptances([], None, now=datetime.now(tz=UTC))
    assert blocking == []
    assert accepted == []

    accepted_finding = _make_finding(rule_id="E501")
    blocking_finding = _make_finding(rule_id="F841")
    store = _make_store([_accept_decision("E501", dec_id="DEC-A")])

    blocking_out, accepted_out = apply_risk_acceptances([accepted_finding, blocking_finding], store)

    assert len(blocking_out) == 1
    assert blocking_out[0].rule_id == "F841"
    assert len(accepted_out) == 1
    assert accepted_out[0].rule_id == "E501"
    assert accepted_out[0].dec_id == "DEC-A"


def test_apply_skips_expired_decisions() -> None:
    """Findings matching an expired DEC remain blocking (not accepted)."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    finding = _make_finding(rule_id="E501")
    expired = _accept_decision("E501", dec_id="DEC-EXP", expires_in_days=-1)
    store = _make_store([expired])

    blocking, accepted = apply_risk_acceptances([finding], store)
    assert len(blocking) == 1
    assert blocking[0].rule_id == "E501"
    assert accepted == []


def test_apply_skips_revoked_or_remediated_decisions() -> None:
    """Non-active decisions never bypass findings."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    finding = _make_finding(rule_id="E501")
    revoked = _accept_decision("E501", dec_id="DEC-REV", status="revoked")
    store = _make_store([revoked])

    blocking, accepted = apply_risk_acceptances([finding], store)
    assert len(blocking) == 1
    assert accepted == []


def test_apply_treats_non_risk_acceptance_categories_as_blocking() -> None:
    """A flow-decision in the store does not bypass a matching finding."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances
    from ai_engineering.state.decision_logic import compute_context_hash
    from ai_engineering.state.models import Decision, DecisionStatus, RiskCategory

    finding = _make_finding(rule_id="E501")
    flow_decision = Decision(
        id="DEC-FLOW",
        context="finding:E501",
        decision="Use option A",
        decidedAt=datetime.now(tz=UTC),
        spec="spec-105",
        context_hash=compute_context_hash("finding:E501"),
        risk_category=RiskCategory.FLOW_DECISION,
        status=DecisionStatus.ACTIVE,
    )
    store = _make_store([flow_decision])

    blocking, accepted = apply_risk_acceptances([finding], store)
    assert len(blocking) == 1
    assert accepted == []


def test_apply_emits_control_outcome_telemetry_per_accepted(tmp_path: Path) -> None:
    """Each accepted finding emits exactly one telemetry event."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    events_path = state_dir / "framework-events.ndjson"

    accepted_finding_a = _make_finding(rule_id="E501", file="src/a.py", line=10)
    accepted_finding_b = _make_finding(rule_id="F841", file="src/b.py", line=20)
    blocking_finding = _make_finding(rule_id="UNCOVERED", file="src/c.py", line=30)
    store = _make_store(
        [
            _accept_decision("E501", dec_id="DEC-A"),
            _accept_decision("F841", dec_id="DEC-B"),
        ]
    )

    blocking, accepted = apply_risk_acceptances(
        [accepted_finding_a, accepted_finding_b, blocking_finding],
        store,
        project_root=tmp_path,
    )

    assert len(blocking) == 1
    assert len(accepted) == 2

    lines = [ln for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2, "Expected exactly one event per accepted finding"
    payloads = [json.loads(ln) for ln in lines]
    for payload in payloads:
        assert payload["detail"]["category"] == "risk-acceptance"
        assert payload["detail"]["control"] == "finding-bypassed"
        assert payload["detail"]["dec_id"] in {"DEC-A", "DEC-B"}
        assert payload["detail"]["finding_id"] in {"E501", "F841"}
        assert payload["detail"]["severity"] == "low"


def test_apply_does_not_emit_telemetry_when_project_root_none() -> None:
    """Without ``project_root`` the function still partitions but writes no events."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    finding = _make_finding(rule_id="E501")
    store = _make_store([_accept_decision("E501", dec_id="DEC-A")])

    blocking, accepted = apply_risk_acceptances([finding], store)
    assert blocking == []
    assert len(accepted) == 1


def test_finding_is_accepted_canonical_context_format() -> None:
    """`finding_is_accepted` looks up via `f\"finding:{rule_id}\"` + context_hash."""
    from ai_engineering.policy.checks._accept_lookup import finding_is_accepted

    assert finding_is_accepted(None, None, now=datetime.now(tz=UTC)) is None

    finding = _make_finding(rule_id="E501")
    store = _make_store([_accept_decision("E501", dec_id="DEC-X")])
    decision = finding_is_accepted(finding, store)
    assert decision is not None
    assert decision.id == "DEC-X"


def test_finding_is_accepted_returns_none_for_null_or_empty_rule_id() -> None:
    """Findings without a stable ``rule_id`` are never accepted (OQ-1 safety)."""
    from ai_engineering.policy.checks._accept_lookup import finding_is_accepted

    finding = _make_finding(rule_id="")
    store = _make_store([_accept_decision("anything", dec_id="DEC-Z")])
    assert finding_is_accepted(finding, store) is None


def test_apply_handles_empty_store_as_all_blocking() -> None:
    """Empty store → every finding is blocking, no telemetry."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    findings = [_make_finding(rule_id=f"R-{i}") for i in range(3)]
    store = _make_store([])

    blocking, accepted = apply_risk_acceptances(findings, store)
    assert len(blocking) == 3
    assert accepted == []


def test_apply_all_accepted_returns_no_blocking() -> None:
    """When every finding has an active acceptance, blocking is empty."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    findings = [_make_finding(rule_id=f"R-{i}") for i in range(3)]
    store = _make_store([_accept_decision(f"R-{i}", dec_id=f"DEC-{i}") for i in range(3)])

    blocking, accepted = apply_risk_acceptances(findings, store)
    assert blocking == []
    assert len(accepted) == 3


def test_apply_handles_store_none_gracefully() -> None:
    """`store=None` is the no-acceptance case (everything blocking)."""
    from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances

    findings = [_make_finding(rule_id="E501")]
    blocking, accepted = apply_risk_acceptances(findings, None)
    assert len(blocking) == 1
    assert accepted == []
