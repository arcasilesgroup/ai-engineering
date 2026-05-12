"""Smoke tests for Cursor hook bridge (spec-133 D-133-06).

Cursor's stdio JSON contract is isomorphic to Claude Code's. The
bridge re-emits the payload into the canonical Python hook entrypoint
under .ai-engineering/scripts/hooks/<event>.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_BRIDGE = Path(".ai-engineering/scripts/hooks/cursor-hook-bridge.py")


def test_cursor_bridge_script_exists() -> None:
    assert _BRIDGE.is_file(), f"missing: {_BRIDGE}"


def test_cursor_bridge_script_is_executable() -> None:
    assert _BRIDGE.stat().st_mode & 0o100, "bridge not executable"


def test_cursor_bridge_event_translation_table_complete() -> None:
    text = _BRIDGE.read_text()
    # Cursor camelCase -> ai-engineering canonical PascalCase. Spec
    # D-133-13 says 11 canonical events; the translation table covers
    # the high-frequency cursor events that map directly.
    for cursor_event in (
        "preToolUse",
        "postToolUse",
        "sessionStart",
        "sessionEnd",
        "preCompact",
        "stop",
        "beforeSubmitPrompt",
    ):
        assert cursor_event in text, f"missing translation for {cursor_event}"


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
