"""Detector package for ai-engineering framework."""

from __future__ import annotations

from ai_engineering.detector.readiness import (
    check_all_tools,
    check_tools_for_stacks,
    is_tool_available,
)

__all__ = [
    "check_all_tools",
    "check_tools_for_stacks",
    "is_tool_available",
]
