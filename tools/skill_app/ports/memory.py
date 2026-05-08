"""``MemoryPort`` — persistent-memory abstraction (Engram, etc.).

Memory is an *optional* third-party integration per the project
charter. The application layer treats memory as a port so the
``no_op`` adapter can be substituted whenever the operator skipped
the Engram install.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class MemoryPort(Protocol):
    """Save and retrieve cross-session observations."""

    def save(self, topic: str, body: str, tags: tuple[str, ...] = ()) -> str:
        """Persist an observation; return its provider-specific ID."""
        ...

    def search(self, query: str, limit: int = 10) -> Iterable[dict[str, object]]:
        """Return up to ``limit`` matches ranked by relevance."""
        ...
