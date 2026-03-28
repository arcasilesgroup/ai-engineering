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

# Post spec-055: 9 user-facing orchestrator agents (ai-*.md)
_EXPECTED_ORCHESTRATORS = frozenset(
    {
        "ai-build",
        "ai-explore",
        "ai-guard",
        "ai-guide",
        "ai-plan",
        "ai-review",
        "ai-simplify",
        "ai-verify",
        "ai-autopilot",
    }
)

# Post spec-086: 15 specialist sub-agents dispatched by orchestrators
_EXPECTED_SPECIALISTS = frozenset(
    {
        "review-context-explorer",
        "reviewer-security",
        "reviewer-backend",
        "reviewer-performance",
        "reviewer-correctness",
        "reviewer-testing",
        "reviewer-compatibility",
        "reviewer-architecture",
        "reviewer-maintainability",
        "reviewer-frontend",
        "review-finding-validator",
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
    """There should be exactly 9 orchestrator agents on disk."""
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
