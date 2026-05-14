"""OpenCode surface generators (spec-128 Wave 4, supersedes spec-133 D-133-06).

Maps the canonical ``.claude/`` tree to ``.opencode/`` per OpenCode's
native skills convention (folder per skill, agent-discovered lazy-load):

  .claude/skills/ai-<name>/SKILL.md  ->  .opencode/skills/ai-<name>/SKILL.md
  .claude/agents/ai-<name>.md        ->  .opencode/agents/ai-<name>.md

OpenCode reads ``AGENTS.md`` (project root, primary) + ``CLAUDE.md``
(fallback) for primary instructions; both are byte-equivalent to the
canonical payload, so no per-surface root rewrite is required.

The skill generator reuses ``generate_codex_skill`` (structural
equivalence with the AGENTS.md-rooted convention). OpenCode's SKILL.md
schema recognises ``name`` (1–64 chars, lowercase-alphanumeric-hyphen,
matches dir name), ``description`` (mandatory), ``license``,
``compatibility``, and ``metadata`` (string-to-string map). The Codex
generator already produces ``name`` + ``description``; extra Claude
fields are ignored gracefully.

The agent generator post-processes Codex output to translate
Claude-style color names (``red``, ``green``, ...) into OpenCode's
schema. OpenCode validates ``color`` strictly (Zod) and rejects
unrecognised values, so passthrough is not possible:

- Accepted: hex ``^#[0-9a-fA-F]{6}$`` OR semantic tokens
  ``primary | secondary | accent | success | warning | error | info``.

Researched 2026-05-14 against https://opencode.ai/docs/skills/ +
https://opencode.ai/docs/agents/.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.sync_mirrors.core import (
    generate_codex_agent,
    generate_codex_skill,
)

# Maps Claude Code's 8 named colors to OpenCode semantic tokens that
# preserve intent (success/error/warning/info) where possible. Names
# without a direct semantic counterpart route to ``primary`` / ``accent``.
_OPENCODE_COLOR_MAP = {
    "red": "error",
    "green": "success",
    "yellow": "warning",
    "blue": "info",
    "cyan": "info",
    "purple": "primary",
    "orange": "warning",
    "pink": "accent",
    "magenta": "accent",
}

_COLOR_LINE_RE = re.compile(r"^color:\s*(\S+)\s*$", re.MULTILINE)


def _translate_opencode_color(content: str) -> str:
    """Replace ``color: <claude-name>`` with an OpenCode-valid token.

    Hex values (``#RRGGBB``) and already-valid semantic tokens pass
    through unchanged.
    """

    def _repl(m: re.Match[str]) -> str:
        value = m.group(1).strip()
        if value.startswith("#"):
            return m.group(0)
        if value in _OPENCODE_COLOR_MAP.values():
            return m.group(0)
        return f"color: {_OPENCODE_COLOR_MAP.get(value, 'primary')}"

    return _COLOR_LINE_RE.sub(_repl, content)


def generate_opencode_skill(name: str, skill_path: Path) -> str:
    """Generate .opencode/skills/ai-<name>/SKILL.md (native agent-discovered skill).

    OpenCode reads on-demand skills from ``.opencode/skills/<name>/SKILL.md``
    (folder per skill). The agent scans ``name`` + ``description`` and lazy-
    loads the full file body when relevant. Frontmatter contract matches
    ``.codex/`` (AGENTS.md-rooted).
    """
    return generate_codex_skill(name, skill_path)


def generate_opencode_agent(name: str, agent_path: Path) -> str:
    """Generate .opencode/agents/ai-<name>.md with translated color."""
    return _translate_opencode_color(generate_codex_agent(name, agent_path))


__all__ = [
    "generate_opencode_agent",
    "generate_opencode_skill",
]
