"""Smoke tests for OpenCode hook bridge (spec-133 D-133-06)."""

from __future__ import annotations

import re
from pathlib import Path

_BRIDGE = Path(".ai-engineering/scripts/hooks/opencode-hook-bridge.ts")

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"^\s*//.*$", re.MULTILINE)


def _code_only(path: Path) -> str:
    """Bridge source with comments stripped.

    The module docstring legitimately quotes the retired `dispatch()` stub and
    the non-existent `permission.asked` event as provenance, so an absence
    assertion has to look at executable code rather than raw bytes.
    """
    text = _BLOCK_COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
    return _LINE_COMMENT_RE.sub("", text)


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


def test_opencode_bridge_default_exports_a_plugin() -> None:
    """spec-201 sub-005: the `dispatch()` stub is replaced by a real Plugin.

    `dispatch` was `return 0;` — it could not deny anything, and nothing
    imported it. The blocking contract is now the default export that
    OpenCode's plugin loader calls.
    """
    code = _code_only(_BRIDGE)
    assert "export default plugin" in code
    assert "export async function dispatch" not in code
    for hook in ("tool.execute.before", "permission.ask", "tool.execute.after"):
        assert f'"{hook}"' in code


def test_opencode_bridge_drops_the_nonexistent_permission_event() -> None:
    """`permission.asked` is not a plugin hook in the installed 1.18.5 SDK."""
    assert '"permission.asked"' not in _code_only(_BRIDGE)
