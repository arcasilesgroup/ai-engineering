"""Decision reuse logic with SHA-256 context hashing.

Provides:
- Context hashing for decision relevance tracking.
- Decision lookup by hash (reuse existing decisions).
- Decision creation with automatic hash generation.
- Expiry checking for time-bounded decisions.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from .models import Decision, DecisionStore


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
    now = now or datetime.utcnow()
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
        decidedAt=datetime.utcnow(),
        spec=spec,
        contextHash=compute_context_hash(context),
        expiresAt=expires_at,
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
        suffix = did[len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"
