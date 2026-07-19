"""Contract tests for the spec-187 D-187-03 tool-name map (wired spec-189 D-189-06).

The map at ``scripts/sync_mirrors/tool_name_map.py`` is the SINGLE SOURCE the
copilot mirror generator consumes to translate canonical tool names into VS Code
Copilot tool ids. These tests pin its invariants so it cannot silently drift
from the canonical agent tool vocabulary, and assert that ``core.py`` actually
consumes it for that translation (not a dormant reference artifact).
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.sync_mirrors.tool_name_map import (
    CANONICAL_TOOLS,
    TOOL_FAMILY_MAP,
    FamilyToolProfile,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_AGENTS_DIR = _PROJECT_ROOT / ".claude" / "agents"

# The 5 open-weight families D-187-03 must document, plus the three
# already-supported surfaces (claude native, copilot mirror, gemini).
_OPEN_WEIGHT_FAMILIES = ("kimi", "glm", "deepseek", "qwen", "mimo")
_EXPECTED_FAMILIES = ("claude", "copilot", "gemini", *_OPEN_WEIGHT_FAMILIES)


def _agent_declared_tools() -> set[str]:
    """Collect every tool literal from `.claude/agents/*.md` `tools:` frontmatter."""
    tools: set[str] = set()
    for path in _AGENTS_DIR.glob("*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^tools:\s*\[(.*)\]\s*$", line)
            if match:
                tools.update(t.strip() for t in match.group(1).split(",") if t.strip())
    return tools


def test_all_expected_families_present() -> None:
    """All 5 open-weight families + claude/copilot/gemini are documented."""
    for family in _EXPECTED_FAMILIES:
        assert family in TOOL_FAMILY_MAP, f"missing family: {family}"


def test_no_unexpected_families() -> None:
    """The map documents exactly the intended families — no accidental extras."""
    assert set(TOOL_FAMILY_MAP) == set(_EXPECTED_FAMILIES)


def test_canonical_tools_are_real_agent_literals() -> None:
    """Every CANONICAL_TOOLS entry is a real tool literal in some agent file."""
    declared = _agent_declared_tools()
    assert declared, "no tools: frontmatter found in .claude/agents/*.md"
    for tool in CANONICAL_TOOLS:
        assert tool in declared, f"{tool!r} not declared in any .claude/agents/*.md"


def test_mimo_flagged_unverified() -> None:
    """MiMo carries no live-behavior claim (D-187-08)."""
    assert TOOL_FAMILY_MAP["mimo"].verified is False


def test_non_mimo_families_are_verified() -> None:
    """Every family except MiMo is backed by a primary portability source."""
    for family, profile in TOOL_FAMILY_MAP.items():
        if family == "mimo":
            continue
        assert profile.verified is True, f"{family} unexpectedly unverified"


def test_records_are_internally_consistent() -> None:
    """No record is empty; every field carries real content."""
    for family, profile in TOOL_FAMILY_MAP.items():
        assert isinstance(profile, FamilyToolProfile)
        assert profile.tool_name_style.strip(), f"{family}: empty tool_name_style"
        assert profile.call_format_notes.strip(), f"{family}: empty call_format_notes"


def test_only_copilot_renames_tools() -> None:
    """Copilot has a name_map; open-weight families pass names through unchanged."""
    assert TOOL_FAMILY_MAP["copilot"].name_map is not None
    for family in _OPEN_WEIGHT_FAMILIES:
        assert TOOL_FAMILY_MAP[family].name_map is None, f"{family} should pass through"


def test_copilot_name_map_covers_canonical_tools() -> None:
    """The Copilot rename map translates every canonical tool name."""
    name_map = TOOL_FAMILY_MAP["copilot"].name_map
    assert name_map is not None
    for tool in CANONICAL_TOOLS:
        assert tool in name_map, f"copilot name_map missing {tool!r}"
        assert name_map[tool].strip(), f"copilot name_map has empty target for {tool!r}"


# ── Consumption: core.py sources its copilot translation from THIS map ───────
# spec-189 D-189-06: the map is no longer inert — the mirror generator reads it
# as the single source for canonical→VS-Code tool-name translation.


def test_core_translation_source_is_this_map() -> None:
    """`core.py` builds its copilot translation FROM `TOOL_FAMILY_MAP` (no dupe)."""
    from scripts.sync_mirrors.core import _COPILOT_NAME_MAP

    assert TOOL_FAMILY_MAP["copilot"].name_map == _COPILOT_NAME_MAP


def test_core_translate_helper_renames_via_map() -> None:
    """`core._translate_copilot_tools` yields exactly the map's target ids."""
    from scripts.sync_mirrors.core import _translate_copilot_tools

    name_map = TOOL_FAMILY_MAP["copilot"].name_map
    assert name_map is not None
    assert _translate_copilot_tools(CANONICAL_TOOLS) == set(name_map.values())


def test_generated_copilot_agent_emits_mapped_tool_names() -> None:
    """Generating a copilot agent yields mapped ids, not canonical tool names."""
    from scripts.sync_mirrors.core import (
        AGENT_METADATA,
        CLAUDE_AGENTS,
        generate_copilot_agent,
    )

    meta = AGENT_METADATA["build"]
    content = generate_copilot_agent("build", meta, CLAUDE_AGENTS / "ai-build.md")
    tools_line = next(line for line in content.splitlines() if line.startswith("tools: ["))

    name_map = TOOL_FAMILY_MAP["copilot"].name_map
    assert name_map is not None
    # Every renamed canonical tool surfaces as its MAPPED id, never the
    # canonical name, and the mapped id is sourced from THIS map.
    for canonical in meta.copilot_renamed_tools:
        mapped = name_map[canonical]
        assert mapped in tools_line, f"expected mapped {mapped!r} in {tools_line!r}"
        assert f" {canonical}" not in tools_line and f"[{canonical}" not in tools_line, (
            f"canonical {canonical!r} leaked untranslated into {tools_line!r}"
        )
