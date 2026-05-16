"""Unit tests for the relevance gate (spec-137 D-137-01)."""

from __future__ import annotations

import pytest

from ai_engineering.state.relevance import (
    DEFAULT_SEVERITY,
    SEVERITY_RANK,
    AuditPolicy,
    load_audit_policy_from_manifest,
    relevance_gate,
)


def _make_event(
    *,
    kind: str = "framework_operation",
    severity: str | None = "S1",
    outcome: str = "success",
) -> dict:
    event = {"kind": kind, "outcome": outcome}
    if severity is not None:
        event["severity"] = severity
    return event


def test_allow_all_policy_admits_every_kind_and_severity() -> None:
    policy = AuditPolicy.allow_all()
    for kind in ("skill_invoked", "framework_operation", "ide_hook"):
        for severity in SEVERITY_RANK:
            event = _make_event(kind=kind, severity=severity)
            assert relevance_gate(event, policy), f"allow-all should admit {kind}/{severity}"


def test_kind_not_in_allowlist_is_dropped() -> None:
    policy = AuditPolicy(kind_allowlist=frozenset({"skill_invoked"}))
    assert relevance_gate(_make_event(kind="skill_invoked"), policy)
    assert not relevance_gate(_make_event(kind="ide_hook"), policy)


def test_severity_floor_drops_below_threshold() -> None:
    policy = AuditPolicy(
        kind_allowlist=frozenset({"framework_operation"}),
        severity_floor={"framework_operation": "S2"},
    )
    # S3 is below S2 floor -- drop.
    assert not relevance_gate(_make_event(kind="framework_operation", severity="S3"), policy)
    # S2 meets the floor -- admit.
    assert relevance_gate(_make_event(kind="framework_operation", severity="S2"), policy)
    # S1 above the floor -- admit.
    assert relevance_gate(_make_event(kind="framework_operation", severity="S1"), policy)
    # S0 highest signal -- admit.
    assert relevance_gate(_make_event(kind="framework_operation", severity="S0"), policy)


def test_failure_emission_admits_below_floor() -> None:
    policy = AuditPolicy(
        kind_allowlist=frozenset({"framework_operation"}),
        severity_floor={"framework_operation": "S2"},
        failure_emission="always",
    )
    # S3 below the floor BUT outcome is failure -- admit.
    assert relevance_gate(
        _make_event(kind="framework_operation", severity="S3", outcome="failure"),
        policy,
    )
    # S3 below the floor and outcome is success -- drop.
    assert not relevance_gate(
        _make_event(kind="framework_operation", severity="S3", outcome="success"),
        policy,
    )


def test_failure_emission_never_does_not_carve_out() -> None:
    policy = AuditPolicy(
        kind_allowlist=frozenset({"framework_operation"}),
        severity_floor={"framework_operation": "S2"},
        failure_emission="never",
    )
    # Even a failure outcome below the floor drops with failure_emission=never.
    assert not relevance_gate(
        _make_event(kind="framework_operation", severity="S3", outcome="failure"),
        policy,
    )


def test_missing_severity_defaults_to_state_change() -> None:
    policy = AuditPolicy(
        kind_allowlist=frozenset({"framework_operation"}),
        severity_floor={"framework_operation": "S1"},
    )
    event = _make_event(kind="framework_operation", severity=None)
    # Default severity is S1 -- meets the S1 floor.
    assert relevance_gate(event, policy)
    assert event.get("severity") is None
    # Sanity: default is in the rank table.
    assert DEFAULT_SEVERITY in SEVERITY_RANK


def test_empty_kind_is_rejected() -> None:
    policy = AuditPolicy.allow_all()
    assert not relevance_gate({"kind": "", "outcome": "success"}, policy)
    assert not relevance_gate({"outcome": "success"}, policy)


def test_default_floor_applies_when_no_per_kind_entry() -> None:
    policy = AuditPolicy(
        kind_allowlist=frozenset({"framework_operation", "skill_invoked"}),
        severity_floor={"default": "S2"},
    )
    # Both kinds use the default S2 floor; S3 drops, S2 admits.
    assert not relevance_gate(_make_event(kind="framework_operation", severity="S3"), policy)
    assert not relevance_gate(_make_event(kind="skill_invoked", severity="S3"), policy)
    assert relevance_gate(_make_event(kind="skill_invoked", severity="S2"), policy)


def test_load_audit_policy_from_manifest_with_full_block() -> None:
    manifest = {
        "audit_policy": {
            "kind_allowlist": ["skill_invoked", "framework_operation"],
            "severity_floor": {"framework_operation": "S2", "default": "S1"},
            "sampling": {"policy_decision_allow": 0.10},
            "failure_emission": "always",
        }
    }
    policy = load_audit_policy_from_manifest(manifest)
    assert policy.kind_allowlist == frozenset({"skill_invoked", "framework_operation"})
    assert policy.severity_floor["framework_operation"] == "S2"
    assert policy.sampling["policy_decision_allow"] == pytest.approx(0.10)
    assert policy.failure_emission == "always"


def test_load_audit_policy_from_manifest_missing_block_yields_allow_all() -> None:
    policy = load_audit_policy_from_manifest({})
    assert policy.kind_allowlist == frozenset()
    assert policy.failure_emission == "always"
    # Allow-all admits everything.
    for kind in ("skill_invoked", "framework_operation"):
        for severity in SEVERITY_RANK:
            assert relevance_gate(_make_event(kind=kind, severity=severity), policy)


def test_load_audit_policy_from_manifest_rejects_invalid_severity() -> None:
    manifest = {
        "audit_policy": {
            "severity_floor": {"framework_operation": "S9", "valid": "S2"},
        }
    }
    policy = load_audit_policy_from_manifest(manifest)
    # Invalid value is silently filtered out.
    assert "framework_operation" not in policy.severity_floor
    assert policy.severity_floor.get("valid") == "S2"
