"""Smoke tests for Cursor hook bridge (spec-133 D-133-06).

Cursor's stdio JSON contract is isomorphic to Claude Code's. The
bridge re-emits the payload into the canonical Python hook entrypoint
under .ai-engineering/scripts/hooks/<event>.py.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_BRIDGE = Path(".ai-engineering/scripts/hooks/cursor-hook-bridge.py")


def _load_bridge() -> ModuleType:
    """Import the hyphenated bridge module by path (not a valid identifier)."""
    spec = importlib.util.spec_from_file_location("cursor_hook_bridge", _BRIDGE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cursor_bridge_script_exists() -> None:
    assert _BRIDGE.is_file(), f"missing: {_BRIDGE}"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows filesystems do not honour Unix execute bits",
)
def test_cursor_bridge_script_is_executable() -> None:
    assert _BRIDGE.stat().st_mode & 0o100, "bridge not executable"


def test_cursor_bridge_guard_map_names_only_real_scripts() -> None:
    """spec-201 D-201-17: every mapped guard must exist on disk.

    Supersedes the old string-presence check. The original defect was a
    dispatch that resolved `pretooluse.py` / `posttooluse.py` / `stop.py` —
    filenames that have never existed — so every Cursor event silently
    returned 0. Presence of a camelCase key in the source proved nothing.
    """
    bridge = _load_bridge()

    assert bridge.missing_guard_scripts() == []
    for cursor_event in (
        "beforeShellExecution",
        "beforeReadFile",
        "preToolUse",
        "postToolUse",
        "sessionStart",
        "sessionEnd",
        "preCompact",
        "stop",
        "beforeSubmitPrompt",
    ):
        assert cursor_event in bridge._GUARD_MAP, f"missing mapping for {cursor_event}"


def test_cursor_bridge_drops_the_subagent_start_mismap() -> None:
    """`subagentStart` is a start event; mapping it to Stop fired a rollup early."""
    bridge = _load_bridge()

    assert "subagentStart" not in bridge._GUARD_MAP
    assert bridge._GUARD_MAP["subagentStop"] == ("runtime-subagent-stop.py",)


def test_cursor_bridge_pins_an_admitted_engine_literal() -> None:
    """`cursor` is not in `_ALLOWED_ENGINES`; the OpenAI-shaped label is."""
    from ai_engineering.state.observability import ALLOWED_ENGINES

    bridge = _load_bridge()

    assert bridge._HOOK_ENGINE in ALLOWED_ENGINES
    assert bridge._HOOK_ENGINE == "openai_compatible"


def test_cursor_bridge_rejects_invalid_json() -> None:
    """Bridge must exit non-zero on malformed stdin (R-133-04 mitigation)."""
    result = subprocess.run(
        [sys.executable, str(_BRIDGE)],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


def test_cursor_bridge_observes_unknown_event() -> None:
    """Unknown Cursor event passes through observe-only (exit 0)."""
    payload = {"event": "neverHeardOf", "data": {}}
    result = subprocess.run(
        [sys.executable, str(_BRIDGE)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
