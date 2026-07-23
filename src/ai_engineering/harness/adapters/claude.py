"""Claude Code host adapter (spec-194).

Probes Claude Code's skill discovery, hook injection and root instructions.
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


class ClaudeAdapter(HostAdapter):
    """Claude Code host adapter."""

    @property
    def host_id(self) -> str:
        return "claude-code"

    @property
    def root_paths(self) -> list[Path]:
        return [
            Path(".claude/AGENTS.md"),
            Path("AGENTS.md"),
            Path("CLAUDE.md"),
        ]

    @property
    def skills_dir(self) -> Path:
        return Path(".claude/skills")

    @property
    def commands_dir(self) -> Path | None:
        return None  # Claude uses skills, not commands

    @property
    def hooks_dir(self) -> Path:
        return Path(".ai-engineering/scripts/hooks")

    @property
    def mcp_config_paths(self) -> list[Path]:
        return [
            Path(".claude/mcp.json"),
            Path(".claude/mcp_servers.json"),
        ]

    def _determine_verdict(
        self,
        root: RootMetrics,
        catalog: CatalogMetrics,
        hooks: HookMetrics,
        mcp: McpResidue,
    ) -> str:
        """Claude Code verdict logic."""
        # Fail if root is too large (>2 KiB)
        if root.bytes > 2048:
            return "fail"

        # Fail if duplicate skills exist
        if catalog.duplicate_ids > 0:
            return "fail"

        # Fail if hooks inject context
        if hooks.injection_count > 0:
            return "fail"

        # Pass if all checks pass
        return "pass"
