"""OpenCode surface generators (spec-133 D-133-06).

Maps the canonical ``.claude/`` tree to ``.opencode/`` per OpenCode's
plugin + commands convention:

  .claude/skills/ai-<name>/SKILL.md  ->  .opencode/commands/ai-<name>.md
  .claude/agents/ai-<name>.md        ->  .opencode/agents/ai-<name>.md

OpenCode reads ``AGENTS.md`` (project root, primary) + ``CLAUDE.md``
(fallback) for primary instructions; both are byte-equivalent to the
canonical payload, so no per-surface root rewrite is required.

The generator reuses :func:`generate_codex_skill` / agent helpers
(structural equivalence with the AGENTS.md-rooted convention).
"""

from __future__ import annotations

from pathlib import Path

from scripts.sync_mirrors.core import (
    generate_codex_agent,
    generate_codex_skill,
)


def generate_opencode_skill(name: str, skill_path: Path) -> str:
    """Generate .opencode/commands/ai-<name>.md (slash command).

    OpenCode slash commands live under ``.opencode/commands/`` and
    register as ``/<filename>`` automatically. Frontmatter contract
    matches ``.codex/`` (AGENTS.md-rooted).
    """
    return generate_codex_skill(name, skill_path)


def generate_opencode_agent(name: str, agent_path: Path) -> str:
    """Generate .opencode/agents/ai-<name>.md."""
    return generate_codex_agent(name, agent_path)


__all__ = [
    "generate_opencode_agent",
    "generate_opencode_skill",
]
