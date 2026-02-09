"""Decision-store helpers for governance flow reuse."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, NamedTuple

from ai_engineering.state.io import load_model, write_json
from ai_engineering.state.models import DecisionRecord, DecisionScope, DecisionStore


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def context_hash(payload: dict[str, Any]) -> str:
    """Create stable context hash for decision reuse."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def find_valid_decision(
    store: DecisionStore,
    *,
    policy_id: str,
    repo_name: str,
    context_hash_value: str,
) -> DecisionRecord | None:
    """Return latest non-expired decision that matches same policy and context."""
    now = _now_utc()
    candidates = [
        record
        for record in store.decisions
        if record.scope.policyId == policy_id
        and record.scope.repo == repo_name
        and record.contextHash == context_hash_value
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda record: record.createdAt, reverse=True)
    for record in candidates:
        expires = _parse_time(record.expiresAt)
        if expires is None or expires > now:
            return record
    return None


class DecisionReuseResult(NamedTuple):
    """Result of evaluating whether a prior decision can be reused."""

    reusable: bool
    reason: str
    record: DecisionRecord | None


def evaluate_reuse(
    store: DecisionStore,
    *,
    policy_id: str,
    repo_name: str,
    context_hash_value: str,
    severity: Literal["low", "medium", "high", "critical"],
    path_pattern: str | None = None,
    expected_decision: str | None = None,
) -> DecisionReuseResult:
    """Evaluate whether prior decision can be reused or requires re-prompt."""
    candidates = [
        record
        for record in store.decisions
        if record.scope.policyId == policy_id and record.scope.repo == repo_name
    ]
    if not candidates:
        return DecisionReuseResult(False, "no_prior_decision", None)

    candidates.sort(key=lambda record: record.createdAt, reverse=True)
    latest = candidates[0]
    expires = _parse_time(latest.expiresAt)
    now = _now_utc()
    if expires is not None and expires <= now:
        return DecisionReuseResult(False, "decision_expired", latest)
    if latest.scope.pathPattern != path_pattern:
        return DecisionReuseResult(False, "scope_changed", latest)
    if latest.severity != severity:
        return DecisionReuseResult(False, "severity_changed", latest)
    if latest.contextHash != context_hash_value:
        return DecisionReuseResult(False, "material_context_hash_changed", latest)
    if expected_decision is not None and latest.decision != expected_decision:
        return DecisionReuseResult(False, "decision_changed", latest)
    return DecisionReuseResult(True, "reused", latest)


def append_decision(
    decision_store_path: Path,
    *,
    policy_id: str,
    repo_name: str,
    decision: str,
    rationale: str,
    context_hash_value: str,
    severity: Literal["low", "medium", "high", "critical"] = "medium",
    created_by: str | None = None,
    expires_at: str | None = None,
) -> DecisionRecord:
    """Append decision record and persist decision store."""
    store = load_model(decision_store_path, DecisionStore)
    now = _now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identifier = f"dec_{int(_now_utc().timestamp())}_{len(store.decisions) + 1}"

    scope = DecisionScope(repo=repo_name, policyId=policy_id)
    record = DecisionRecord(
        id=identifier,
        scope=scope,
        contextHash=context_hash_value,
        severity=severity,
        decision=decision,
        rationale=rationale,
        createdAt=now,
        createdBy=created_by,
        expiresAt=expires_at,
    )
    store.decisions.append(record)
    write_json(decision_store_path, store.model_dump(mode="json"))
    return record
