"""MCP removal executor (spec-195 T-3).

Preview → confirm → apply → verify cycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .inventory import McpEntry, McpInventory


@dataclass(frozen=True)
class RemovalPlan:
    """Plan for MCP removal."""

    host: str
    entries_to_remove: list[McpEntry]
    entries_to_retain: list[McpEntry]
    preview_json: str
    confirmed: bool = False
    applied: bool = False
    verified: bool = False


@dataclass(frozen=True)
class RemovalResult:
    """Result of MCP removal."""

    host: str
    removed: list[str]
    retained: list[str]
    errors: list[str]
    success: bool


def create_removal_plan(inventory: McpInventory) -> RemovalPlan:
    """Create a removal plan from inventory."""
    entries_to_remove = [e for e in inventory.entries if e.classification == "remove"]
    entries_to_retain = [e for e in inventory.entries if e.classification != "remove"]

    preview = {
        "host": inventory.host,
        "total": inventory.total,
        "to_remove": len(entries_to_remove),
        "to_retain": len(entries_to_retain),
        "remove": [{"name": e.name, "evidence": e.evidence} for e in entries_to_remove],
        "retain": [{"name": e.name, "classification": e.classification} for e in entries_to_retain],
    }

    return RemovalPlan(
        host=inventory.host,
        entries_to_remove=entries_to_remove,
        entries_to_retain=entries_to_retain,
        preview_json=json.dumps(preview, indent=2, sort_keys=True),
    )


def apply_removal(plan: RemovalPlan, config_dir: Path) -> RemovalResult:
    """Apply MCP removal (after confirmation).

    This actually modifies config files. Only call after explicit confirmation.
    """
    if not plan.confirmed:
        return RemovalResult(
            host=plan.host,
            removed=[],
            retained=[],
            errors=["Plan not confirmed"],
            success=False,
        )

    removed: list[str] = []
    retained: list[str] = []
    errors: list[str] = []

    # Group entries by source file
    by_source: dict[str, list[McpEntry]] = {}
    for entry in plan.entries_to_remove:
        by_source.setdefault(entry.source_file, []).append(entry)

    for source_file, entries in by_source.items():
        path = Path(source_file)
        if not path.exists():
            errors.append(f"Source file not found: {source_file}")
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"Failed to parse {source_file}: {e}")
            continue

        servers = data.get("mcpServers", data.get("servers", {}))
        for entry in entries:
            if entry.name in servers:
                del servers[entry.name]
                removed.append(entry.name)

        # Write back
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    for entry in plan.entries_to_retain:
        retained.append(entry.name)

    return RemovalResult(
        host=plan.host,
        removed=removed,
        retained=retained,
        errors=errors,
        success=len(errors) == 0,
    )


def verify_removal(config_dir: Path, host: str) -> list[str]:
    """Verify no third-party MCP residue remains."""
    residue: list[str] = []

    # Check Claude configs
    claude_configs = [
        config_dir / ".claude" / "mcp.json",
        config_dir / ".claude" / "mcp_servers.json",
    ]
    for config_file in claude_configs:
        if not config_file.exists():
            continue
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", data.get("servers", {}))
            if servers:
                residue.extend(f"claude:{name}" for name in servers.keys())
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Check Codex configs
    codex_config = config_dir / ".codex" / "mcp.json"
    if codex_config.exists():
        try:
            data = json.loads(codex_config.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", data.get("servers", {}))
            if servers:
                # Only flag non-vendor entries
                from .inventory import _RETAIN_VENDOR

                for name in servers.keys():
                    if name not in _RETAIN_VENDOR:
                        residue.append(f"codex:{name}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    return residue
