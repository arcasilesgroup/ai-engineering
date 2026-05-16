"""Relevance contract for framework-events emission (spec-137 D-137-01).

Single decision point that the two canonical writers consult before
admitting an event to the audit chain. Returns True iff the event
survives the contract; otherwise the caller drops silently.

Three layers, asserted in order:

1. **Kind allow-list** (manifest-driven). The emitted ``kind`` must be in
   ``audit_policy.kind_allowlist``. Operators can shrink the list in
   their manifest to silence categories.
2. **Severity floor** (manifest-driven). Each kind has a configurable
   severity floor in ``audit_policy.severity_floor``. An emit with
   ``severity`` numerically below the floor is dropped. S0 is highest
   signal (rank 0); S3 is lowest (rank 3). A floor of S2 (rank 2) means
   "drop S3 rows, keep S0/S1/S2 rows".
3. **Failure-emission asymmetry** (caller-asserted). When
   ``failure_emission == "always"`` and the event's ``outcome`` is not
   in ``{"success", "allow"}``, the event is admitted regardless of the
   severity floor. This ensures failure rows always emit even if the
   normal-success row would have been filtered.

Severity is an optional field on the event; events without an explicit
severity default to ``S1`` (state-change tier). This keeps the contract
backward-compatible with pre-spec-137 emit sites while still letting
new emit sites pick a tier.

The mechanism is hybrid -- it combines OTel-semconv-style allow-list,
OTel SeverityNumber-style tier, and Honeycomb / Observability 2.0-style
caller-asserted relevance. See spec-137 §Architecture and the brief
references for prior art.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# Mapping: S0 is highest signal, S3 is lowest (S0 = critical / failure,
# S1 = state change, S2 = decision, S3 = debug). The numeric rank lets
# us compare "is this event at or above the floor" with a simple
# integer comparison rather than membership checks.
SEVERITY_RANK: dict[str, int] = {"S0": 0, "S1": 1, "S2": 2, "S3": 3}

# Default severity when a caller emits without specifying one. S1
# (state-change tier) is the middle-of-the-road choice: state-change
# emissions are the canonical "this happened" signal that callers
# typically want to record. Pre-spec-137 emit sites continue to work
# without code changes; new sites should pick a tier explicitly.
DEFAULT_SEVERITY: str = "S1"

# Default severity floor when no per-kind floor is configured.
DEFAULT_FLOOR: str = "S1"

# Outcomes treated as "success" for failure-emission asymmetry. Any
# outcome NOT in this set, when failure_emission=always, is admitted
# even if it would otherwise be dropped by the severity floor.
SUCCESS_OUTCOMES: frozenset[str] = frozenset({"success", "allow"})


@dataclass(frozen=True)
class AuditPolicy:
    """Parsed ``audit_policy:`` block from ``.ai-engineering/manifest.yml``.

    All fields have safe defaults so a manifest with no policy block
    (or a manifest read failure) yields an "allow all" policy --
    the relevance gate is opt-in.
    """

    kind_allowlist: frozenset[str] = field(default_factory=lambda: frozenset())
    severity_floor: Mapping[str, str] = field(default_factory=dict)
    sampling: Mapping[str, float] = field(default_factory=dict)
    failure_emission: str = "always"

    @classmethod
    def allow_all(cls) -> AuditPolicy:
        """Return an explicit allow-all policy (used when manifest is missing).

        ``kind_allowlist`` is sentinel-empty; the gate interprets an empty
        allow-list as "no allow-list configured, accept everything". This
        mirrors the principle of "manifest declares the restriction;
        absence is freedom".
        """
        return cls()


def relevance_gate(event: Mapping[str, Any], policy: AuditPolicy) -> bool:
    """Return True iff ``event`` survives the relevance contract.

    The two canonical writers call this helper before appending to
    ``framework-events.ndjson``. False means "drop the row silently".
    """
    kind = event.get("kind", "")
    if not isinstance(kind, str) or not kind:
        return False

    # Layer 1: kind allow-list. Empty allow-list means "no restriction".
    if policy.kind_allowlist and kind not in policy.kind_allowlist:
        return False

    # Determine severity (default to DEFAULT_SEVERITY if absent).
    severity = event.get("severity", DEFAULT_SEVERITY)
    if severity not in SEVERITY_RANK:
        severity = DEFAULT_SEVERITY
    severity_rank = SEVERITY_RANK[severity]

    # Layer 2: severity floor. Per-kind floor wins; otherwise the
    # explicit "default" key. If neither exists, the policy is treated
    # as "no floor configured" -- admit-all-by-severity. This makes
    # AuditPolicy.allow_all() (empty severity_floor) a true allow-all.
    floor = policy.severity_floor.get(kind) or policy.severity_floor.get("default")
    if floor is None or floor not in SEVERITY_RANK:
        # No floor configured -- the floor is the lowest tier (S3), so
        # nothing drops by severity. Failure-emission asymmetry still
        # applies but is irrelevant since no rows drop here.
        return True
    floor_rank = SEVERITY_RANK[floor]

    if severity_rank > floor_rank:
        # Layer 3: failure-emission asymmetry. Even if the row would be
        # dropped by the floor, a failure outcome keeps it.
        outcome = event.get("outcome", "")
        return bool(
            policy.failure_emission == "always"
            and isinstance(outcome, str)
            and outcome
            and outcome not in SUCCESS_OUTCOMES
        )

    return True


def load_audit_policy_from_manifest(manifest_data: Mapping[str, Any]) -> AuditPolicy:
    """Parse an ``audit_policy:`` block from a manifest dict.

    Returns ``AuditPolicy.allow_all()`` when the block is absent or
    malformed -- the gate is opt-in and must never fail closed at
    load time (that would break every existing emit on a manifest
    with no policy declared).
    """
    if not isinstance(manifest_data, Mapping):
        return AuditPolicy.allow_all()
    block = manifest_data.get("audit_policy")
    if not isinstance(block, Mapping):
        return AuditPolicy.allow_all()

    allowlist_raw = block.get("kind_allowlist", [])
    allowlist: frozenset[str]
    if isinstance(allowlist_raw, (list, tuple)):
        allowlist = frozenset(entry for entry in allowlist_raw if isinstance(entry, str) and entry)
    else:
        allowlist = frozenset()

    floor_raw = block.get("severity_floor", {})
    floor: dict[str, str] = {}
    if isinstance(floor_raw, Mapping):
        for kind, severity in floor_raw.items():
            if isinstance(kind, str) and isinstance(severity, str) and severity in SEVERITY_RANK:
                floor[kind] = severity

    sampling_raw = block.get("sampling", {})
    sampling: dict[str, float] = {}
    if isinstance(sampling_raw, Mapping):
        for key, rate in sampling_raw.items():
            if isinstance(key, str) and isinstance(rate, (int, float)):
                sampling[key] = float(rate)

    failure_emission = block.get("failure_emission", "always")
    if not isinstance(failure_emission, str) or failure_emission not in {
        "always",
        "never",
    }:
        failure_emission = "always"

    return AuditPolicy(
        kind_allowlist=allowlist,
        severity_floor=floor,
        sampling=sampling,
        failure_emission=failure_emission,
    )


__all__ = [
    "DEFAULT_FLOOR",
    "DEFAULT_SEVERITY",
    "SEVERITY_RANK",
    "SUCCESS_OUTCOMES",
    "AuditPolicy",
    "load_audit_policy_from_manifest",
    "relevance_gate",
]
