#!/usr/bin/env python3
"""Pre/PostToolUse hook: append sanitized observations for instinct learning.

Fail-open: exit 0 always and preserve hook chaining for all IDEs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.instincts import append_instinct_observation

_SUPPORTED_EVENTS = {"PreToolUse", "PostToolUse"}


def main() -> None:
    ctx = get_hook_context()

    if ctx.event_name not in _SUPPORTED_EVENTS:
        passthrough_stdin(ctx.data)
        return

    append_instinct_observation(
        ctx.project_root,
        engine=ctx.engine,
        hook_event=ctx.event_name,
        data=ctx.data,
        session_id=ctx.session_id,
    )
    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(main, component="hook.instinct-observe", hook_kind="post-tool-use")
