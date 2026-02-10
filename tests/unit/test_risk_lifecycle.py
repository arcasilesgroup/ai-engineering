"""Tests for risk acceptance lifecycle in ai_engineering.state.decision_logic.

Covers:
- default_expiry_for_severity: all severity levels and custom config.
- create_risk_acceptance: field population, expiry calculation.
- renew_decision: renewal count, max renewals, superseded status.
- revoke_decision: status change.
- mark_remediated: status change.
- list_expired_decisions: filtering.
- list_expiring_soon: threshold-based filtering.
- Backward compatibility: schema 1.0 → 1.1 data validation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ai_engineering.state.decision_logic import (
    _SEVERITY_EXPIRY_DAYS,
    create_risk_acceptance,
    default_expiry_for_severity,
    list_expired_decisions,
    list_expiring_soon,
    mark_remediated,
    renew_decision,
    revoke_decision,
)
from ai_engineering.state.models import (
    Decision,
    DecisionStatus,
    DecisionStore,
    RiskCategory,
    RiskSeverity,
)


def _empty_store() -> DecisionStore:
    """Create an empty decision store for testing."""
    return DecisionStore(schemaVersion="1.1", decisions=[])


# ── default_expiry_for_severity ─────────────────────────────────────────


class TestDefaultExpiryForSeverity:
    """Tests for severity-based expiry calculation."""

    def test_critical_15_days(self) -> None:
        delta = default_expiry_for_severity(RiskSeverity.CRITICAL)
        assert delta == timedelta(days=15)

    def test_high_30_days(self) -> None:
        delta = default_expiry_for_severity(RiskSeverity.HIGH)
        assert delta == timedelta(days=30)

    def test_medium_60_days(self) -> None:
        delta = default_expiry_for_severity(RiskSeverity.MEDIUM)
        assert delta == timedelta(days=60)

    def test_low_90_days(self) -> None:
        delta = default_expiry_for_severity(RiskSeverity.LOW)
        assert delta == timedelta(days=90)

    def test_custom_config_overrides(self) -> None:
        config = {"critical": 5, "high": 10}
        delta = default_expiry_for_severity(
            RiskSeverity.CRITICAL,
            config=config,
        )
        assert delta == timedelta(days=5)

    def test_custom_config_falls_back(self) -> None:
        config = {"critical": 5}
        delta = default_expiry_for_severity(
            RiskSeverity.LOW,
            config=config,
        )
        assert delta == timedelta(days=90)


# ── create_risk_acceptance ──────────────────────────────────────────────


class TestCreateRiskAcceptance:
    """Tests for creating risk acceptance decisions."""

    def test_creates_with_correct_fields(self) -> None:
        store = _empty_store()
        d = create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="CVE-2025-12345 in package X",
            decision_text="Accept risk for 30 days",
            severity=RiskSeverity.HIGH,
            follow_up="Upgrade package X to 2.0",
            spec="004",
            accepted_by="dev@example.com",
        )
        assert d.id == "RA-001"
        assert d.risk_category == RiskCategory.RISK_ACCEPTANCE
        assert d.severity == RiskSeverity.HIGH
        assert d.status == DecisionStatus.ACTIVE
        assert d.follow_up_action == "Upgrade package X to 2.0"
        assert d.accepted_by == "dev@example.com"
        assert d.renewal_count == 0
        assert d.expires_at is not None

    def test_auto_calculates_expiry(self) -> None:
        store = _empty_store()
        before = datetime.now(tz=UTC)
        d = create_risk_acceptance(
            store,
            decision_id="RA-002",
            context="test",
            decision_text="test",
            severity=RiskSeverity.CRITICAL,
            follow_up="fix",
            spec="004",
            accepted_by="test",
        )
        expected_min = before + timedelta(days=_SEVERITY_EXPIRY_DAYS[RiskSeverity.CRITICAL])
        assert d.expires_at >= expected_min

    def test_explicit_expiry_overrides(self) -> None:
        store = _empty_store()
        exp = datetime(2099, 12, 31)
        d = create_risk_acceptance(
            store,
            decision_id="RA-003",
            context="test",
            decision_text="test",
            severity=RiskSeverity.LOW,
            follow_up="fix",
            spec="004",
            accepted_by="test",
            expires_at=exp,
        )
        assert d.expires_at == exp

    def test_adds_to_store(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-004",
            context="test",
            decision_text="test",
            severity=RiskSeverity.MEDIUM,
            follow_up="fix",
            spec="004",
            accepted_by="test",
        )
        assert len(store.decisions) == 1


# ── renew_decision ──────────────────────────────────────────────────────


class TestRenewDecision:
    """Tests for decision renewal."""

    def _create_risk(self, store: DecisionStore, *, decision_id: str = "RA-001") -> Decision:
        return create_risk_acceptance(
            store,
            decision_id=decision_id,
            context="test risk",
            decision_text="accept",
            severity=RiskSeverity.HIGH,
            follow_up="fix it",
            spec="004",
            accepted_by="dev",
        )

    def test_creates_new_decision(self) -> None:
        store = _empty_store()
        self._create_risk(store)
        renewed = renew_decision(
            store,
            decision_id="RA-001",
            justification="need more time",
            spec="004",
            actor="dev",
        )
        assert renewed.renewal_count == 1
        assert renewed.renewed_from == "RA-001"
        assert len(store.decisions) == 2

    def test_marks_original_superseded(self) -> None:
        store = _empty_store()
        self._create_risk(store)
        renew_decision(
            store,
            decision_id="RA-001",
            justification="need more time",
            spec="004",
            actor="dev",
        )
        original = store.find_by_id("RA-001")
        assert original is not None
        assert original.status == DecisionStatus.SUPERSEDED

    def test_max_renewals_raises(self) -> None:
        store = _empty_store()
        self._create_risk(store)

        # Renew twice (max 2)
        r1 = renew_decision(
            store,
            decision_id="RA-001",
            justification="first renewal",
            spec="004",
            actor="dev",
        )
        renew_decision(
            store,
            decision_id=r1.id,
            justification="second renewal",
            spec="004",
            actor="dev",
        )

        # Third renewal should fail
        with pytest.raises(ValueError, match="maximum renewals"):
            # Find the latest renewed decision
            latest = next(d for d in store.decisions if d.renewal_count == 2)
            renew_decision(
                store,
                decision_id=latest.id,
                justification="third renewal",
                spec="004",
                actor="dev",
            )

    def test_not_found_raises(self) -> None:
        store = _empty_store()
        with pytest.raises(ValueError, match="not found"):
            renew_decision(
                store,
                decision_id="nonexistent",
                justification="test",
                spec="004",
                actor="dev",
            )

    def test_non_risk_raises(self) -> None:
        store = _empty_store()
        # Add a regular decision (not risk acceptance)
        store.decisions.append(
            Decision(
                id="D-001",
                context="regular decision",
                decision="decided",
                decided_at=datetime.now(tz=UTC),
                spec="004",
            )
        )
        with pytest.raises(ValueError, match="not a risk acceptance"):
            renew_decision(
                store,
                decision_id="D-001",
                justification="test",
                spec="004",
                actor="dev",
            )


# ── revoke_decision ─────────────────────────────────────────────────────


class TestRevokeDecision:
    """Tests for decision revocation."""

    def test_sets_revoked_status(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.MEDIUM,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
        )
        d = revoke_decision(store, decision_id="RA-001")
        assert d.status == DecisionStatus.REVOKED

    def test_not_found_raises(self) -> None:
        store = _empty_store()
        with pytest.raises(ValueError, match="not found"):
            revoke_decision(store, decision_id="nonexistent")


# ── mark_remediated ─────────────────────────────────────────────────────


class TestMarkRemediated:
    """Tests for marking decisions as remediated."""

    def test_sets_remediated_status(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.LOW,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
        )
        d = mark_remediated(store, decision_id="RA-001")
        assert d.status == DecisionStatus.REMEDIATED


# ── list_expired_decisions ──────────────────────────────────────────────


class TestListExpiredDecisions:
    """Tests for listing expired decisions."""

    def test_finds_expired(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.CRITICAL,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
            expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        expired = list_expired_decisions(store)
        assert len(expired) == 1
        assert expired[0].id == "RA-001"

    def test_excludes_non_expired(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.CRITICAL,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
            expires_at=datetime(2099, 12, 31, tzinfo=UTC),
        )
        expired = list_expired_decisions(store)
        assert len(expired) == 0

    def test_excludes_remediated(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.CRITICAL,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
            expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        mark_remediated(store, decision_id="RA-001")
        expired = list_expired_decisions(store)
        assert len(expired) == 0


# ── list_expiring_soon ──────────────────────────────────────────────────


class TestListExpiringSoon:
    """Tests for listing soon-to-expire decisions."""

    def test_finds_expiring_within_threshold(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.HIGH,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
            expires_at=datetime.now(tz=UTC) + timedelta(days=3),
        )
        expiring = list_expiring_soon(store, days=7)
        assert len(expiring) == 1

    def test_excludes_far_future(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.LOW,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
            expires_at=datetime.now(tz=UTC) + timedelta(days=60),
        )
        expiring = list_expiring_soon(store, days=7)
        assert len(expiring) == 0

    def test_excludes_already_expired(self) -> None:
        store = _empty_store()
        create_risk_acceptance(
            store,
            decision_id="RA-001",
            context="test",
            decision_text="accept",
            severity=RiskSeverity.CRITICAL,
            follow_up="fix",
            spec="004",
            accepted_by="dev",
            expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        expiring = list_expiring_soon(store, days=7)
        assert len(expiring) == 0


# ── Backward Compatibility ──────────────────────────────────────────────


class TestBackwardCompatibility:
    """Tests for schema 1.0 → 1.1 backward compatibility."""

    def test_old_decision_without_risk_fields(self) -> None:
        """Schema 1.0 decisions (no risk fields) should validate cleanly."""
        raw = {
            "id": "S1-001",
            "context": "old decision",
            "decision": "decided",
            "decidedAt": "2025-01-01T00:00:00Z",
            "spec": "001",
        }
        d = Decision.model_validate(raw)
        assert d.risk_category is None
        assert d.severity is None
        assert d.status == DecisionStatus.ACTIVE
        assert d.renewal_count == 0

    def test_schema_1_0_store_validates(self) -> None:
        """Schema 1.0 store (no risk fields) should validate."""
        raw = {
            "schemaVersion": "1.0",
            "decisions": [
                {
                    "id": "S1-001",
                    "context": "test",
                    "decision": "decided",
                    "decidedAt": "2025-01-01T00:00:00Z",
                    "spec": "001",
                },
            ],
        }
        store = DecisionStore.model_validate(raw)
        assert len(store.decisions) == 1
        assert store.risk_decisions() == []
