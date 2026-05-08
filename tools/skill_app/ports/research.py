"""``ResearchPort`` — external knowledge fetcher (Context7, NotebookLM, …).

Application layer use cases that need fresh library / spec / paper
context call into this port. Concrete adapters wrap MCP clients,
HTTP fetchers, or local cache stores. The default no-op adapter
returns an empty result set so use cases degrade gracefully when no
research backend is configured.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol


class ResearchPort(Protocol):
    """Resolve and query external research sources."""

    def resolve(self, query: str) -> str | None:
        """Return a backend-specific resource ID for ``query`` (or ``None``)."""
        ...

    def fetch(self, resource_id: str, query: str) -> Iterable[Mapping[str, object]]:
        """Yield documents (title + body chunks) matching ``query``."""
        ...
