"""GitHub Copilot agent-persona surface generators.

spec-201 D-201-04: `.github/skills` was hard-deleted — Copilot reads the
shared `.agents/skills` tree — so the skill and handler generators, along
with the `copilot_compatible` opt-out filter that only they consulted,
went with it. Only the agent-persona and instruction-file generators
remain (D-201-22).
"""

from __future__ import annotations

from scripts.sync_mirrors.core import (
    generate_copilot_agent,
    generate_copilot_instructions,
)

__all__ = [
    "generate_copilot_agent",
    "generate_copilot_instructions",
]
