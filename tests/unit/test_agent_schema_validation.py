"""Validate agent definitions in .ai-engineering/agents/ against architecture v3.

Unlike test_validator.py which creates isolated fixture worlds, these tests
parametrize against the REAL .ai-engineering/agents/ directory. If an agent
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
    / ".ai-engineering"
    / "agents"
)

# Architecture v3: 8 agents
_EXPECTED_AGENTS = frozenset(
    {
        "build",
        "explorer",
        "guard",
        "guide",
        "operate",
        "plan",
        "simplifier",
        "verify",
    }
)

_REQUIRED_FRONTMATTER = {"name"}


def _all_agent_files() -> list[Path]:
    """Return all .md files in the agents directory."""
    if not _AGENTS_DIR.is_dir():
        return []
    return sorted(_AGENTS_DIR.glob("*.md"))


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


# ── Tests ────────────────────────────────────────────────────────────────


def test_agent_count_matches_expected() -> None:
    """There should be exactly 8 agents on disk (architecture v3)."""
    agents = _all_agent_files()
    names = {f.stem for f in agents}
    assert len(agents) == len(_EXPECTED_AGENTS), (
        f"Expected {len(_EXPECTED_AGENTS)} agents, found {len(agents)}: {sorted(names)}"
    )


def test_agent_names_match_expected() -> None:
    """Agent file names must match the architecture v3 set exactly."""
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
def test_agent_has_identity_section(agent_file: Path) -> None:
    """Every agent must have an ## Identity section."""
    text = agent_file.read_text(encoding="utf-8")
    assert "## Identity" in text or "## Supported Stacks" in text, (
        f"{agent_file.name}: missing '## Identity' section"
    )
