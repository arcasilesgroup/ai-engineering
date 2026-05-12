"""Cursor surface generators (spec-133 D-133-06, D-133-07).

Cursor reads granular ``.mdc`` rules from ``.cursor/rules/`` (D-133-07).
Per-rule selective application (``@``-mention) requires one .mdc per
skill — single-file .mdc loses this UX.

Mapping:
  .claude/skills/ai-<name>/SKILL.md  ->  .cursor/rules/ai-<name>.mdc
  .claude/agents/ai-<name>.md        ->  .cursor/agents/ai-<name>.mdc

Reuses the gemini generator path because Gemini's content shape is the
closest match for Cursor's ``.mdc`` (markdown with optional glob frontmatter).
"""

from __future__ import annotations

from pathlib import Path

from scripts.sync_mirrors.core import (
    generate_gemini_agent,
    generate_gemini_skill,
)


def generate_cursor_skill(name: str, skill_path: Path) -> str:
    """Generate .cursor/rules/ai-<name>.mdc."""
    return generate_gemini_skill(name, skill_path)


def generate_cursor_agent(name: str, agent_path: Path) -> str:
    """Generate .cursor/agents/ai-<name>.mdc."""
    return generate_gemini_agent(name, agent_path)


__all__ = [
    "generate_cursor_agent",
    "generate_cursor_skill",
]
