"""Decision record emitter (spec-199 T-4).

Emits adopt/adapt/reject/blocked decisions for CLI candidates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionRecord:
    """Decision record for a CLI candidate."""

    candidate_name: str
    decision: str  # "adopt", "adapt", "reject", "blocked"
    rationale: str
    evidence: list[str]
    pilot_brief: str | None = None  # path to implementation brief

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "decision": self.decision,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "pilot_brief": self.pilot_brief,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def emit_decision(
    candidate_name: str,
    decision: str,
    rationale: str,
    evidence: list[str],
    pilot_brief: str | None = None,
) -> DecisionRecord:
    """Emit a decision record."""
    valid_decisions = {"adopt", "adapt", "reject", "blocked"}
    if decision not in valid_decisions:
        raise ValueError(f"Invalid decision: {decision}. Must be one of {valid_decisions}")

    return DecisionRecord(
        candidate_name=candidate_name,
        decision=decision,
        rationale=rationale,
        evidence=evidence,
        pilot_brief=pilot_brief,
    )
