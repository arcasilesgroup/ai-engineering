"""Decision reuse logic with SHA-256 context hashing.

Provides:
- Context hashing for decision relevance tracking.
- Decision lookup by hash (reuse existing decisions).
- Decision creation with automatic hash generation.
- Expiry checking for time-bounded decisions.
- Risk acceptance lifecycle: create, renew, revoke, remediate.
- Expired/expiring-soon decision queries.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from .models import (
    Decision,
    DecisionStatus,
    DecisionStore,
    RiskCategory,
    RiskSeverity,
)

# Default expiry durations per severity level (days).
_SEVERITY_EXPIRY_DAYS: dict[RiskSeverity, int] = {
    RiskSeverity.CRITICAL: 15,
    RiskSeverity.HIGH: 30,
    RiskSeverity.MEDIUM: 60,
    RiskSeverity.LOW: 90,
}

# Maximum number of renewals allowed per risk acceptance.
_MAX_RENEWALS: int = 2

# Days before expiry to trigger a warning.
_WARN_BEFORE_EXPIRY_DAYS: int = 7


def compute_context_hash(context: str) -> str:
    """Compute a SHA-256 hash of a decision context string.

    Used to detect when the same decision context arises again,
    enabling automatic reuse without re-prompting.

    Args:
        context: The decision context description.

    Returns:
        Hex-encoded SHA-256 hash of the context.
    """
    return hashlib.sha256(context.encode("utf-8")).hexdigest()


def find_reusable_decision(
    store: DecisionStore,
    context: str,
    *,
    now: datetime | None = None,
) -> Decision | None:
    """Find a reusable decision for the given context.

    Looks up by context hash and checks expiry if set.

    Args:
        store: The decision store to search.
        context: The decision context to match.
        now: Current time for expiry checks. Defaults to utcnow.

    Returns:
        The matching non-expired decision, or None.
    """
    now = now or datetime.now(tz=UTC)
    context_hash = compute_context_hash(context)
    decision = store.find_by_context_hash(context_hash)
    if decision is None:
        return None
    if decision.expires_at is not None and decision.expires_at < now:
        return None
    return decision


def create_decision(
    store: DecisionStore,
    *,
    decision_id: str,
    context: str,
    decision_text: str,
    spec: str,
    expires_at: datetime | None = None,
) -> Decision:
    """Create a new decision and add it to the store.

    Automatically computes context hash for future reuse lookup.

    Args:
        store: The decision store to add to.
        decision_id: Unique identifier for the decision (e.g., "S1-001").
        context: Description of the decision context.
        decision_text: The decision made.
        spec: Spec identifier (e.g., "001-rewrite-v2").
        expires_at: Optional expiry datetime.

    Returns:
        The newly created decision.
    """
    decision = Decision(
        id=decision_id,
        context=context,
        decision=decision_text,
        decidedAt=datetime.now(tz=UTC),
        spec=spec,
        context_hash=compute_context_hash(context),
        expires_at=expires_at,
    )
    store.decisions.append(decision)
    return decision


def next_decision_id(store: DecisionStore, session: str) -> str:
    """Generate the next sequential decision ID for a session.

    Format: "{session}-{NNN}" where NNN is zero-padded.

    Args:
        store: The decision store to check existing IDs.
        session: Session identifier (e.g., "S1").

    Returns:
        Next available decision ID (e.g., "S1-003").
    """
    prefix = f"{session}-"
    existing = [d.id for d in store.decisions if d.id.startswith(prefix)]
    if not existing:
        return f"{prefix}001"

    max_num = 0
    for did in existing:
        suffix = did[len(prefix) :]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"


# ---------------------------------------------------------------------------
# Risk acceptance lifecycle
# ---------------------------------------------------------------------------


def default_expiry_for_severity(
    severity: RiskSeverity,
    *,
    config: dict[str, int] | None = None,
) -> timedelta:
    """Return the default expiry duration for a severity level.

    Args:
        severity: The risk severity.
        config: Optional override mapping severity name → days.
            Falls back to ``_SEVERITY_EXPIRY_DAYS``.

    Returns:
        Timedelta for the expiry period.
    """
    if config and severity.value in config:
        return timedelta(days=config[severity.value])
    return timedelta(days=_SEVERITY_EXPIRY_DAYS[severity])


def list_expired_decisions(
    store: DecisionStore,
    *,
    now: datetime | None = None,
) -> list[Decision]:
    """Return risk acceptances that are expired and still active.

    Args:
        store: The decision store to scan.
        now: Current time for expiry checks. Defaults to utcnow.

    Returns:
        List of expired active risk acceptance decisions.
    """
    now = now or datetime.now(tz=UTC)
    return [
        d
        for d in store.risk_decisions()
        if d.status == DecisionStatus.ACTIVE and d.expires_at is not None and d.expires_at < now
    ]


def list_expiring_soon(
    store: DecisionStore,
    *,
    days: int = _WARN_BEFORE_EXPIRY_DAYS,
    now: datetime | None = None,
) -> list[Decision]:
    """Return risk acceptances that will expire within N days.

    Only returns decisions that are still active and not yet expired.

    Args:
        store: The decision store to scan.
        days: Warning threshold in days.
        now: Current time. Defaults to utcnow.

    Returns:
        List of soon-to-expire active risk acceptance decisions.
    """
    now = now or datetime.now(tz=UTC)
    threshold = now + timedelta(days=days)
    return [
        d
        for d in store.risk_decisions()
        if d.status == DecisionStatus.ACTIVE
        and d.expires_at is not None
        and now <= d.expires_at <= threshold
    ]


def create_risk_acceptance(
    store: DecisionStore,
    *,
    decision_id: str,
    context: str,
    decision_text: str,
    severity: RiskSeverity,
    follow_up: str,
    spec: str,
    accepted_by: str,
    expires_at: datetime | None = None,
    config: dict[str, int] | None = None,
) -> Decision:
    """Create a risk acceptance decision.

    Calculates ``expires_at`` from severity if not provided.
    Sets ``risk_category`` to ``RISK_ACCEPTANCE`` automatically.

    Args:
        store: The decision store to add to.
        decision_id: Unique identifier.
        context: Risk context description.
        decision_text: The acceptance decision text.
        severity: Severity of the finding.
        follow_up: Required remediation plan.
        spec: Spec identifier.
        accepted_by: Actor who accepted the risk.
        expires_at: Optional explicit expiry. Computed from severity if omitted.
        config: Optional severity → days mapping.

    Returns:
        The newly created risk acceptance decision.
    """
    if expires_at is None:
        expires_at = datetime.now(tz=UTC) + default_expiry_for_severity(
            severity,
            config=config,
        )

    decision = Decision(
        id=decision_id,
        context=context,
        decision=decision_text,
        decidedAt=datetime.now(tz=UTC),
        spec=spec,
        context_hash=compute_context_hash(context),
        expires_at=expires_at,
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=severity,
        accepted_by=accepted_by,
        follow_up_action=follow_up,
        status=DecisionStatus.ACTIVE,
        renewal_count=0,
    )
    store.decisions.append(decision)
    return decision


def renew_decision(
    store: DecisionStore,
    *,
    decision_id: str,
    justification: str,
    spec: str,
    actor: str,
    max_renewals: int = _MAX_RENEWALS,
    config: dict[str, int] | None = None,
) -> Decision:
    """Renew (extend) an existing risk acceptance.

    Creates a new decision with ``renewed_from`` pointing to the original.
    Marks the original as ``SUPERSEDED``.
    Fails if max renewals exceeded.

    Args:
        store: The decision store.
        decision_id: ID of the decision to renew.
        justification: Why remediation hasn't happened yet.
        spec: Current spec identifier.
        actor: Actor requesting renewal.
        max_renewals: Maximum allowed renewals (default 2).
        config: Optional severity → days mapping.

    Returns:
        The new renewed decision.

    Raises:
        ValueError: If decision not found, not a risk acceptance,
            or max renewals exceeded.
    """
    original = store.find_by_id(decision_id)
    if original is None:
        msg = f"Decision '{decision_id}' not found"
        raise ValueError(msg)

    if original.risk_category != RiskCategory.RISK_ACCEPTANCE:
        msg = f"Decision '{decision_id}' is not a risk acceptance"
        raise ValueError(msg)

    new_count = original.renewal_count + 1
    if new_count > max_renewals:
        msg = (
            f"Decision '{decision_id}' has reached maximum renewals "
            f"({max_renewals}). Remediation is required."
        )
        raise ValueError(msg)

    # Mark original as superseded
    original.status = DecisionStatus.SUPERSEDED

    severity = original.severity or RiskSeverity.MEDIUM
    expires_at = datetime.now(tz=UTC) + default_expiry_for_severity(
        severity,
        config=config,
    )

    new_id = next_decision_id(store, spec)
    renewed = Decision(
        id=new_id,
        context=original.context,
        decision=f"Renewed: {justification}",
        decidedAt=datetime.now(tz=UTC),
        spec=spec,
        context_hash=original.context_hash,
        expires_at=expires_at,
        risk_category=RiskCategory.RISK_ACCEPTANCE,
        severity=severity,
        accepted_by=actor,
        follow_up_action=original.follow_up_action,
        status=DecisionStatus.ACTIVE,
        renewed_from=decision_id,
        renewal_count=new_count,
    )
    store.decisions.append(renewed)
    return renewed


def revoke_decision(store: DecisionStore, *, decision_id: str) -> Decision:
    """Revoke an active risk acceptance.

    Args:
        store: The decision store.
        decision_id: ID of the decision to revoke.

    Returns:
        The revoked decision.

    Raises:
        ValueError: If decision not found.
    """
    decision = store.find_by_id(decision_id)
    if decision is None:
        msg = f"Decision '{decision_id}' not found"
        raise ValueError(msg)
    decision.status = DecisionStatus.REVOKED
    return decision


def mark_remediated(store: DecisionStore, *, decision_id: str) -> Decision:
    """Mark a risk acceptance as remediated (fix applied).

    Args:
        store: The decision store.
        decision_id: ID of the decision to close.

    Returns:
        The remediated decision.

    Raises:
        ValueError: If decision not found.
    """
    decision = store.find_by_id(decision_id)
    if decision is None:
        msg = f"Decision '{decision_id}' not found"
        raise ValueError(msg)
    decision.status = DecisionStatus.REMEDIATED
    return decision
