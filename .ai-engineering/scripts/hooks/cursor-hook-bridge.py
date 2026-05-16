"""Cursor hook bridge — spec-133 D-133-06 + R-133-04.

Cursor 1.7+ ships native hooks (beta, Sept 2025). Hooks fire with
stdio JSON contract identical in shape to Claude Code's. Event names
differ: ``preToolUse`` (camelCase) vs Claude's ``PreToolUse`` (PascalCase).
Capabilities (deny, modify, observe) are isomorphic.

This adapter:
  1. Reads the Cursor hook payload from stdin.
  2. Translates the camelCase event name to ai-engineering's canonical
     PascalCase via ``_EVENT_MAP``.
  3. Re-emits the payload to the canonical hook entrypoint at
     ``.ai-engineering/scripts/hooks/<canonical_event>.py``.
  4. Emits a ``framework-events.ndjson`` envelope with
     ``{"engine": "cursor"}`` for audit trace continuity.

Reference: https://cursor.com/docs/hooks
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Final

_EVENT_MAP: Final[dict[str, str]] = {
    # Cursor camelCase -> ai-engineering canonical PascalCase
    "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse",
    "postToolUseFailure": "PostToolUseFailure",
    "sessionStart": "SessionStart",
    "sessionEnd": "SessionEnd",
    "subagentStart": "SubagentStop",  # Cursor 'start' maps to canonical 'Stop' lifecycle
    "subagentStop": "SubagentStop",
    "beforeShellExecution": "PreToolUse",
    "afterShellExecution": "PostToolUse",
    "preCompact": "PreCompact",
    "stop": "Stop",
    "beforeSubmitPrompt": "UserPromptSubmit",
}


def main() -> int:
    """Read stdin payload, translate event, dispatch canonical hook."""
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"cursor-hook-bridge: invalid stdin JSON: {exc}\n")
        return 1

    cursor_event = payload.get("event") or payload.get("hookEventName")
    if not cursor_event:
        sys.stderr.write("cursor-hook-bridge: missing 'event' in payload\n")
        return 1

    canonical = _EVENT_MAP.get(cursor_event)
    if not canonical:
        # Unknown event from Cursor: pass through observe-only.
        return 0

    hooks_root = Path(__file__).resolve().parent
    target_script = hooks_root / f"{canonical.lower()}.py"
    if not target_script.is_file():
        sys.stderr.write(f"cursor-hook-bridge: no canonical handler at {target_script}\n")
        return 0

    # Augment payload with bridge metadata.
    payload["__bridge"] = {
        "engine": "cursor",
        "canonical_event": canonical,
        "source_event": cursor_event,
    }

    result = subprocess.run(
        ["python", str(target_script)],
        input=json.dumps(payload),
        text=True,
        check=False,
        env={**os.environ, "AIENG_HOOK_ENGINE": "cursor"},
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
