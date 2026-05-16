"""``BoardPort`` — issue / project-board provider abstraction.

Both Azure DevOps and GitHub adapters implement this single port so
use cases (work-item sync, label propagation) stay provider-agnostic.
The application layer never imports the provider SDKs; concrete
``infra`` adapters do.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol


class BoardPort(Protocol):
    """Read and update issues / work items on a board provider."""

    def list_open_items(self, label: str | None = None) -> Iterable[Mapping[str, object]]:
        """Yield open work items, optionally filtered by ``label``."""
        ...

    def get_item(self, item_id: str) -> Mapping[str, object]:
        """Return one work item by provider-specific ID."""
        ...

    def add_comment(self, item_id: str, body: str) -> None:
        """Post a comment on a work item."""
        ...
