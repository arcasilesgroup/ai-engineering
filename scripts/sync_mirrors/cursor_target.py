"""Cursor surface generators.

spec-201 D-201-04: the Cursor 3.x discovery allowlist contains
``.agents/skills/``, so Cursor now reads the shared skill tree the
installer ships and ``.cursor/skills`` was hard-deleted — it shipped 54
skill directories with zero ``handlers/``, which stopped ``/ai-build`` at
preflight for every Cursor consumer. Agents stay at
``.cursor/agents/<name>.mdc`` (D-201-22).
"""

from __future__ import annotations

from scripts.sync_mirrors.core import generate_cursor_agent

__all__ = ["generate_cursor_agent"]
