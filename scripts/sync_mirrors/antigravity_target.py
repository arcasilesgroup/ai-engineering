"""Antigravity surface generators.

Antigravity app and `agy` CLI share one workspace surface:

  .claude/skills/ai-<name>/SKILL.md  ->  .agents/skills/ai-<name>/SKILL.md
  .claude/agents/ai-<name>.md        ->  .agents/agents/ai-<name>.md

Root context is AGENTS.md. The retired Gemini CLI surface no longer owns
GEMINI.md or .gemini/ generated output in ai-engineering.
"""

from __future__ import annotations

from scripts.sync_mirrors.core import (
    generate_antigravity_agent,
    generate_antigravity_skill,
)

__all__ = [
    "generate_antigravity_agent",
    "generate_antigravity_skill",
]
