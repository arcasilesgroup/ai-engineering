"""GitHub Copilot Agent Skills surface generators."""

from __future__ import annotations

from scripts.sync_mirrors.core import (
    generate_copilot_agent,
    generate_copilot_handler,
    generate_copilot_instructions,
    generate_copilot_skill,
    is_copilot_compatible,
)

__all__ = [
    "generate_copilot_agent",
    "generate_copilot_handler",
    "generate_copilot_instructions",
    "generate_copilot_skill",
    "is_copilot_compatible",
]
