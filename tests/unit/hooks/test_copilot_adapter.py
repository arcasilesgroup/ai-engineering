"""Tests for `copilot-adapter.py` -- payload key remapping for bash-Copilot.

The headline regression: `toolResult` MUST be renamed to `tool_response`,
not `tool_result`. runtime-guard reads `tool_response`, so any other key
silently makes tool-output offload broken on bash hosts.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ADAPTER_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "copilot-adapter.py"


def _load():
    spec = importlib.util.spec_from_file_location("aieng_copilot_adapter", ADAPTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_renames_tool_result_to_tool_response() -> None:
    adapter = _load()
    payload = {
        "toolName": "shell",
        "toolArgs": {"command": "ls"},
        "toolResult": {"stdout": "ok"},
    }
    out = adapter._normalize(payload)
    assert "tool_response" in out
    assert "tool_result" not in out
    assert out["tool_name"] == "shell"
    assert out["tool_input"] == {"command": "ls"}
    assert out["tool_response"] == {"stdout": "ok"}


def test_normalize_handles_alternative_camelcase_key() -> None:
    """Some Copilot builds use `toolResponse` (camelCase) directly."""
    adapter = _load()
    out = adapter._normalize({"toolResponse": {"stdout": "x"}})
    assert out["tool_response"] == {"stdout": "x"}


def test_normalize_passes_through_other_keys_via_snake_case() -> None:
    adapter = _load()
    out = adapter._normalize({"sessionId": "s1", "correlationId": "c1"})
    assert out["session_id"] == "s1"
    assert out["correlation_id"] == "c1"
