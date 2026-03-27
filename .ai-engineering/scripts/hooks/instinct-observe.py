#!/usr/bin/env python3
"""Pre/PostToolUse hook: append sanitized observations for instinct learning.

Fail-open: exit 0 always and preserve hook chaining for Claude Code.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin, read_stdin
from _lib.instincts import append_instinct_observation

_SUPPORTED_EVENTS = {"PreToolUse", "PostToolUse"}


def main() -> None:
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT_NAME", "")
    data = read_stdin()

    if hook_event not in _SUPPORTED_EVENTS:
        passthrough_stdin(data)
        return

    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd()))
    append_instinct_observation(
        project_root,
        engine=os.environ.get("AIENG_HOOK_ENGINE", "claude_code"),
        hook_event=hook_event,
        data=data,
        session_id=os.environ.get("CLAUDE_SESSION_ID") or data.get("session_id"),
    )
    passthrough_stdin(data)


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
