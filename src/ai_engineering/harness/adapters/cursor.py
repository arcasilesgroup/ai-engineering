"""Cursor host adapter (spec-194)."""

from __future__ import annotations

from pathlib import Path

from ..schema import CatalogMetrics, HookMetrics, McpResidue, RootMetrics
from . import HostAdapter


class CursorAdapter(HostAdapter):
    @property
    def host_id(self) -> str:
        return "cursor"

    @property
    def _default_root_paths(self) -> list[Path]:
        return [Path(".cursor/AGENTS.md"), Path("AGENTS.md")]

    @property
    def _default_skills_dir(self) -> Path:
        return Path(".cursor/skills")

    @property
    def _default_mcp_config_paths(self) -> list[Path]:
        return [Path(".cursor/mcp.json")]

    def _determine_verdict(
        self, root: RootMetrics, catalog: CatalogMetrics, hooks: HookMetrics, mcp: McpResidue
    ) -> str:
        if root.bytes > 2048:
            return "fail"
        if catalog.duplicate_ids > 0:
            return "fail"
        return "pass"
