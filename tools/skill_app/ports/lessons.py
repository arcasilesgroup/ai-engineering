"""``LessonsPort`` — read accumulated operator lessons from ``LESSONS.md``.

The skill-tune workflow ingests three signal sources to propose a
description rewrite: prior eval corpora, Engram observations, and
``LESSONS.md`` entries (operator-authored corrections). This port
exposes only the third — Engram lives behind the existing
:class:`~skill_app.ports.memory.MemoryPort`, eval corpora are read
directly from disk by the runner.

The contract is intentionally narrow: filter by skill name, return
the matching H3-section bodies. Parsing details (regex, frontmatter,
H3 walker behaviour) belong in the infra adapter.
"""

from __future__ import annotations

from typing import Protocol


class LessonsPort(Protocol):
    """Read operator-authored lessons keyed by skill name."""

    def lessons_for_skill(self, skill_name: str) -> tuple[str, ...]:
        """Return the H3-section bodies that mention ``skill_name``.

        Implementations may match liberally (substring of the H3
        title, frontmatter tag, body mention) so the operator does
        not have to use an exact key. Returning an empty tuple is a
        valid result: it means there are no lessons recorded for
        this skill, and the tune-skill flow proceeds with eval +
        Engram signals only.
        """
        ...
