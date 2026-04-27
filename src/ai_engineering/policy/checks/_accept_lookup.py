"""Orchestrator-level risk-acceptance lookup (spec-105 D-105-07).

Provides two functions consumed by ``policy/orchestrator.py`` after Wave 2
collection completes:

* ``finding_is_accepted(finding, store, *, now=None) -> Decision | None``
  — Look up the active risk-acceptance ``Decision`` whose ``context_hash``
  matches the canonical context format ``f"finding:{rule_id}"``. Filters
  by ``status==ACTIVE``, ``risk_category==RISK_ACCEPTANCE`` and a non-
  expired window (``expires_at is None or expires_at > now``).

* ``apply_risk_acceptances(findings, store, *, now=None, project_root=None)``
  — Partition a list of ``GateFinding`` into ``(blocking, accepted)``,
  emitting one ``framework_event`` per accepted finding via
  ``emit_control_outcome`` (category ``risk-acceptance``,
  control ``finding-bypassed``).

Both functions are pure with respect to the inputs (no global state) and
treat ``store=None`` and empty inputs as the no-acceptance case so callers
can wire them in unconditionally without guard logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ai_engineering.state.decision_logic import compute_context_hash
from ai_engineering.state.models import (
    AcceptedFinding,
    DecisionStatus,
    RiskCategory,
)
from ai_engineering.state.observability import emit_control_outcome

if TYPE_CHECKING:
    from ai_engineering.state.models import Decision, DecisionStore, GateFinding


def finding_is_accepted(
    finding: GateFinding | None,
    store: DecisionStore | None,
    *,
    now: datetime | None = None,
) -> Decision | None:
    """Return the active risk-acceptance ``Decision`` for ``finding.rule_id``.

    Looks up by canonical context format ``f"finding:{rule_id}"`` hashed
    via :func:`compute_context_hash`. A match must be active, classified
    as a risk acceptance, and either non-expiring or in-window.

    Args:
        finding: The gate finding to check, or ``None`` (returns ``None``).
        store: The decision store, or ``None`` (returns ``None``).
        now: Reference time for expiry comparison. Defaults to ``utcnow``.

    Returns:
        The matching ``Decision``, or ``None`` if no active acceptance
        covers the finding.
    """
    if finding is None or store is None:
        return None
    rule_id = getattr(finding, "rule_id", None)
    if not rule_id:
        return None

    reference_time = now or datetime.now(tz=UTC)
    canonical_hash = compute_context_hash(f"finding:{rule_id}")

    return next(
        (
            d
            for d in store.decisions
            if d.context_hash == canonical_hash
            and d.status == DecisionStatus.ACTIVE
            and d.risk_category == RiskCategory.RISK_ACCEPTANCE
            and (d.expires_at is None or d.expires_at > reference_time)
        ),
        None,
    )


def apply_risk_acceptances(
    findings: list[GateFinding],
    store: DecisionStore | None,
    *,
    now: datetime | None = None,
    project_root: Path | None = None,
) -> tuple[list[GateFinding], list[AcceptedFinding]]:
    """Partition ``findings`` into ``(blocking, accepted)`` and emit telemetry.

    For each finding covered by an active risk-acceptance, build an
    :class:`AcceptedFinding` carrying the ``dec_id`` and ``expires_at`` of
    the matching decision; emit one canonical ``control_outcome`` event
    per acceptance when ``project_root`` is provided.

    Findings without a ``rule_id`` (NULL/empty) are treated as blocking —
    they cannot be matched to any DEC entry. This mirrors OQ-1: skip the
    bypass attempt with a warning rather than raising, so the gate keeps
    running for the rest of the surface.

    Args:
        findings: All findings emitted by Wave 2 (post-collector).
        store: The decision store, or ``None`` (everything is blocking).
        now: Reference time for expiry comparison.
        project_root: Project root for telemetry emission. ``None`` skips
            the framework-events write (used in unit tests / dry-runs).

    Returns:
        A tuple ``(blocking, accepted)`` whose union equals ``findings``.
    """
    reference_time = now or datetime.now(tz=UTC)
    blocking: list[GateFinding] = []
    accepted: list[AcceptedFinding] = []

    for finding in findings:
        decision = finding_is_accepted(finding, store, now=reference_time)
        if decision is None:
            blocking.append(finding)
            continue

        accepted.append(
            AcceptedFinding(
                check=finding.check,
                rule_id=finding.rule_id,
                file=finding.file,
                line=finding.line,
                severity=finding.severity,
                message=finding.message,
                dec_id=decision.id,
                expires_at=decision.expires_at,
            )
        )

        if project_root is not None:
            emit_control_outcome(
                project_root,
                category="risk-acceptance",
                control="finding-bypassed",
                component=finding.check,
                outcome="bypassed",
                source="orchestrator",
                metadata={
                    "dec_id": decision.id,
                    "finding_id": finding.rule_id,
                    "expires_at": (
                        decision.expires_at.isoformat() if decision.expires_at else None
                    ),
                    "severity": finding.severity.value,
                    "file": finding.file,
                    "line": finding.line,
                },
            )

    return blocking, accepted


__all__ = ["apply_risk_acceptances", "finding_is_accepted"]
