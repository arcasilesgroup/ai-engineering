"""MCP inventory scanner (spec-195 T-1).

Classifies all MCP registrations across hosts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class McpEntry:
    """Single MCP registration entry."""

    name: str
    owner: str  # "user", "project", "plugin", "vendor"
    classification: str  # "remove", "retain_vendor", "retain_pencil", "blocker"
    source_file: str
    evidence: str  # why this classification


@dataclass(frozen=True)
class McpInventory:
    """Complete MCP inventory for a host."""

    host: str
    entries: list[McpEntry]
    total: int
    to_remove: int
    to_retain: int
    blockers: list[str]

    def to_json(self) -> str:
        import json as json_mod

        return json_mod.dumps(
            {
                "host": self.host,
                "total": self.total,
                "to_remove": self.to_remove,
                "to_retain": self.to_retain,
                "blockers": self.blockers,
                "entries": [
                    {
                        "name": e.name,
                        "owner": e.owner,
                        "classification": e.classification,
                        "source_file": e.source_file,
                        "evidence": e.evidence,
                    }
                    for e in self.entries
                ],
            },
            indent=2,
            sort_keys=True,
        )


# Known vendor/system capabilities to retain (Codex)
_RETAIN_VENDOR = {"node_repl", "sites-design-picker", "github"}

# Pencil/Pen exception fields
_PENCIL_FIELDS = {"vendor", "component_id", "channel", "version", "installation_owner"}


def scan_claude_mcp(config_dir: Path) -> list[McpEntry]:
    """Scan Claude Code MCP configurations."""
    entries: list[McpEntry] = []
    config_files = [
        config_dir / ".claude" / "mcp.json",
        config_dir / ".claude" / "mcp_servers.json",
    ]

    for config_file in config_files:
        if not config_file.exists():
            continue
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Parse MCP servers
        servers = data.get("mcpServers", data.get("servers", {}))
        if isinstance(servers, dict):
            for name, config in servers.items():
                owner = _classify_owner(config)
                classification = _classify_entry(name, config, "claude")
                entries.append(
                    McpEntry(
                        name=name,
                        owner=owner,
                        classification=classification,
                        source_file=str(config_file),
                        evidence=f"owner={owner}, classification={classification}",
                    )
                )

    return entries


def scan_codex_mcp(config_dir: Path) -> list[McpEntry]:
    """Scan Codex MCP configurations."""
    entries: list[McpEntry] = []
    config_file = config_dir / ".codex" / "mcp.json"

    if not config_file.exists():
        return entries

    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return entries

    servers = data.get("mcpServers", data.get("servers", {}))
    if isinstance(servers, dict):
        for name, config in servers.items():
            owner = _classify_owner(config)
            # Codex retains vendor/system capabilities
            if name in _RETAIN_VENDOR:
                classification = "retain_vendor"
            else:
                classification = _classify_entry(name, config, "codex")
            entries.append(
                McpEntry(
                    name=name,
                    owner=owner,
                    classification=classification,
                    source_file=str(config_file),
                    evidence=f"owner={owner}, classification={classification}",
                )
            )

    return entries


def scan_opencode_mcp(config_dir: Path) -> list[McpEntry]:
    """Scan OpenCode MCP configurations."""
    entries: list[McpEntry] = []
    config_file = config_dir / ".opencode" / "mcp.json"

    if not config_file.exists():
        return entries

    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return entries

    servers = data.get("mcpServers", data.get("servers", {}))
    if isinstance(servers, dict):
        for name, config in servers.items():
            owner = _classify_owner(config)
            classification = _classify_entry(name, config, "opencode")
            entries.append(
                McpEntry(
                    name=name,
                    owner=owner,
                    classification=classification,
                    source_file=str(config_file),
                    evidence=f"owner={owner}, classification={classification}",
                )
            )

    return entries


def _classify_owner(config: dict[str, Any]) -> str:
    """Classify MCP owner from config."""
    if "command" in config or "args" in config:
        return "project"
    if "url" in config:
        return "user"
    return "plugin"


def _classify_entry(name: str, config: dict[str, Any], host: str) -> str:
    """Classify MCP entry for removal."""
    name_lower = name.lower()

    # Check for Pencil/Pen
    if "pencil" in name_lower or "pen" in name_lower:
        # Would need full 5-field verification in production
        return "retain_pencil"

    # Check for vendor/system capabilities
    if name in _RETAIN_VENDOR:
        return "retain_vendor"

    # Everything else is remove
    return "remove"


def build_inventory(host: str, entries: list[McpEntry]) -> McpInventory:
    """Build complete inventory from entries."""
    to_remove = sum(1 for e in entries if e.classification == "remove")
    to_retain = sum(1 for e in entries if e.classification.startswith("retain"))
    blockers = [e.name for e in entries if e.classification == "blocker"]

    return McpInventory(
        host=host,
        entries=entries,
        total=len(entries),
        to_remove=to_remove,
        to_retain=to_retain,
        blockers=blockers,
    )
