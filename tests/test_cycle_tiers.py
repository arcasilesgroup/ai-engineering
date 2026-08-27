"""Executable contracts for spec 042 / B-042-1: the cycle skills name the tier they ask for.

`model_router` maps cycle steps to tiers (research/spec -> low, security/review/plan/audit
-> top, the rest -> medium). The skills that run those steps must ask for the same tier —
the router and the instruction are one contract, and a test pins the two together so a
renamed stage or a retiered step cannot drift silently. Never reads the conversation; only
the router's own sets and the skills' own words.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import model_router  # noqa: E402


def _body(name: str) -> str:
    return (ROOT / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def _flat(name: str) -> str:
    """The skill's body with line breaks flattened, so a phrase the author wrapped across
    two lines (`**top**\ntier`) still matches the phrase a reader would say."""
    return " ".join(_body(name).split())


def test_each_top_step_skill_asks_for_the_top_tier():
    for skill in ("ai-security", "ai-review"):
        body = _flat(skill)
        assert "**top** tier" in body, f"{skill} should ask the top tier"
        assert "model_router" in body, f"{skill} should name the router it matches"


def test_spec_skill_asks_for_the_low_tier():
    body = _flat("ai-spec")
    assert "**low** tier" in body, "ai-spec should ask the low tier"
    assert "model_router" in body


def test_ai_goal_names_the_tier_for_every_stage():
    body = _flat("ai-goal")
    assert "**low** tier" in body
    assert "**top** tier" in body
    assert "**medium**" in body
    assert "model_router" in body


def test_the_skills_agree_with_the_routers_own_sets():
    """The words in the skills and the sets in model_router are the same contract.

    The router is the authority (it is data the command event reads); the skills must not
    ask for a tier the router would not route to. The router's own step sets are the
    contract; the skills name tiers for steps the sets cover."""
    assert {"research", "spec"} <= set(model_router._LOW_STEPS)
    assert {"security", "review", "plan", "audit"} <= set(model_router._TOP_STEPS)
    for step in model_router._LOW_STEPS:
        assert model_router.route(step, {"models": {"low": "low"}}) == "low"
    for step in model_router._TOP_STEPS:
        assert model_router.route(step, {"models": {"top": "top"}}) == "top"
