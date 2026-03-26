#!/usr/bin/env python3
"""Telemetry hook: emit skill_invoked on UserPromptSubmit matching /ai-*.

Called by Claude Code hooks (UserPromptSubmit event).
Fail-open: exit 0 always -- never blocks IDE.
Replaces former telemetry-skill.sh.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from datetime import UTC

from _lib.audit import (
    append_audit_event,
    get_audit_log,
    get_project_root,
    is_debug_mode,
    read_stdin,
)

_SKILL_RE = re.compile(r"/ai-([a-zA-Z-]+)")


def main() -> None:
    data = read_stdin()
    prompt = data.get("prompt", "")
    if not prompt:
        return

    match = _SKILL_RE.search(prompt)
    if not match:
        return

    raw = match.group(1)
    skill_name = f"ai-{raw.lower()}"

    project_root = get_project_root()
    audit_log = get_audit_log(project_root)

    append_audit_event(
        audit_log,
        {
            "event": "skill_invoked",
            "actor": "ai",
            "detail": {"skill": skill_name},
        },
        project_root=project_root,
    )

    if is_debug_mode():
        from datetime import datetime

        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] skill_invoked: {skill_name} (prompt: {prompt})\n")
        except Exception:
            pass


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
