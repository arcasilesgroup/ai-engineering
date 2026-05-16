"""``HookPort`` — read/verify Claude-Code hook scripts and their manifest.

Application layer contract for hook-bytes integrity per spec-120 (the
``.ai-engineering/state/hooks-manifest.json`` sha256 pin). The infra
adapter wraps the manifest read/regenerate path; use cases call into
this port without knowing whether the manifest lives on disk, in git
LFS, or behind a remote signing service.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class HookPort(Protocol):
    """Verify and enumerate Claude-Code hook scripts."""

    def list_hooks(self) -> list[Path]:
        """Return the paths of every canonical hook script."""
        ...

    def manifest(self) -> Mapping[str, str]:
        """Return the ``hook_path → sha256`` mapping."""
        ...

    def verify(self, hook_path: Path) -> bool:
        """``True`` iff ``hook_path`` matches its manifest entry."""
        ...
