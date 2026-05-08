"""Validate agent definitions in .ai-engineering/agents/ against architecture v3.

Unlike test_validator.py which creates isolated fixture worlds, these tests
parametrize against the REAL .ai-engineering/agents/ template directory. If an agent
is added, removed, or has broken frontmatter, these tests FAIL.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_AGENTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "ai_engineering"
    / "templates"
    / "project"
    / ".claude"
    / "agents"
)

# spec-127 sub-005 (M4): 9 user-facing orchestrator agents (ai-*.md)
# Bumped 10 → 9 by deleting `ai-run-orchestrator.md`; functionality
# absorbed by `ai-autopilot --backlog --source <github|ado|local>`
# (D-127-12).
_EXPECTED_ORCHESTRATORS = frozenset(
    {
        "ai-autopilot",
        "ai-build",
        "ai-explore",
        "ai-guard",
        "ai-guide",
        "ai-review",
        "ai-simplify",
        "ai-verify",
        "ai-plan",
    }
)

# spec-127 sub-005 (M4): 15 specialist sub-agents (was 16 — bumped by
# deleting `reviewer-design.md` whose rules now live in `reviewer-frontend.md`,
# and renaming `review-context-explorer` → `reviewer-context` +
# `review-finding-validator` → `reviewer-validator` per D-127-04 / D-127-10).
_EXPECTED_SPECIALISTS = frozenset(
    {
        "reviewer-context",
        "reviewer-security",
        "reviewer-backend",
        "reviewer-performance",
        "reviewer-correctness",
        "reviewer-testing",
        "reviewer-compatibility",
        "reviewer-architecture",
        "reviewer-maintainability",
        "reviewer-frontend",
        "reviewer-validator",
        "verify-deterministic",
        "verifier-governance",
        "verifier-architecture",
        "verifier-feature",
    }
)

_EXPECTED_AGENTS = _EXPECTED_ORCHESTRATORS | _EXPECTED_SPECIALISTS

_REQUIRED_FRONTMATTER = {"name"}


def _all_agent_files() -> list[Path]:
    """Return all .md files in the agents directory."""
    if not _AGENTS_DIR.is_dir():
        return []
    return sorted(_AGENTS_DIR.glob("*.md"))


def _orchestrator_files() -> list[Path]:
    """Return only ai-*.md orchestrator agent files."""
    if not _AGENTS_DIR.is_dir():
        return []
    return sorted(_AGENTS_DIR.glob("ai-*.md"))


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract flat key-value frontmatter from markdown."""
    match = re.match(r"^---[ \t]*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        m = re.match(r"^(\w[\w-]*):[ \t]*(?:\"([^\"]*)\"|'([^']*)'|(.+))$", line.strip())
        if m:
            result[m.group(1)] = (m.group(2) or m.group(3) or m.group(4)).strip()
    return result


# -- Tests ---------------------------------------------------------------


def test_orchestrator_count_matches_expected() -> None:
    """There should be exactly 9 orchestrator agents on disk (post-spec-127 sub-005)."""
    agents = _orchestrator_files()
    names = {f.stem for f in agents}
    assert len(agents) == len(_EXPECTED_ORCHESTRATORS), (
        f"Expected {len(_EXPECTED_ORCHESTRATORS)} orchestrators, "
        f"found {len(agents)}: {sorted(names)}"
    )


def test_orchestrator_names_match_expected() -> None:
    """Orchestrator file names must match the expected set exactly."""
    agents = _orchestrator_files()
    names = {f.stem for f in agents}
    assert names == _EXPECTED_ORCHESTRATORS, (
        f"Orchestrator mismatch. "
        f"Missing: {_EXPECTED_ORCHESTRATORS - names}, "
        f"Extra: {names - _EXPECTED_ORCHESTRATORS}"
    )


def test_total_agent_count_matches_expected() -> None:
    """Total agents (orchestrators + specialists) must match."""
    agents = _all_agent_files()
    names = {f.stem for f in agents}
    assert len(agents) == len(_EXPECTED_AGENTS), (
        f"Expected {len(_EXPECTED_AGENTS)} total agents, found {len(agents)}: {sorted(names)}"
    )


def test_agent_names_match_expected() -> None:
    """All agent file names must match the expected set exactly."""
    agents = _all_agent_files()
    names = {f.stem for f in agents}
    assert names == _EXPECTED_AGENTS, (
        f"Agent mismatch. Missing: {_EXPECTED_AGENTS - names}, Extra: {names - _EXPECTED_AGENTS}"
    )


@pytest.mark.parametrize("agent_file", _all_agent_files(), ids=lambda f: f.stem)
def test_agent_has_valid_frontmatter(agent_file: Path) -> None:
    """Every agent must have YAML frontmatter with required fields."""
    text = agent_file.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{agent_file.name}: missing frontmatter fence"
    fm = _parse_frontmatter(text)
    missing = _REQUIRED_FRONTMATTER - set(fm.keys())
    assert not missing, f"{agent_file.name}: missing frontmatter fields: {missing}"


@pytest.mark.parametrize("agent_file", _all_agent_files(), ids=lambda f: f.stem)
def test_agent_has_identity_or_role_section(agent_file: Path) -> None:
    """Every agent must have an Identity, Role, or Process section."""
    text = agent_file.read_text(encoding="utf-8")
    has_section = any(
        section in text
        for section in [
            "## Identity",
            "## Supported Stacks",
            "## Role",
            "## Process",
            "## Your Role",
            "## Before You Review",
            "## Before You Verify",
            "## Review Scope",
            "## Verification Scope",
        ]
    )
    assert has_section, (
        f"{agent_file.name}: missing structural section "
        "(Identity, Role, Process, or domain-specific header)"
    )
