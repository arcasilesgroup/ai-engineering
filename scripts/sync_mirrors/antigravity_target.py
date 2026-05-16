"""Antigravity surface generators (spec-133 D-133-06 — MIRROR-ONLY).

Per research artifact ``.ai-engineering/research/ide-hook-engines-2026-05-12.md``
and Google staff statement on the Antigravity forum, Antigravity does
NOT support hooks today (workaround-only). The framework treats it as
mirror-only: copy instruction payload to ``GEMINI.md`` (priority 1) and
``AGENTS.md`` (v1.20.3+) at the repo root; copy skills to
``.agent/skills/`` and workflows to ``.agent/workflows/``.

No hook adapter is shipped. Re-evaluate post-v2.x if Google ships hooks.

Mapping:
  .claude/skills/ai-<name>/SKILL.md  ->  .agent/skills/ai-<name>/SKILL.md
  .claude/agents/ai-<name>.md        ->  .agent/agents/ai-<name>.md
"""

from __future__ import annotations

from pathlib import Path

from scripts.sync_mirrors.core import (
    generate_gemini_agent,
    generate_gemini_skill,
)


def generate_antigravity_skill(name: str, skill_path: Path) -> str:
    """Generate .agent/skills/ai-<name>/SKILL.md (mirror-only)."""
    return generate_gemini_skill(name, skill_path)


def generate_antigravity_agent(name: str, agent_path: Path) -> str:
    """Generate .agent/agents/ai-<name>.md (mirror-only)."""
    return generate_gemini_agent(name, agent_path)


__all__ = [
    "generate_antigravity_agent",
    "generate_antigravity_skill",
]
