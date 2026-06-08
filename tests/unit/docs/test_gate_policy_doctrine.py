"""Guard: gate-policy.md must define the fail-open/closed error-handling doctrine.

spec-168 D-168-04: the posture governs ~273 source files but was defined nowhere.
This locks the doctrine into its canonical home so it cannot silently regress.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_POLICY = REPO_ROOT / ".ai-engineering" / "reference" / "gate-policy.md"


def test_gate_policy_states_error_handling_posture() -> None:
    lower = GATE_POLICY.read_text(encoding="utf-8").lower()
    assert "error-handling posture" in lower, "missing the posture section header"
    # the four invariants must all be stated
    assert "fail closed" in lower, "missing the fail-closed rule"
    assert "fail open" in lower, "missing the fail-open rule"
    assert "must log" in lower, "missing the must-log rule"
    assert "silently swallow" in lower, "missing the never-silently-swallow rule"
    assert "fail-open hole" in lower, "missing the security-gate-is-a-bug rule"
