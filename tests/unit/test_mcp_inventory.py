"""Tests for MCP inventory scanner (spec-195 T-1)."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.mcp.inventory import (
    McpEntry,
    _classify_entry,
    build_inventory,
    scan_claude_mcp,
)


class TestMcpEntry:
    """McpEntry dataclass tests."""

    def test_create_entry(self):
        entry = McpEntry(
            name="test-server",
            owner="project",
            classification="remove",
            source_file="/path/to/mcp.json",
            evidence="test evidence",
        )
        assert entry.name == "test-server"
        assert entry.classification == "remove"


class TestClassification:
    """Classification tests."""

    def test_remove_by_default(self):
        assert _classify_entry("unknown-server", {}, "claude") == "remove"

    def test_retain_pencil(self):
        assert _classify_entry("pencil-mcp", {}, "claude") == "retain_pencil"

    def test_retain_vendor(self):
        assert _classify_entry("node_repl", {}, "codex") == "retain_vendor"


class TestScanClaude:
    """Claude MCP scanning tests."""

    def test_scan_empty_dir(self, tmp_path: Path):
        entries = scan_claude_mcp(tmp_path)
        assert entries == []

    def test_scan_with_servers(self, tmp_path: Path):
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        config_file = config_dir / "mcp.json"
        config_file.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "test-server": {"command": "test"},
                        "pencil-mcp": {"command": "pencil"},
                    }
                }
            )
        )

        entries = scan_claude_mcp(tmp_path)
        assert len(entries) == 2
        names = {e.name for e in entries}
        assert "test-server" in names
        assert "pencil-mcp" in names


class TestBuildInventory:
    """Inventory builder tests."""

    def test_build_inventory(self):
        entries = [
            McpEntry("a", "project", "remove", "f", "e"),
            McpEntry("b", "project", "retain_vendor", "f", "e"),
        ]
        inventory = build_inventory("test", entries)
        assert inventory.total == 2
        assert inventory.to_remove == 1
        assert inventory.to_retain == 1

    def test_inventory_json(self):
        entries = [McpEntry("a", "project", "remove", "f", "e")]
        inventory = build_inventory("test", entries)
        json_str = inventory.to_json()
        parsed = json.loads(json_str)
        assert parsed["host"] == "test"
        assert parsed["to_remove"] == 1
