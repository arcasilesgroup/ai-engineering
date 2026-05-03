#!/usr/bin/env python3
"""spec-118 one-shot helper: wire memory-* hooks into .claude/settings.json.

Idempotent. Safe to re-run. Adds:
    Stop[0].hooks         <- memory-stop.py (timeout 10)
    SessionStart[].hooks  <- memory-session-start.py (timeout 8)
"""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path(".claude/settings.json")
MEMORY_STOP_CMD = 'python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/memory-stop.py"'
MEMORY_SESSION_START_CMD = (
    'python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/memory-session-start.py"'
)


def main() -> int:
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    hooks = data.setdefault("hooks", {})
    changed = False

    # Stop chain
    stop_block = hooks.setdefault("Stop", [])
    existing_stop = [h.get("command", "") for blk in stop_block for h in blk.get("hooks", [])]
    if not any("memory-stop.py" in c for c in existing_stop):
        if stop_block and stop_block[0].get("matcher") == "":
            stop_block[0]["hooks"].append(
                {"type": "command", "command": MEMORY_STOP_CMD, "timeout": 10}
            )
        else:
            stop_block.append(
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": MEMORY_STOP_CMD,
                            "timeout": 10,
                        }
                    ],
                }
            )
        changed = True

    # SessionStart
    if "SessionStart" not in hooks:
        hooks["SessionStart"] = [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": MEMORY_SESSION_START_CMD,
                        "timeout": 8,
                    }
                ],
            }
        ]
        changed = True
    else:
        ss_existing = [
            h.get("command", "") for blk in hooks["SessionStart"] for h in blk.get("hooks", [])
        ]
        if not any("memory-session-start.py" in c for c in ss_existing):
            hooks["SessionStart"].append(
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": MEMORY_SESSION_START_CMD,
                            "timeout": 8,
                        }
                    ],
                }
            )
            changed = True

    if changed:
        SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print("wired memory hooks into .claude/settings.json")
    else:
        print("settings.json already wired; no change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
