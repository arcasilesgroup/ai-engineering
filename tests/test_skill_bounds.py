"""Executable contracts for spec 041 / B-041-2: the spec↔critics loop bound.

The two-rounds-per-digest cap is the skill layer's instruction, and a script pins that
the instruction is there in the two skills that run the loop. A bound nobody can find in
the file the loop reads is a bound that does not exist.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _body(name: str) -> str:
    return (ROOT / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_challenge_declares_the_two_round_cap_per_digest():
    body = _body("ai-challenge")
    assert "two rounds" in body
    assert "digest" in body


def test_council_declares_the_two_round_cap_per_digest():
    body = _body("ai-council")
    assert "two rounds" in body
    assert "digest" in body


def test_the_cap_names_the_escalation_not_a_silent_stop():
    for name in ("ai-challenge", "ai-council"):
        body = _body(name)
        assert "hand the page to the person" in body, name
        # the bound is named as a rule, not as a module: `loopgate` was deleted by spec
        # 044, and a skill that points at the corpse is the dead reference this replaced
        assert "digest-equal green runs" in body, (
            f"{name} should name the two-identical-greens rule as the orchestrator's bound"
        )
