#!/usr/bin/env python3
"""Pre/PostToolUse hook: emit canonical agent dispatch events.

Fail-open: exit 0 always -- never blocks IDE.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import is_debug_mode, passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.observability import (
    emit_agent_dispatched,
    emit_ide_hook_outcome,
)

_ALLOWED_ENTRYPOINTS = {"cli", "sdk-ts"}


def _handle_agent_dispatch(data: dict, project_root: Path, engine: str, session_id: str) -> None:
    """Emit ``agent_dispatched`` to the canonical framework stream."""
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    subagent_type = tool_input.get("subagent_type", tool_input.get("description", ""))
    if not subagent_type:
        return

    normalized = subagent_type.lower()
    if normalized.startswith("ai-"):
        normalized = normalized[3:]
    agent_name = f"ai-{normalized}"

    description = tool_input.get("description", "")
    if isinstance(description, str) and len(description) > 200:
        description = description[:200] + "..."

    emit_agent_dispatched(
        project_root,
        engine=engine,
        agent_name=agent_name,
        component="hook.observe",
        source="hook",
        session_id=session_id,
        trace_id=os.environ.get("CLAUDE_TRACE_ID"),
        metadata={"description": description},
    )


def main() -> None:
    ctx = get_hook_context()

    # Entrypoint check only applies to claude_code engine
    if ctx.engine == "claude_code":
        entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
        if entrypoint and entrypoint not in _ALLOWED_ENTRYPOINTS:
            return

    if ctx.data.get("agent_id"):
        passthrough_stdin(ctx.data)
        return

    tool_name = ctx.data.get("tool_name", "")
    session_id = ctx.session_id or "unknown"

    if ctx.event_name == "PostToolUse" and tool_name == "Agent":
        emit_ide_hook_outcome(
            ctx.project_root,
            engine=ctx.engine,
            hook_kind="post-tool-use",
            component="hook.observe",
            outcome="success",
            source="hook",
            session_id=session_id,
            trace_id=os.environ.get("CLAUDE_TRACE_ID"),
        )
        _handle_agent_dispatch(ctx.data, ctx.project_root, ctx.engine, session_id)

    if is_debug_mode():
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            phase = "pre" if ctx.event_name == "PreToolUse" else "post"
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] observe: {phase} tool={tool_name}\n")
        except Exception:
            pass

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(main, component="hook.observe", hook_kind="post-tool-use")
