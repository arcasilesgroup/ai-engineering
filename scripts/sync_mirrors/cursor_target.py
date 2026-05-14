"""Cursor surface generators (spec-128 Wave 4, supersedes spec-133 D-133-07).

Cursor 2.4+ reads native skills from ``.cursor/skills/<name>/SKILL.md``
(folder per skill, agent-discovered lazy-load). Skills are the on-demand
counterpart to always-included rules — wrong fit for 48 framework skills
that should load only when relevant.

Mapping:
  .claude/skills/ai-<name>/SKILL.md  ->  .cursor/skills/ai-<name>/SKILL.md
  .claude/agents/ai-<name>.md        ->  .cursor/agents/ai-<name>.mdc

Reuses the gemini generator path because Gemini's content shape is the
closest match for Cursor's markdown+frontmatter format (no tool metadata).

Researched 2026-05-14 against https://cursor.com/help/customization/skills.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sync_mirrors.core import (
    generate_gemini_agent,
    generate_gemini_skill,
)


def generate_cursor_skill(name: str, skill_path: Path) -> str:
    """Generate .cursor/skills/ai-<name>/SKILL.md (native agent-discovered skill)."""
    return generate_gemini_skill(name, skill_path)


def generate_cursor_agent(name: str, agent_path: Path) -> str:
    """Generate .cursor/agents/ai-<name>.mdc."""
    return generate_gemini_agent(name, agent_path)


__all__ = [
    "generate_cursor_agent",
    "generate_cursor_skill",
]
