#!/usr/bin/env python3
"""Notification hook: capture LLM-driven user notifications into the audit chain.

Claude Code emits ``Notification`` when the model surfaces a banner,
permission request, or out-of-band signal to the user. Without a hook,
those signals are invisible to the spec-120 audit chain — we lose
attribution of why a session paused or what the model asked for.

Contract: fail-open. Any malformed payload, import failure, or disk
error must not block the notification reaching the user.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context

_COMPONENT = "hook.runtime-notification"


def _coerce_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "Notification":
        passthrough_stdin(ctx.data)
        return

    message = _coerce_str(ctx.data.get("message")) or ""
    title = _coerce_str(ctx.data.get("title"))
    notification_kind = _coerce_str(ctx.data.get("type")) or "generic"

    metadata: dict[str, object] = {
        "notification_kind": notification_kind,
        "message_chars": len(message),
        "session_id": ctx.session_id,
    }
    if title:
        metadata["title"] = title[:120]
    # Truncate message to avoid blowing up the audit chain on long banners.
    if message:
        metadata["message_preview"] = message[:240]

    try:
        from _lib.observability import emit_framework_operation

        emit_framework_operation(
            ctx.project_root,
            operation="ide_notification",
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
        hook_kind="notification",
        script_path=__file__,
    )
