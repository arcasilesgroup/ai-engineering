"""Stdlib-only mirror of ``src/ai_engineering/state/relevance.py``.

Hook scripts under ``.ai-engineering/scripts/hooks/`` run before
``uv sync`` and cannot import third-party dependencies. This file
re-declares the relevance contract with stdlib-only types so the
hook-side writer at ``_lib/observability.py`` can consult the same
gate as the package-side writer.

The two modules are parity-tested by
``tests/unit/hooks/test_relevance_gate_parity.py`` -- the test
parametrizes over the same input matrix and asserts identical
admit/drop decisions.

See spec-137 §Architecture for the contract and the brief for the
prior art (OTel-semconv allow-list + OTel SeverityNumber tier +
Honeycomb / Observability 2.0 caller-asserted relevance).
"""

from __future__ import annotations

from typing import Any

SEVERITY_RANK: dict[str, int] = {"S0": 0, "S1": 1, "S2": 2, "S3": 3}
DEFAULT_SEVERITY: str = "S1"
DEFAULT_FLOOR: str = "S1"
SUCCESS_OUTCOMES: frozenset[str] = frozenset({"success", "allow"})


def relevance_gate(event: dict, policy: dict) -> bool:
    """Return True iff ``event`` survives the relevance contract.

    Stdlib-only signature: ``policy`` is a plain dict with keys
    ``kind_allowlist`` (list of str), ``severity_floor`` (dict
    str->str), ``failure_emission`` (str). Missing keys default to
    permissive values (allow-all behaviour).
    """
    kind_raw: Any = event.get("kind", "")
    if not isinstance(kind_raw, str) or not kind_raw:
        return False
    kind: str = kind_raw

    allowlist_raw: Any = policy.get("kind_allowlist", [])
    if isinstance(allowlist_raw, (list, tuple)) and allowlist_raw and kind not in allowlist_raw:
        return False

    severity_raw: Any = event.get("severity", DEFAULT_SEVERITY)
    severity: str = (
        severity_raw
        if isinstance(severity_raw, str) and severity_raw in SEVERITY_RANK
        else DEFAULT_SEVERITY
    )
    severity_rank = SEVERITY_RANK[severity]

    floor_map_raw: Any = policy.get("severity_floor", {})
    floor_map: dict = floor_map_raw if isinstance(floor_map_raw, dict) else {}
    floor = floor_map.get(kind) or floor_map.get("default")
    if not isinstance(floor, str) or floor not in SEVERITY_RANK:
        # No floor configured -- admit (mirror of package-side behaviour).
        return True
    floor_rank = SEVERITY_RANK[floor]

    if severity_rank > floor_rank:
        failure_emission_raw: Any = policy.get("failure_emission", "always")
        failure_emission: str = (
            failure_emission_raw if isinstance(failure_emission_raw, str) else "always"
        )
        outcome_raw: Any = event.get("outcome", "")
        outcome: str = outcome_raw if isinstance(outcome_raw, str) else ""
        return bool(failure_emission == "always" and outcome and outcome not in SUCCESS_OUTCOMES)

    return True


def allow_all_policy() -> dict:
    """Return a policy dict that admits every event (manifest absent)."""
    return {
        "kind_allowlist": [],
        "severity_floor": {},
        "failure_emission": "always",
    }


__all__ = [
    "DEFAULT_FLOOR",
    "DEFAULT_SEVERITY",
    "SEVERITY_RANK",
    "SUCCESS_OUTCOMES",
    "allow_all_policy",
    "relevance_gate",
]
