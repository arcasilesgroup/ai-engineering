"""Antigravity host adapter (spec-194)."""

from __future__ import annotations

from pathlib import Path

from ..schema import CatalogMetrics, HookMetrics, McpResidue, RootMetrics
from . import HostAdapter


class AntigravityAdapter(HostAdapter):
    @property
    def host_id(self) -> str:
        return "antigravity"

    @property
    def _default_root_paths(self) -> list[Path]:
        return [Path(".agents/AGENTS.md"), Path("AGENTS.md")]

    @property
    def _default_skills_dir(self) -> Path:
        return Path(".agents/skills")

    @property
    def _default_mcp_config_paths(self) -> list[Path]:
        return []

    def _determine_verdict(
        self, root: RootMetrics, catalog: CatalogMetrics, hooks: HookMetrics, mcp: McpResidue
    ) -> str:
        # Antigravity is unproven - always UNVERIFIED
        return "UNVERIFIED"
