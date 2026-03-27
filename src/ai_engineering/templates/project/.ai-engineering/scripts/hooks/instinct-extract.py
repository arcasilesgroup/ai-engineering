#!/usr/bin/env python3
"""Stop hook: aggregate recent observations into the canonical instinct store."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import get_project_root, is_debug_mode, read_stdin

from ai_engineering.state.instincts import extract_instincts
from ai_engineering.state.observability import emit_framework_operation


def main() -> None:
    _ = read_stdin()
    project_root = get_project_root()
    extracted = extract_instincts(project_root)
    if not extracted:
        return

    emit_framework_operation(
        project_root,
        operation="instinct-extract",
        component="hook.instinct-extract",
        source="hook",
        metadata={"engine": os.environ.get("AIENG_HOOK_ENGINE", "claude_code")},
    )

    if is_debug_mode():
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        with contextlib.suppress(Exception), open(debug_log, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] instinct-extract: refreshed canonical instinct store\n")


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
