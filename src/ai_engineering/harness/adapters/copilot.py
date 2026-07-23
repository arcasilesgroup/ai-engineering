"""GitHub Copilot host adapter (spec-194)."""

from __future__ import annotations

from pathlib import Path

from ..schema import CatalogMetrics, HookMetrics, McpResidue, RootMetrics
from . import HostAdapter


class CopilotAdapter(HostAdapter):
    @property
    def host_id(self) -> str:
        return "github-copilot"

    @property
    def root_paths(self) -> list[Path]:
        return [Path(".github/copilot-instructions.md"), Path("AGENTS.md")]

    @property
    def skills_dir(self) -> Path:
        return Path(".github/skills")

    @property
    def mcp_config_paths(self) -> list[Path]:
        return [Path(".github/copilot-mcp.json")]

    def _determine_verdict(
        self, root: RootMetrics, catalog: CatalogMetrics, hooks: HookMetrics, mcp: McpResidue
    ) -> str:
        if root.bytes > 2048:
            return "fail"
        if catalog.duplicate_ids > 0:
            return "fail"
        return "pass"
