"""OpenCode surface generators (spec-128 Wave 4, supersedes spec-133 D-133-06).

Maps the canonical ``.claude/`` tree to ``.opencode/`` per OpenCode's
native skills convention (folder per skill, agent-discovered lazy-load):

  .claude/skills/ai-<name>/SKILL.md  ->  .opencode/skills/ai-<name>/SKILL.md
  .claude/skills/ai-<name>/SKILL.md  ->  .opencode/commands/ai-<name>.md
  .claude/agents/ai-<name>.md        ->  .opencode/agents/ai-<name>.md

OpenCode separates two surfaces (https://opencode.ai/docs/skills/ +
https://opencode.ai/docs/commands/):

* ``skills/`` — agent-discovered, lazy-loaded, NOT visible in the ``/``
  slash menu. The agent sees ``name`` + ``description`` and loads the
  full body via the ``skill`` tool when relevant.
* ``commands/`` — saved-prompt slash commands that DO appear in ``/``
  menu. Each command body is a prompt template.

Both surfaces are required: skills give the agent on-demand expertise,
commands give the human the muscle-memory ``/ai-<name>`` entry point
they expect from Claude Code parity. The command body is a thin
wrapper that invokes the skill by name (the agent then lazy-loads the
canonical body via the ``skill`` tool), so the skill remains SSOT.

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
https://opencode.ai/docs/commands/ + https://opencode.ai/docs/agents/.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

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


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _extract_skill_description(name: str, skill_path: Path) -> str:
    """Read ``description`` from the canonical SKILL.md frontmatter.

    Falls back to a generic stub if the file is malformed; the validator
    upstream (``tools/skill_lint``) already enforces a description, so
    the fallback is defensive rather than load-bearing.

    ``name`` is the skill slug without the ``ai-`` prefix (as passed by
    ``core.py``).
    """
    fallback = f"Invoke the ai-{name} skill."
    raw = skill_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return fallback
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return fallback
    desc = data.get("description")
    if isinstance(desc, str) and desc.strip():
        return desc.strip()
    return fallback


def generate_opencode_command(name: str, skill_path: Path) -> str:
    """Generate .opencode/commands/ai-<name>.md (slash-menu wrapper).

    Emits a thin saved-prompt command whose body asks the agent to use
    the matching ``ai-<name>`` skill. OpenCode 1.14+ lazy-loads the
    skill body via the ``skill`` tool once the name appears in the
    prompt context, so the command stays a few hundred bytes and the
    canonical SKILL.md remains the single source of truth.

    The frontmatter carries only ``description`` (mandatory per
    https://opencode.ai/docs/commands/). No ``agent`` / ``model``
    override — the user's default agent picks up the skill's own
    ``model_tier`` advice from the lazy-loaded SKILL.md.
    """
    description = _extract_skill_description(name, skill_path)
    # Force a single-line scalar (width=inf) and strip the trailing newline
    # that PyYAML appends. ``default_style="'"`` quotes consistently so embedded
    # ``:`` and ``#`` do not break the YAML.
    desc_yaml = yaml.safe_dump(
        description,
        default_style="'",
        default_flow_style=True,
        width=10_000,
        allow_unicode=True,
    ).strip()
    return (
        "---\n"
        f"description: {desc_yaml}\n"
        "mirror_family: opencode-commands\n"
        "generated_by: ai-eng sync\n"
        f"canonical_source: .claude/skills/ai-{name}/SKILL.md\n"
        "edit_policy: generated-do-not-edit\n"
        "---\n"
        "\n"
        f"Use the `ai-{name}` skill to handle this request. "
        "OpenCode will lazy-load the canonical skill body via the "
        "`skill` tool; arguments below are forwarded verbatim.\n"
        "\n"
        "$ARGUMENTS\n"
    )


__all__ = [
    "generate_opencode_agent",
    "generate_opencode_command",
    "generate_opencode_skill",
]
