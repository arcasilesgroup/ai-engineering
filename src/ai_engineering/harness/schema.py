"""ContextSafetyReport schema and redaction rules (spec-194 D-194-01).

The schema is the single normalized output format for all host adapters.
Same fixture and inputs produce byte-identical JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RootMetrics:
    """Metrics for a single root instruction file."""

    bytes: int
    estimated_tokens: int
    mandatory_reads: int
    source_path: str


@dataclass(frozen=True)
class CatalogMetrics:
    """Metrics for a skill/command catalog directory."""

    unique_ids: int
    duplicate_ids: int
    total_skills: int
    duplicate_ids_list: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HookMetrics:
    """Metrics for hook injection and automatic writes."""

    injection_count: int
    additional_context_tokens: int
    automatic_writes: int
    hook_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class McpResidue:
    """Reachable third-party MCP operational residue."""

    reachable_registrations: int
    plugins: int
    permissions: int
    operational_instructions: int
    names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OutputBounds:
    """Output capping configuration."""

    normal_cap: int = 8192
    error_cap: int = 2048
    lines_cap: int = 200


@dataclass(frozen=True)
class ContextSafetyReport:
    """Complete context safety report for one host fixture.

    This is the canonical output format. Redaction is applied before
    persistence; no secret value, home path or credential key material
    appears in the report.
    """

    schema_version: str
    host: str
    fixture: str
    root: RootMetrics
    catalog: CatalogMetrics
    hooks: HookMetrics
    mcp_residue: McpResidue
    output_bounds: OutputBounds
    verdict: str  # "pass" | "fail" | "UNVERIFIED"
    redacted: bool = True

    def to_json(self) -> str:
        """Serialize to deterministic JSON (sorted keys)."""
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, data: str | dict[str, Any]) -> ContextSafetyReport:
        """Deserialize from JSON string or dict."""
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            schema_version=data["schema_version"],
            host=data["host"],
            fixture=data["fixture"],
            root=RootMetrics(**data["root"]),
            catalog=CatalogMetrics(**data["catalog"]),
            hooks=HookMetrics(**data["hooks"]),
            mcp_residue=McpResidue(**data["mcp_residue"]),
            output_bounds=OutputBounds(**data["output_bounds"]),
            verdict=data["verdict"],
            redacted=data.get("redacted", True),
        )

    def truncate_to_budget(self, max_bytes: int = 8192) -> str:
        """Truncate serialized report to byte budget, preserving validity."""
        full = self.to_json()
        if len(full.encode("utf-8")) <= max_bytes:
            return full
        # Build a minimal valid JSON with truncation marker
        minimal = {
            "schema_version": self.schema_version,
            "host": self.host,
            "fixture": self.fixture,
            "verdict": self.verdict,
            "truncated": True,
            "original_bytes": len(full.encode("utf-8")),
        }
        result = json.dumps(minimal, indent=2, sort_keys=True)
        if len(result.encode("utf-8")) > max_bytes:
            return '{"truncated": true}'
        return result


SCHEMA_VERSION = "1.0.0"
