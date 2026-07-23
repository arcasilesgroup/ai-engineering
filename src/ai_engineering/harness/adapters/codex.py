"""Codex host adapter (spec-194).

Probes Codex's skill discovery, hook injection and root instructions.
"""

from __future__ import annotations

from pathlib import Path

from ..schema import (
    CatalogMetrics,
    HookMetrics,
    McpResidue,
    RootMetrics,
)
from . import HostAdapter


class CodexAdapter(HostAdapter):
    """Codex host adapter."""

    @property
    def host_id(self) -> str:
        return "codex"

    @property
    def root_paths(self) -> list[Path]:
        return [
            Path(".codex/AGENTS.md"),
            Path("AGENTS.md"),
        ]

    @property
    def skills_dir(self) -> Path:
        return Path(".codex/skills")

    @property
    def commands_dir(self) -> Path | None:
        return None

    @property
    def hooks_dir(self) -> Path:
        return Path(".ai-engineering/scripts/hooks")

    @property
    def mcp_config_paths(self) -> list[Path]:
        return [
            Path(".codex/mcp.json"),
        ]

    def _determine_verdict(
        self,
        root: RootMetrics,
        catalog: CatalogMetrics,
        hooks: HookMetrics,
        mcp: McpResidue,
    ) -> str:
        """Codex verdict logic."""
        # Fail if root is too large (>2 KiB)
        if root.bytes > 2048:
            return "fail"

        # Fail if duplicate skills exist
        if catalog.duplicate_ids > 0:
            return "fail"

        return "pass"
