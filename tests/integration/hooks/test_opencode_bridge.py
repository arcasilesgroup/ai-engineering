"""Smoke tests for OpenCode hook bridge (spec-133 D-133-06)."""

from __future__ import annotations

from pathlib import Path


def test_opencode_bridge_typescript_file_exists() -> None:
    p = Path(".ai-engineering/scripts/hooks/opencode-hook-bridge.ts")
    assert p.is_file(), f"missing: {p}"


def test_opencode_bridge_declares_event_map() -> None:
    p = Path(".ai-engineering/scripts/hooks/opencode-hook-bridge.ts")
    text = p.read_text()
    # Spec D-133-13 / R-133-03: 11 canonical events mapped, but OpenCode
    # uses subset (no PostToolUseFailure, no SubagentStop differentiation).
    # Assert key translations exist.
    assert "tool.execute.before" in text
    assert "PreToolUse" in text
    assert "tool.execute.after" in text
    assert "PostToolUse" in text
    assert "session.created" in text
    assert "SessionStart" in text
    assert '"engine": "opencode"' in text or 'engine: "opencode"' in text


def test_opencode_bridge_exports_translate_function() -> None:
    p = Path(".ai-engineering/scripts/hooks/opencode-hook-bridge.ts")
    text = p.read_text()
    assert "export function translate" in text


def test_opencode_bridge_exports_dispatch_function() -> None:
    p = Path(".ai-engineering/scripts/hooks/opencode-hook-bridge.ts")
    text = p.read_text()
    assert "export async function dispatch" in text
