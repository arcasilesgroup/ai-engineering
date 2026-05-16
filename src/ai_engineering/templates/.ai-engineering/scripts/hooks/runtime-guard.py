#!/usr/bin/env python3
"""PostToolUse runtime guard: tool-call offload + loop detection (spec-116 G-2).

Two harness primitives in one hook to avoid stacking another fork()
on every tool invocation:

* **Offload**: large stdout/stderr payloads (above
  ``AIENG_TOOL_OFFLOAD_BYTES``, default 4 KB) are written to
  ``RUNTIME_DIR(project_root) / "tool-outputs"`` (canonical
  ``.ai-engineering/runtime/tool-outputs/``) and a head+tail+pointer
  hint is surfaced via ``hookSpecificOutput.additionalContext`` so the
  model can read the full file on demand instead of bloating context.

* **Loop detection**: a sliding window of recent tool signatures is
  persisted in ``runtime/tool-history.ndjson``. When the same signature
  (or repeated failures) crosses ``LOOP_REPEAT_THRESHOLD`` inside the
  window, the hook emits a ``framework_error`` event and injects a hint
  asking the model to change approach.

Fail-open: never blocks the IDE. Exits 0 even on error.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import (
    emit_event,
    get_correlation_id,
    get_session_id,
    run_hook_safe,
)
from _lib.hook_context import get_hook_context
from _lib.runtime_state import (
    LOOP_WINDOW,
    TOOL_OFFLOAD_SKIP,
    TOOL_RESPONSE_FLATTEN_CAP,
    ToolHistoryEntry,
    append_tool_history,
    derive_outcome,
    detect_repetition,
    extract_error_summary,
    iso_now,
    offload_large_text,
    recent_tool_history,
    tool_signature,
)

# File-path-bearing tools whose tool_input.file_path we persist into the
# tool-history record so runtime-stop can recover edited paths from a single
# source of truth (rather than scanning framework-events for an event auto-format
# never emits).
_FILE_PATH_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})


def _flatten_tool_response(response: object) -> str:
    """Reduce arbitrary tool_response payloads to a single string.

    Truncates at TOOL_RESPONSE_FLATTEN_CAP (≥ TOOL_OFFLOAD_BYTES) so that any
    payload large enough to be flattened is also large enough to be offloaded
    cleanly downstream. Earlier versions hard-coded 65536 in three places,
    desynchronising from the offload threshold when AIENG_TOOL_OFFLOAD_BYTES
    was raised.
    """
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        chunks: list[str] = []
        for item in response:
            chunks.append(_flatten_tool_response(item))
        return "\n".join(c for c in chunks if c)
    if isinstance(response, dict):
        for key in ("text", "content", "stdout", "result", "output"):
            value = response.get(key)
            if isinstance(value, str) and value:
                return value
        try:
            return json.dumps(response, default=str)[:TOOL_RESPONSE_FLATTEN_CAP]
        except (TypeError, ValueError):
            return repr(response)[:TOOL_RESPONSE_FLATTEN_CAP]
    return str(response)[:TOOL_RESPONSE_FLATTEN_CAP]


def _extract_file_path(tool: str, tool_input: dict) -> str | None:
    """Return file_path from a file-touching tool, else None."""
    if tool not in _FILE_PATH_TOOLS:
        return None
    candidate = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(candidate, str) and candidate:
        return candidate
    return None


def _emit_loop_warning(
    *,
    project_root: Path,
    session_id: str | None,
    correlation_id: str,
    reason: str,
    window_size: int,
) -> None:
    event: dict = {
        "kind": "framework_error",
        "engine": "claude_code",
        "timestamp": iso_now(),
        "component": "hook.runtime-guard",
        "outcome": "failure",
        "correlationId": correlation_id,
        "schemaVersion": "1.0",
        "project": project_root.name,
        "source": "hook",
        "detail": {
            "error_code": "loop_detected",
            "summary": reason[:200],
            "window_size": window_size,
            "hook_kind": "post-tool-use",
        },
    }
    if session_id:
        event["sessionId"] = session_id
    emit_event(project_root, event)


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "PostToolUse":
        passthrough_stdin(ctx.data)
        return

    tool = str(ctx.data.get("tool_name") or "").strip()
    if not tool:
        passthrough_stdin(ctx.data)
        return

    correlation_id = get_correlation_id()
    session_id = ctx.session_id or get_session_id()

    # --- Loop detection -------------------------------------------------
    tool_input = dict(ctx.data.get("tool_input") or {})
    sig = tool_signature(tool, tool_input)
    outcome = derive_outcome(ctx.data)
    error_summary = extract_error_summary(ctx.data)
    file_path = _extract_file_path(tool, tool_input)
    append_tool_history(
        ctx.project_root,
        ToolHistoryEntry(
            timestamp=iso_now(),
            session_id=session_id,
            tool=tool,
            signature=sig,
            outcome=outcome,
            error_summary=error_summary,
            file_path=file_path,
        ),
    )
    history = recent_tool_history(ctx.project_root, session_id=session_id, limit=LOOP_WINDOW)
    looped, loop_reason = detect_repetition(history)
    hints: list[str] = []
    if looped and loop_reason:
        _emit_loop_warning(
            project_root=ctx.project_root,
            session_id=session_id,
            correlation_id=correlation_id,
            reason=loop_reason,
            window_size=len(history),
        )
        hints.append(
            "[runtime-guard] Loop detected: "
            f"{loop_reason}. Change tool, inputs, or strategy before retrying."
        )

    # --- Tool-call offload ---------------------------------------------
    # Skip tools whose responses the model already has in full (Read, Glob, Grep,
    # TodoWrite). For those a "go fetch from a different path" hint inflates
    # context without saving bytes.
    if tool not in TOOL_OFFLOAD_SKIP:
        raw_text = _flatten_tool_response(ctx.data.get("tool_response"))
        if raw_text:
            summary = offload_large_text(
                ctx.project_root,
                correlation_id=correlation_id,
                tool_name=tool,
                text=raw_text,
            )
            if summary["offloaded"]:
                hints.append(
                    f"[runtime-guard] Tool output offloaded ({summary['totalBytes']} bytes). "
                    f"Head + tail kept in context; full payload at "
                    f"{summary['path']}. Read it on demand instead of pasting."
                )

    # --- PRISM risk warn-level surface (spec-120 #17) ------------------
    # When accumulated session risk crosses the warn threshold, append a
    # one-line hint so the model knows recent prompt-injection-guard
    # findings have stacked up. Block / force_stop are handled by
    # prompt-injection-guard.py itself; runtime-guard is observational.
    risk_disabled = (os.environ.get("AIENG_RISK_ACCUMULATOR_DISABLED") or "").strip() == "1"
    if not risk_disabled:
        try:
            from _lib import risk_accumulator  # type: ignore[import-not-found]

            state = risk_accumulator.get(ctx.project_root, session_id=session_id or "unknown")
            if risk_accumulator.threshold_action(state.score) == "warn":
                hints.append(
                    f"[runtime-guard] ⚠️ Session risk score {state.score:.1f} "
                    "(warn threshold). Review recent prompt-injection-guard findings."
                )
        except Exception:
            pass  # fail-open; never break runtime-guard

    # --- Surface hints to the model ------------------------------------
    if hints:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "\n".join(hints),
                    }
                },
                separators=(",", ":"),
            )
        )
        sys.stdout.flush()
    else:
        passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main, component="hook.runtime-guard", hook_kind="post-tool-use", script_path=__file__
    )
