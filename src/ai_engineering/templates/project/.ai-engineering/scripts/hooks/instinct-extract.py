#!/usr/bin/env python3
"""Stop hook: aggregate recent observations into the canonical instinct store."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import is_debug_mode
from _lib.hook_context import get_hook_context
from _lib.instincts import extract_instincts
from _lib.observability import emit_framework_operation


def main() -> None:
    ctx = get_hook_context()
    extracted = extract_instincts(ctx.project_root)
    if not extracted:
        return

    emit_framework_operation(
        ctx.project_root,
        operation="instinct-extract",
        component="hook.instinct-extract",
        source="hook",
        metadata={"engine": ctx.engine},
    )

    if is_debug_mode():
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        with contextlib.suppress(Exception), open(debug_log, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] instinct-extract: refreshed canonical instinct store\n")


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
