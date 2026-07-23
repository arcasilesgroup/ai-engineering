"""Host adapters for the context safety harness (spec-194 D-194-01).

Each adapter owns host-specific probes. The domain owns normalization,
duplicate detection, budgets and verdicts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..collector import (
    collect_catalog_metrics,
    collect_hook_metrics,
    collect_mcp_residue,
    collect_root_metrics,
)
from ..schema import (
    SCHEMA_VERSION,
    CatalogMetrics,
    ContextSafetyReport,
    HookMetrics,
    McpResidue,
    OutputBounds,
    RootMetrics,
)


class HostAdapter(ABC):
    """Base class for host-specific adapters."""

    @property
    @abstractmethod
    def host_id(self) -> str:
        """Unique identifier for this host."""

    @property
    @abstractmethod
    def root_paths(self) -> list[Path]:
        """Paths to root instruction files for this host."""

    @property
    @abstractmethod
    def skills_dir(self) -> Path:
        """Path to the skills directory."""

    @property
    def commands_dir(self) -> Path | None:
        """Path to commands directory (if any)."""
        return None

    @property
    def hooks_dir(self) -> Path:
        """Path to hooks directory."""
        return Path(".ai-engineering/scripts/hooks")

    @property
    def mcp_config_paths(self) -> list[Path]:
        """Paths to MCP configuration files."""
        return []

    def collect(self, fixture_name: str = "live") -> ContextSafetyReport:
        """Collect metrics from this host's configuration."""
        # Collect root metrics (merge all root paths)
        root_metrics = RootMetrics(
            bytes=0,
            estimated_tokens=0,
            mandatory_reads=0,
            source_path=str(self.root_paths[0]) if self.root_paths else "",
        )
        for root_path in self.root_paths:
            rm = collect_root_metrics(root_path)
            root_metrics = RootMetrics(
                bytes=root_metrics.bytes + rm.bytes,
                estimated_tokens=root_metrics.estimated_tokens + rm.estimated_tokens,
                mandatory_reads=root_metrics.mandatory_reads + rm.mandatory_reads,
                source_path=root_metrics.source_path or rm.source_path,
            )

        # Collect catalog metrics
        catalog = collect_catalog_metrics(self.skills_dir)
        if self.commands_dir:
            cmd_catalog = collect_catalog_metrics(self.commands_dir)
            catalog = CatalogMetrics(
                unique_ids=catalog.unique_ids + cmd_catalog.unique_ids,
                duplicate_ids=catalog.duplicate_ids + cmd_catalog.duplicate_ids,
                total_skills=catalog.total_skills + cmd_catalog.total_skills,
                duplicate_ids_list=sorted(
                    set(catalog.duplicate_ids_list + cmd_catalog.duplicate_ids_list)
                ),
            )

        # Collect hook metrics
        hooks = collect_hook_metrics(self.hooks_dir)

        # Collect MCP residue
        mcp = collect_mcp_residue(self.mcp_config_paths)

        # Determine verdict
        verdict = self._determine_verdict(root_metrics, catalog, hooks, mcp)

        return ContextSafetyReport(
            schema_version=SCHEMA_VERSION,
            host=self.host_id,
            fixture=fixture_name,
            root=root_metrics,
            catalog=catalog,
            hooks=hooks,
            mcp_residue=mcp,
            output_bounds=OutputBounds(),
            verdict=verdict,
            redacted=True,
        )

    def _determine_verdict(
        self,
        root: RootMetrics,
        catalog: CatalogMetrics,
        hooks: HookMetrics,
        mcp: McpResidue,
    ) -> str:
        """Determine pass/fail/UNVERIFIED verdict.

        Override in subclasses for host-specific logic.
        """
        # Default: UNVERIFIED (no evidence = no pass)
        return "UNVERIFIED"
