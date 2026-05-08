"""``MirrorPort`` — IDE mirror tree sync abstraction.

Plus the ``ReporterPort`` — render protocol used by the conformance
report renderer. Both are kept in this module because they both deal
with the *output* surface (mirror trees on disk, Markdown rendered
to a stream/file).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class MirrorPort(Protocol):
    """Synchronise the canonical surface to one or more IDE mirrors."""

    def list_mirrors(self) -> list[Path]:
        """Return the root directories of every configured mirror."""
        ...

    def sync(self, source: Path, mapping: Mapping[Path, Path]) -> None:
        """Copy / regenerate ``source`` files into mirror destinations."""
        ...


class ReporterPort(Protocol):
    """Render a ``RubricReport`` into a target format (e.g., Markdown).

    Migrated from ``tools/skill_app/ports.py`` per spec-127 sub-006 M5.
    """

    def render(self, report: object) -> str: ...
