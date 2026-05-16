"""Skill domain model — frozen dataclasses parsed from SKILL.md files.

Stub for Phase B/C RED collection. Real implementation lands in
Phase D T-D.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Frontmatter:
    """SKILL.md frontmatter — only ``name`` and ``description`` per Anthropic standard."""

    name: str
    description: str
    extra_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class Skill:
    """Parsed SKILL.md."""

    path: Path
    frontmatter: Frontmatter
    body: str
    line_count: int
    token_estimate: int
    sections: tuple[str, ...] = ()
    examples_count: int = 0
    refs_paths: tuple[Path, ...] = ()
    anti_pattern_hits: tuple[str, ...] = ()
    has_evals: bool = False
    eval_count: int = 0
    optimizer_committed: bool = False
    extra_fm_fields: tuple[str, ...] = field(default_factory=tuple)
