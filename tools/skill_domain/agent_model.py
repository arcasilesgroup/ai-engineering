"""Agent domain model — frozen dataclass parsed from agent .md files.

Stub for Phase B/C RED collection. Real implementation lands in
Phase D T-D.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentFrontmatter:
    """Agent ``.md`` frontmatter."""

    name: str
    description: str
    model: str | None
    tools: tuple[str, ...]
    extra_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class Agent:
    """Parsed agent ``.md``."""

    path: Path
    frontmatter: AgentFrontmatter
    body: str
    line_count: int
    dispatched_by: tuple[Path, ...] = ()
