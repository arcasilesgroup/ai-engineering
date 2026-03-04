"""Risk acceptance checks for gate hooks."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.policy.gates import GateCheckResult, GateResult
from ai_engineering.state.decision_logic import list_expired_decisions, list_expiring_soon
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore


def load_decision_store(project_root: Path) -> DecisionStore | None:
    """Load the decision store from the project, or None if unavailable."""
    ds_path = project_root / ".ai-engineering" / "state" / "decision-store.json"
    if not ds_path.exists():
        return None
    try:
        return read_json_model(ds_path, DecisionStore)
    except (OSError, ValueError):
        return None


def check_expiring_risk_acceptances(
    project_root: Path,
    result: GateResult,
) -> None:
    """Warn about risk acceptances expiring within 7 days (non-blocking)."""
    store = load_decision_store(project_root)
    if store is None:
        result.checks.append(
            GateCheckResult(
                name="risk-expiry-warning",
                passed=True,
                output="No decision store found — skipped",
            )
        )
        return

    expiring = list_expiring_soon(store)
    if not expiring:
        result.checks.append(
            GateCheckResult(
                name="risk-expiry-warning",
                passed=True,
                output="No risk acceptances expiring soon",
            )
        )
        return

    lines = [f"{len(expiring)} risk acceptance(s) expiring within 7 days:"]
    for d in expiring:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
        lines.append(f"  - {d.id}: expires {exp} ({d.context[:60]})")
    lines.append("Consider renewing or remediating before expiry.")

    result.checks.append(
        GateCheckResult(
            name="risk-expiry-warning",
            passed=True,
            output="\n".join(lines),
        )
    )


def check_expired_risk_acceptances(
    project_root: Path,
    result: GateResult,
) -> None:
    """Block push if expired risk acceptances exist (blocking)."""
    store = load_decision_store(project_root)
    if store is None:
        result.checks.append(
            GateCheckResult(
                name="risk-expired-block",
                passed=True,
                output="No decision store found — skipped",
            )
        )
        return

    expired = list_expired_decisions(store)
    if not expired:
        result.checks.append(
            GateCheckResult(
                name="risk-expired-block",
                passed=True,
                output="No expired risk acceptances",
            )
        )
        return

    lines = [f"{len(expired)} expired risk acceptance(s) blocking push:"]
    for d in expired:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
        lines.append(f"  - {d.id}: expired {exp} ({d.context[:60]})")
    lines.append("Run 'ai-eng maintenance risk-status' to review.")
    lines.append("Renew with accept-risk skill or remediate with resolve-risk skill.")

    result.checks.append(
        GateCheckResult(
            name="risk-expired-block",
            passed=False,
            output="\n".join(lines),
        )
    )
