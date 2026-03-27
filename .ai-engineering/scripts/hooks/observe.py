#!/usr/bin/env python3
"""Pre/PostToolUse hook: emit canonical agent dispatch events.

Fail-open: exit 0 always -- never blocks IDE.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import get_project_root, is_debug_mode, passthrough_stdin, read_stdin
from _lib.observability import (
    emit_agent_dispatched,
    emit_framework_error,
    emit_ide_hook_outcome,
)

_ALLOWED_ENTRYPOINTS = {"cli", "sdk-ts"}


def _handle_agent_dispatch(data: dict, project_root: Path, session_id: str) -> None:
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
        engine="claude_code",
        agent_name=agent_name,
        component="hook.observe",
        source="hook",
        session_id=session_id,
        trace_id=os.environ.get("CLAUDE_TRACE_ID"),
        metadata={"description": description},
    )


def main() -> None:
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT_NAME", "")
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")

    if entrypoint and entrypoint not in _ALLOWED_ENTRYPOINTS:
        return

    data = read_stdin()

    if data.get("agent_id"):
        passthrough_stdin(data)
        return

    tool_name = data.get("tool_name", "")
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    project_root = get_project_root()
    if hook_event == "PostToolUse" and tool_name == "Agent":
        emit_ide_hook_outcome(
            project_root,
            engine="claude_code",
            hook_kind="post-tool-use",
            component="hook.observe",
            outcome="success",
            source="hook",
            session_id=session_id,
            trace_id=os.environ.get("CLAUDE_TRACE_ID"),
        )
        _handle_agent_dispatch(data, project_root, session_id)

    if is_debug_mode():
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            phase = "pre" if hook_event == "PreToolUse" else "post"
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] observe: {phase} tool={tool_name}\n")
        except Exception:
            pass

    passthrough_stdin(data)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            project_root = get_project_root()
            emit_ide_hook_outcome(
                project_root,
                engine="claude_code",
                hook_kind="post-tool-use",
                component="hook.observe",
                outcome="failure",
                source="hook",
                session_id=os.environ.get("CLAUDE_SESSION_ID"),
                trace_id=os.environ.get("CLAUDE_TRACE_ID"),
            )
            emit_framework_error(
                project_root,
                engine="claude_code",
                component="hook.observe",
                error_code="hook_execution_failed",
                summary=str(exc),
                source="hook",
                session_id=os.environ.get("CLAUDE_SESSION_ID"),
                trace_id=os.environ.get("CLAUDE_TRACE_ID"),
            )
        except Exception:
            pass
    sys.exit(0)
