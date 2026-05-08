"""``LessonsPort`` adapter — parse ``LESSONS.md`` H3 sections per skill.

Sub-007 M6 infrastructure layer. The adapter reads the canonical
``LESSONS.md`` (operator-authored corrections) and returns the H3
section bodies that mention the requested skill name.

Format assumed: standard CommonMark with ``###`` headings. The
parser is regex-based rather than CommonMark-AST-based because the
file is small (a few hundred lines at most) and the contract is
narrow (return matching section bodies). Pulling in a Markdown
parser would be over-engineering at the pilot scope.
"""

from __future__ import annotations

import re
from pathlib import Path

from skill_app.ports.lessons import LessonsPort

# ``###`` followed by anything up to end-of-line. Used to chunk the
# file into per-section bodies without an AST walker.
_H3_RE = re.compile(r"^###\s+(.*)$", re.MULTILINE)


class LessonsMdParser(LessonsPort):
    """Read operator-authored lessons keyed by skill name from ``LESSONS.md``."""

    def __init__(self, lessons_path: Path) -> None:
        self._path = lessons_path

    def lessons_for_skill(self, skill_name: str) -> tuple[str, ...]:
        """Return the H3-section bodies that mention ``skill_name``.

        Matching is liberal:
        - substring match against the H3 title (case-insensitive);
        - substring match against the H3 body (case-insensitive).
        Either positive ⇒ the body is returned.
        """
        if not self._path.exists():
            return ()
        text = self._path.read_text(encoding="utf-8")

        # Find every H3 boundary; chunk the file by them.
        boundaries = [(m.start(), m.group(1)) for m in _H3_RE.finditer(text)]
        if not boundaries:
            return ()
        boundaries.append((len(text), ""))  # sentinel for the last chunk.

        needle = skill_name.lower()
        sections: list[str] = []
        for idx in range(len(boundaries) - 1):
            start, title = boundaries[idx]
            end, _ = boundaries[idx + 1]
            body = text[start:end]
            if needle in title.lower() or needle in body.lower():
                sections.append(body.strip())
        return tuple(sections)


__all__ = ["LessonsMdParser"]
