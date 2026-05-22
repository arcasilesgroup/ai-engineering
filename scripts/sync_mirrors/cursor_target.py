"""Cursor surface generators.

Cursor 2.4+ reads native skills from ``.cursor/skills/<name>/SKILL.md``
(folder per skill, agent-discovered lazy-load). Skills are the on-demand
counterpart to always-included rules.
"""

from __future__ import annotations

from scripts.sync_mirrors.core import (
    generate_cursor_agent,
    generate_cursor_skill,
)

__all__ = [
    "generate_cursor_agent",
    "generate_cursor_skill",
]
