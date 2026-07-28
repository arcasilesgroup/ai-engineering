"""Judge/verifier model independence (spec-201 sub-006, D-201-16).

D-201-16: agents that *assess* work must not share the model of the agent
that *produced* it. Independence today is persona-only — 15 of 19
canonical agents declare ``model: opus``, the generator and every judge
alike, which makes corroboration and adversarial validation structurally
weaker than their contracts claim.

Two separable halves, pinned separately on purpose:

* **The mechanism** — ``scripts/sync_mirrors/core.py::resolve_agent_model``
  makes ``AgentMeta.model`` an OPTIONAL OVERRIDE that wins over the
  effort-derived literal, so "different model, same capability" becomes
  expressible for the first time. Shipped and asserted here.
* **The assignment** — which model identifier the judges move to. That
  value is NOT derivable from the spec: ``_EFFORT_TO_MODEL`` is the
  complete tier-alias vocabulary (``opus``/``sonnet``/``haiku``), the
  generator ``ai-build`` is ``opus``, and every remaining alias is a
  strictly lower capability tier — the exact trade ``spec.md:358-361``
  refuses. The axis therefore needs a full model identifier that the
  spec never names, so the assignment is an escalation, not a build
  decision. ``test_judges_do_not_share_the_generator_model`` is a
  ``strict`` xfail: it documents the open contract and turns RED the
  moment the assignment lands, forcing the marker off.

Capability is pinned independently of the assignment so a future operator
cannot "achieve" independence by downgrading the reviewers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_AGENTS = _REPO_ROOT / ".claude" / "agents"

_MODEL_RE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)

# Agents that PRODUCE work.
GENERATOR_AGENTS: tuple[str, ...] = ("ai-build", "ai-autopilot", "ai-plan")

# Agents that ASSESS work: the 2 user-facing judges plus the 10 internal
# review/verify specialists they dispatch.
JUDGE_AGENTS: tuple[str, ...] = (
    "ai-review",
    "ai-verify",
    "review-context",
    "review-validator",
    "reviewer-compatibility",
    "reviewer-correctness",
    "reviewer-frontend",
    "reviewer-performance",
    "reviewer-security",
    "reviewer-testing",
    "verifier-acceptance",
    "verifier-deterministic",
)

# Tier aliases below the top tier. A judge carrying one of these has been
# made WEAKER, which spec.md:358-361 explicitly refuses as a way to buy
# independence.
_DOWNGRADED_ALIASES: frozenset[str] = frozenset({"sonnet", "haiku"})


def _declared_model(agent: str) -> str:
    """Return the hand-typed ``model:`` from a canonical agent file."""
    path = _CANONICAL_AGENTS / f"{agent}.md"
    assert path.is_file(), f"{agent}: canonical agent file not found at {path}"
    match = _MODEL_RE.search(path.read_text(encoding="utf-8"))
    assert match is not None, f"{agent}: no 'model:' in frontmatter of {path}"
    return match.group(1)


@pytest.mark.unit
def test_every_canonical_agent_declares_a_model() -> None:
    """Every ``.claude/agents/*.md`` carries a hand-typed model literal."""
    missing = [
        p.stem
        for p in sorted(_CANONICAL_AGENTS.glob("*.md"))
        if not _MODEL_RE.search(p.read_text(encoding="utf-8"))
    ]
    assert not missing, f"canonical agents with no 'model:' declaration: {missing}"


@pytest.mark.unit
@pytest.mark.xfail(
    strict=True,
    reason=(
        "spec-201 D-201-16 assignment is UNRESOLVED (sub-006 T-6.7 escalation): the "
        "mechanism ships, but no full model identifier for the judges has been approved "
        "and no tier alias can express 'different model, same capability'. Remove this "
        "marker in the same change that assigns the identifier."
    ),
)
def test_judges_do_not_share_the_generator_model() -> None:
    """No assessing agent runs the model of a producing agent."""
    generator_models = {name: _declared_model(name) for name in GENERATOR_AGENTS}
    judge_models = {name: _declared_model(name) for name in JUDGE_AGENTS}
    produced = set(generator_models.values())
    offenders = {name: model for name, model in judge_models.items() if model in produced}
    assert not offenders, (
        f"{len(offenders)} judge agent(s) share a generator model: {offenders}. "
        f"Generators: {generator_models}. Corroboration is structurally weaker when the "
        "assessor shares the producer's model (D-201-16)."
    )


@pytest.mark.unit
def test_no_judge_was_downgraded_to_buy_independence() -> None:
    """Independence must not be bought with a lower capability tier."""
    downgraded = {
        name: model
        for name in JUDGE_AGENTS
        if (model := _declared_model(name)) in _DOWNGRADED_ALIASES
    }
    assert not downgraded, (
        f"judges declaring a lower-capability tier alias: {downgraded}. "
        "spec.md:358-361 refuses independence bought by weakening the reviewers — "
        "use the AgentMeta.model override axis instead of a tier downgrade."
    )


@pytest.mark.unit
def test_user_facing_judges_keep_their_high_effort_tier() -> None:
    """`review` / `verify` stay effort=high; the model axis is independent."""
    from scripts.sync_command_mirrors import AGENT_METADATA

    for name in ("review", "verify"):
        assert AGENT_METADATA[name].effort == "high", (
            f"{name}: effort {AGENT_METADATA[name].effort!r} != 'high'. The model axis "
            "(D-201-16) is independent of the effort tier — never trade one for the other."
        )


@pytest.mark.unit
def test_resolve_agent_model_derives_from_effort_without_an_override() -> None:
    """With no override, the resolver is exactly the effort-derived model."""
    from scripts.sync_mirrors.core import AgentMeta, _effort_to_model, resolve_agent_model

    meta = AgentMeta(
        display_name="X",
        description="d",
        model="",
        effort="high",
        color="red",
        copilot_renamed_tools=(),
        copilot_native_tools=(),
        claude_tools=(),
    )
    assert resolve_agent_model(meta) == _effort_to_model("high") == "opus"


@pytest.mark.unit
def test_resolve_agent_model_honours_an_explicit_override() -> None:
    """A model that is not the effort-derived literal wins as an override."""
    from scripts.sync_mirrors.core import AgentMeta, resolve_agent_model

    meta = AgentMeta(
        display_name="X",
        description="d",
        model="some-provider/some-model-2026",
        effort="high",
        color="red",
        copilot_renamed_tools=(),
        copilot_native_tools=(),
        claude_tools=(),
    )
    assert resolve_agent_model(meta) == "some-provider/some-model-2026"
