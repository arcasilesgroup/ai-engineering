"""Agents conformance rubric tests (spec-127 M1, brief §3 / §22 parallel rubric).

Pairing: TDD RED partner of umbrella T-2.11. GREEN target =
``LintAgentsUseCase(...).run()`` over the live ``.claude/agents/``
surface. **DO NOT MODIFY THIS FILE** during Phase D GREEN.

Rules (5):

* ``agent_rule_1_cso_third_person`` — frontmatter description CSO,
  third-person, ≤1024 chars, no banned substrings.
* ``agent_rule_2_tools_whitelist`` — ``tools:`` declared explicitly.
* ``agent_rule_3_model_declared`` — ``model: opus|sonnet|haiku`` set.
* ``agent_rule_4_dispatch_source`` — agent referenced in at least one
  ``.claude/skills/**/SKILL.md`` or ``AGENTS.md`` / ``CLAUDE.md`` body.
* ``agent_rule_5_no_orphan`` — agent file is not orphaned (same
  signal as rule 4 with CRITICAL severity when zero references).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_app.lint_agents import LintAgentsUseCase
from skill_domain.rubric import AGENT_RULES
from skill_infra.fs_scanner import FilesystemAgentScanner


@pytest.fixture(scope="module")
def agents_report(skills_root: Path, agents_root: Path):
    scanner = FilesystemAgentScanner(agents_root, skills_root)
    return LintAgentsUseCase(scanner).run()


def test_agent_rule_1_cso_third_person(agents_report) -> None:
    rule = _get_rule("agent_rule_1_cso_third_person")
    assert rule is not None
    # At least one agent must pass rule 1 — the live surface includes
    # well-formed agents (e.g., reviewer-correctness, ai-build).
    pass_count = sum(
        1
        for r in agents_report.per_agent
        if r.rule_for("agent_rule_1_cso_third_person")
        and r.rule_for("agent_rule_1_cso_third_person").severity == "OK"
    )
    assert pass_count >= 5, (
        f"expected ≥5 agents to pass rule 1; got {pass_count}/{len(agents_report.per_agent)}"
    )


def test_agent_rule_2_tools_whitelist(agents_report) -> None:
    rule = _get_rule("agent_rule_2_tools_whitelist")
    assert rule is not None
    # Most agents in the live surface declare a tools whitelist.
    with_tools = sum(
        1
        for r in agents_report.per_agent
        if r.rule_for("agent_rule_2_tools_whitelist")
        and r.rule_for("agent_rule_2_tools_whitelist").severity == "OK"
    )
    assert with_tools >= 1, (
        f"expected ≥1 agent to declare tools; got {with_tools}/{len(agents_report.per_agent)}"
    )


def test_agent_rule_3_model_declared(agents_report) -> None:
    rule = _get_rule("agent_rule_3_model_declared")
    assert rule is not None
    # Agents must declare a model — opus / sonnet / haiku.
    declared = sum(
        1
        for r in agents_report.per_agent
        if r.rule_for("agent_rule_3_model_declared")
        and r.rule_for("agent_rule_3_model_declared").severity == "OK"
    )
    # At minimum half the agents should declare a model on the live
    # surface; the remainder are flagged for M1 cleanup.
    assert declared >= len(agents_report.per_agent) // 2, (
        f"too few agents declare model: {declared}/{len(agents_report.per_agent)}"
    )


def test_agent_rule_4_dispatch_source(agents_report) -> None:
    rule = _get_rule("agent_rule_4_dispatch_source")
    assert rule is not None
    # Agents on the live surface should be referenced by skills or
    # AGENTS.md. ``reviewer-design`` is the orphan called out in §2.2;
    # ai-engineering / ai-explore / ai-guard are widely referenced.
    referenced = sum(
        1
        for r in agents_report.per_agent
        if r.rule_for("agent_rule_4_dispatch_source")
        and r.rule_for("agent_rule_4_dispatch_source").severity == "OK"
    )
    assert referenced >= 1, (
        f"no agent has any dispatch-source references: {referenced}/{len(agents_report.per_agent)}"
    )


def test_agent_rule_5_no_orphan(agents_report) -> None:
    rule = _get_rule("agent_rule_5_no_orphan")
    assert rule is not None
    # Brief §2.2: ``reviewer-design`` is the named orphan. The rubric
    # must surface at least the orphan(s) the audit identified, but
    # not flag every well-referenced agent as critical.
    critical = [
        r
        for r in agents_report.per_agent
        if r.rule_for("agent_rule_5_no_orphan")
        and r.rule_for("agent_rule_5_no_orphan").severity == "CRITICAL"
    ]
    assert len(agents_report.per_agent) > 0, "agents scanner returned empty list"
    # Sanity bound: orphans should be a small minority.
    assert len(critical) < len(agents_report.per_agent), (
        "every agent flagged as orphan — dispatch-source detection broken"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_rule(name: str):
    for rule in AGENT_RULES:
        if rule.name == name:
            return rule
    return None
