"""``SkillScannerPort`` — read SKILL.md files into domain ``Skill`` objects.

Migrated from ``tools/skill_app/ports.py`` per spec-127 sub-006 M5.
"""

from __future__ import annotations

from typing import Protocol

from skill_domain.skill_model import Skill


class SkillScannerPort(Protocol):
    """Read SKILL.md files into ``Skill`` domain objects.

    Implementations must walk a skills root directory in parallel and
    return one ``Skill`` per ``<root>/<name>/SKILL.md`` discovered.
    """

    def scan_skills(self) -> list[Skill]: ...
