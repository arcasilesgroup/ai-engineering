"""Risk acceptance helpers for explicit governance decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from ai_engineering.state.decision_logic import append_decision, context_hash, evaluate_reuse
from ai_engineering.state.io import append_ndjson, load_model
from ai_engineering.state.models import DecisionStore


Severity = Literal["low", "medium", "high", "critical"]


def remediation_suggestion(policy_id: str) -> str:
    """Return a human-readable remediation suggestion for a policy."""
    suggestions = {
        "PR_ONLY_UNPUSHED_BRANCH_MODE": "Use auto-push mode and create PR with upstream branch tracked.",
        "NO_DIRECT_COMMIT_PROTECTED_BRANCH": "Create a feature branch and use /pr flow instead of direct commit.",
        "MANDATORY_TOOLING_ENFORCEMENT": "Install missing tools locally and re-run gate checks before retrying.",
    }
    return suggestions.get(policy_id, "Apply the documented governance baseline for this policy.")


def parse_context_payload(raw: str) -> dict[str, Any]:
    """Parse JSON context payload from CLI input."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid context JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("context JSON must be an object")
    return payload


def record_acceptance(
    *,
    root: Path,
    policy_id: str,
    decision: str,
    rationale: str,
    severity: Severity,
    context_payload: dict[str, Any],
    path_pattern: str | None,
    created_by: str,
) -> dict[str, Any]:
    """Persist risk acceptance decision and emit append-only audit event."""
    state_root = root / ".ai-engineering" / "state"
    decision_store_path = state_root / "decision-store.json"
    if not decision_store_path.exists():
        raise FileNotFoundError("missing decision-store.json; run 'ai install' first")

    hashed_context = context_hash(context_payload)
    record = append_decision(
        decision_store_path,
        policy_id=policy_id,
        repo_name=root.name,
        decision=decision,
        rationale=rationale,
        context_hash_value=hashed_context,
        severity=severity,
        created_by=created_by,
    )
    if path_pattern is not None:
        store = load_model(decision_store_path, DecisionStore)
        store.decisions[-1].scope.pathPattern = path_pattern
        (state_root / "decision-store.json").write_text(
            store.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

    suggestion = remediation_suggestion(policy_id)
    append_ndjson(
        state_root / "audit-log.ndjson",
        {
            "event": "risk_acceptance_recorded",
            "actor": "gate-cli",
            "details": {
                "policyId": policy_id,
                "decision": decision,
                "severity": severity,
                "contextHash": hashed_context,
                "pathPattern": path_pattern,
                "remediationSuggestion": suggestion,
            },
        },
    )
    return {
        "policyId": policy_id,
        "decision": record.decision,
        "severity": record.severity,
        "contextHash": record.contextHash,
        "createdAt": record.createdAt,
        "reused": False,
        "remediationSuggestion": suggestion,
    }


def check_reuse(
    *,
    root: Path,
    policy_id: str,
    severity: Severity,
    context_payload: dict[str, Any],
    path_pattern: str | None,
    expected_decision: str | None,
) -> dict[str, Any]:
    """Check whether an existing decision can be reused."""
    state_root = root / ".ai-engineering" / "state"
    decision_store_path = state_root / "decision-store.json"
    if not decision_store_path.exists():
        raise FileNotFoundError("missing decision-store.json; run 'ai install' first")

    store = load_model(decision_store_path, DecisionStore)
    hashed_context = context_hash(context_payload)
    evaluation = evaluate_reuse(
        store,
        policy_id=policy_id,
        repo_name=root.name,
        context_hash_value=hashed_context,
        severity=severity,
        path_pattern=path_pattern,
        expected_decision=expected_decision,
    )
    record_id = evaluation.record.id if evaluation.record is not None else None
    return {
        "reusable": evaluation.reusable,
        "reason": evaluation.reason,
        "contextHash": hashed_context,
        "recordId": record_id,
    }
