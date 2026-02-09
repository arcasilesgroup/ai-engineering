"""Generic risk acceptance helpers for governance decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from ai_engineering.state.decision_logic import append_decision, context_hash, evaluate_reuse
from ai_engineering.state.io import append_ndjson, load_model
from ai_engineering.state.models import DecisionStore


Severity = Literal["low", "medium", "high", "critical"]


def parse_context_payload(raw: str) -> dict[str, Any]:
    """Parse CLI JSON payload used for context hash generation."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid context JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("context payload must be a JSON object")
    return payload


def remediation_suggestion(policy_id: str) -> str:
    """Return remediation suggestion for policy weakening requests."""
    suggestions = {
        "PR_ONLY_UNPUSHED_BRANCH_MODE": "Use --mode auto-push and ensure branch tracks upstream.",
        "NO_DIRECT_COMMIT_PROTECTED_BRANCH": (
            "Create a feature branch and run governed /pr workflow instead of direct commit."
        ),
        "MANDATORY_TOOLING_ENFORCEMENT": "Install/repair required tooling and rerun local gates.",
    }
    return suggestions.get(
        policy_id,
        "Apply the canonical governance baseline and rerun checks before continuing.",
    )


def _state_paths(root: Path) -> tuple[Path, Path]:
    state_root = root / ".ai-engineering" / "state"
    return state_root / "decision-store.json", state_root / "audit-log.ndjson"


def record_acceptance(
    *,
    root: Path,
    policy_id: str,
    policy_version: str | None,
    decision: str,
    rationale: str,
    severity: Severity,
    context_payload: dict[str, Any],
    path_pattern: str | None,
    created_by: str,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Persist explicit risk acceptance with append-only audit event."""
    decision_path, audit_path = _state_paths(root)
    if not decision_path.exists():
        raise FileNotFoundError("missing decision-store.json; run 'ai install' first")

    hashed = context_hash(context_payload)
    record = append_decision(
        decision_path,
        policy_id=policy_id,
        repo_name=root.name,
        decision=decision,
        rationale=rationale,
        context_hash_value=hashed,
        severity=severity,
        created_by=created_by,
        path_pattern=path_pattern,
        policy_version=policy_version,
        expires_at=expires_at,
    )

    suggestion = remediation_suggestion(policy_id)
    append_ndjson(
        audit_path,
        {
            "event": "risk_acceptance_recorded",
            "actor": "gate-cli",
            "details": {
                "policyId": policy_id,
                "policyVersion": policy_version,
                "decision": decision,
                "severity": severity,
                "contextHash": hashed,
                "pathPattern": path_pattern,
                "remediationSuggestion": suggestion,
            },
        },
    )
    return {
        "id": record.id,
        "policyId": record.scope.policyId,
        "policyVersion": record.scope.policyVersion,
        "decision": record.decision,
        "severity": record.severity,
        "contextHash": record.contextHash,
        "createdAt": record.createdAt,
        "remediationSuggestion": suggestion,
    }


def check_reuse(
    *,
    root: Path,
    policy_id: str,
    policy_version: str | None,
    severity: Severity,
    context_payload: dict[str, Any],
    path_pattern: str | None,
    expected_decision: str | None,
) -> dict[str, Any]:
    """Check if previous decision can be reused or requires re-prompt."""
    decision_path, _ = _state_paths(root)
    if not decision_path.exists():
        raise FileNotFoundError("missing decision-store.json; run 'ai install' first")

    store = load_model(decision_path, DecisionStore)
    hashed = context_hash(context_payload)
    evaluation = evaluate_reuse(
        store,
        policy_id=policy_id,
        repo_name=root.name,
        context_hash_value=hashed,
        severity=severity,
        path_pattern=path_pattern,
        policy_version=policy_version,
        expected_decision=expected_decision,
    )
    return {
        "reusable": evaluation.reusable,
        "reason": evaluation.reason,
        "contextHash": hashed,
        "recordId": evaluation.record.id if evaluation.record is not None else None,
    }
