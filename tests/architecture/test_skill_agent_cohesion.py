"""Skill ↔ agent cohesion enforcement (spec-134 D-134-07).

Every entry in :data:`DEFAULT_AGENTS_NAMES` (the 9 first-class agents)
MUST have a discoverable slash-skill counterpart so the `/` menu in
every IDE surface exposes the orchestrator handle. Without this guard,
orphan agents (no matching skill) become "ghost surfaces" — present
in the agent registry but unreachable from the operator's primary
discovery channel.

The cohesion rule is the half of spec-134 goal 9 that pairs with the
spec-128 "single source of truth" contract for skill discovery:
operators find capabilities via `/ai-<name>`; everything else
(specialist agents, internal handlers) is dispatch-only.

Reads `.claude/skills/` and `src/.../templates/project/.claude/skills/`
directly. No `manifest.yml` lookup, no `state.db.decisions` query —
satisfies D-134-10 (no decisions-table dependency for architecture
tests).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.config.framework_defaults import DEFAULT_AGENTS_NAMES

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_SKILLS = _REPO_ROOT / ".claude" / "skills"
_TEMPLATE_SKILLS = (
    _REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "skills"
)

# Bare-agent-name → resolved skill directory name (with ``ai-`` prefix).
# Every agent maps trivially: ``<bare>`` → ``ai-<bare>``. Sub-006
# completed the hard-rename wave (D-134-06): the legacy ``ai-guard``
# agent is now ``ai-advise`` (file + registry), and ``ai-guide`` is
# now ``ai-onboard``. The identity map below covers every entry in
# :data:`DEFAULT_AGENTS_NAMES` — no rename bridges remain (Constitution
# §13.3 forbids backwards-compat shims).
_COHESION_MAPPING: dict[str, str] = {}


def _resolve_skill_name(agent_bare_name: str) -> str:
    """Return the skill directory name that an agent should resolve to.

    Uses :data:`_COHESION_MAPPING` for renamed agents; otherwise falls
    back to the identity rule ``ai-<bare>``.
    """
    return _COHESION_MAPPING.get(agent_bare_name, f"ai-{agent_bare_name}")


@pytest.mark.unit
def test_every_first_class_agent_has_a_slash_skill() -> None:
    """Every first-class agent must resolve to an existing SKILL.md.

    Iterates :data:`DEFAULT_AGENTS_NAMES`, resolves each agent to its
    expected skill directory (via :data:`_COHESION_MAPPING` for
    renames; identity otherwise), and asserts that
    ``.claude/skills/<resolved>/SKILL.md`` exists on disk. Orphans
    fail with the explicit list of missing skill directories so the
    remediation is obvious.
    """
    missing: list[str] = []
    for agent_name in DEFAULT_AGENTS_NAMES:
        resolved = _resolve_skill_name(agent_name)
        skill_md = _CANONICAL_SKILLS / resolved / "SKILL.md"
        if not skill_md.is_file():
            missing.append(f"{agent_name} -> {resolved} (expected {skill_md})")

    assert not missing, (
        "First-class agents without a discoverable slash-skill counterpart "
        f"({len(missing)} orphan(s)):\n  - " + "\n  - ".join(missing)
    )


@pytest.mark.unit
def test_cohesion_mapping_has_no_stale_entries() -> None:
    """Every key in :data:`_COHESION_MAPPING` must still appear in
    :data:`DEFAULT_AGENTS_NAMES`.

    Stale entries (agents removed from the registry but still listed
    in the mapping) silently hide cohesion gaps. Fail loudly.
    """
    agent_set = set(DEFAULT_AGENTS_NAMES)
    stale = sorted(k for k in _COHESION_MAPPING if k not in agent_set)
    assert not stale, (
        "_COHESION_MAPPING contains keys absent from DEFAULT_AGENTS_NAMES: "
        f"{stale}. Drop the stale entries or restore the agent registry."
    )


@pytest.mark.unit
def test_cohesion_skill_dirs_exist_in_template_mirror() -> None:
    """The resolved skill directory must also exist under the template tree.

    ``ai-eng install`` ships skills from
    ``src/ai_engineering/templates/project/.claude/skills/`` to
    downstream projects. If a canonical skill ships without a template
    copy, the installer silently omits it from every consumer.
    """
    missing: list[str] = []
    for agent_name in DEFAULT_AGENTS_NAMES:
        resolved = _resolve_skill_name(agent_name)
        template_skill = _TEMPLATE_SKILLS / resolved / "SKILL.md"
        if not template_skill.is_file():
            missing.append(f"{agent_name} -> {resolved} (expected {template_skill})")

    assert not missing, (
        "Cohesion skills missing from template mirror "
        f"({len(missing)} missing):\n  - " + "\n  - ".join(missing)
    )
