#!/usr/bin/env python3
"""SessionEnd hook: emit a session summary into the audit chain.

Claude Code fires ``SessionEnd`` once per session terminus (clean exit
or context-window flush). The Stop hook already handles per-turn
checkpointing; SessionEnd is a separate, lower-frequency primitive
that gives us a single anchor event per session for queryability —
useful for the spec-120 SQLite projection and OTLP export.

Reads ``runtime/checkpoint.json`` (best effort) and emits a
``framework_operation`` with ``operation=session_end_summary``
containing the session id, recent edit count, and the convergence
state captured by Stop. Fail-open; any error is swallowed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context

_COMPONENT = "hook.runtime-session-end"
_CHECKPOINT_REL = Path(".ai-engineering") / "state" / "runtime" / "checkpoint.json"


def _read_checkpoint(project_root: Path) -> dict:
    path = project_root / _CHECKPOINT_REL
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "SessionEnd":
        passthrough_stdin(ctx.data)
        return

    checkpoint = _read_checkpoint(ctx.project_root)
    metadata: dict[str, object] = {
        "session_id": ctx.session_id,
    }
    if isinstance(checkpoint.get("recent_edits"), list):
        metadata["recent_edit_count"] = len(checkpoint["recent_edits"])
    if isinstance(checkpoint.get("recent_tool_calls"), list):
        metadata["recent_tool_call_count"] = len(checkpoint["recent_tool_calls"])
    if isinstance(checkpoint.get("convergence"), dict):
        conv = checkpoint["convergence"]
        if isinstance(conv.get("converged"), bool):
            metadata["converged"] = conv["converged"]
    reason = ctx.data.get("reason")
    if isinstance(reason, str) and reason.strip():
        metadata["end_reason"] = reason.strip()[:64]

    try:
        from _lib.observability import emit_framework_operation

        emit_framework_operation(
            ctx.project_root,
            operation="session_end_summary",
            component=_COMPONENT,
            source="hook",
            correlation_id=get_correlation_id(),
            metadata=metadata,
        )
    except Exception:
        pass

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="session-end",
        script_path=__file__,
    )
