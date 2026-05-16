"""Validate agent definitions in .ai-engineering/agents/ against architecture v3.

Unlike test_validator.py which creates isolated fixture worlds, these tests
parametrize against the REAL .ai-engineering/agents/ template directory. If an agent
is added, removed, or has broken frontmatter, these tests FAIL.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ai_engineering.config.framework_defaults import DEFAULT_AGENTS_NAMES

_AGENTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "ai_engineering"
    / "templates"
    / "project"
    / ".claude"
    / "agents"
)

# Orchestrators are the canonical first-class agent surface (CLAUDE.md §12
# contract "Agents (9)"). Derived dynamically from
# DEFAULT_AGENTS_NAMES — the same source `sync_mirrors.core.discover_agents`
# uses — so adding/removing an agent updates one place, not two.
_EXPECTED_ORCHESTRATORS = frozenset({f"ai-{name}" for name in DEFAULT_AGENTS_NAMES})

# Specialist sub-agents are discovered by prefix (no enumerated contract).
# `validator.categories.mirror_sync._SPECIALIST_AGENT_PREFIXES` is the
# canonical glob set: `reviewer-`, `verifier-`, `review-`, `verify-`.
_SPECIALIST_PREFIXES: tuple[str, ...] = ("reviewer-", "verifier-", "review-", "verify-")

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


def test_orchestrator_count_matches_canonical_registry() -> None:
    """Disk must match DEFAULT_AGENTS_NAMES count — single source of truth."""
    agents = _orchestrator_files()
    names = {f.stem for f in agents}
    assert len(agents) == len(_EXPECTED_ORCHESTRATORS), (
        f"Expected {len(_EXPECTED_ORCHESTRATORS)} orchestrators (per "
        f"DEFAULT_AGENTS_NAMES), found {len(agents)}: {sorted(names)}"
    )


def test_orchestrator_names_match_canonical_registry() -> None:
    """Disk names must match DEFAULT_AGENTS_NAMES exactly — no drift."""
    agents = _orchestrator_files()
    names = {f.stem for f in agents}
    assert names == _EXPECTED_ORCHESTRATORS, (
        f"Orchestrator drift vs DEFAULT_AGENTS_NAMES. "
        f"Missing: {_EXPECTED_ORCHESTRATORS - names}, "
        f"Extra: {names - _EXPECTED_ORCHESTRATORS}"
    )


def test_every_non_orchestrator_uses_specialist_prefix() -> None:
    """Anything in agents/ that isn't an orchestrator MUST be a specialist."""
    extras = {f.stem for f in _all_agent_files()} - _EXPECTED_ORCHESTRATORS
    invalid = {
        name
        for name in extras
        if not any(name.startswith(prefix) for prefix in _SPECIALIST_PREFIXES)
    }
    assert not invalid, (
        f"Files in agents/ that are neither orchestrators nor specialists "
        f"(reviewer-*/verifier-*/review-*/verify-*): {sorted(invalid)}"
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
