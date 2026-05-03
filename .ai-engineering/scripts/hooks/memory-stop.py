#!/usr/bin/env python3
"""spec-118 T-2.4 -- Stop hook: persist current session as an episode.

Stdlib-only. Shells to `python3 -m memory.cli stop ...` via subprocess so the
hook never imports fastembed, hdbscan, or numpy directly. The CLI handles the
synchronous SQLite write (cheap, ~10 ms) and emits `memory_event/episode_stored`
through `_lib/observability.py::append_framework_event`.

Per CONCERN-3 from the pre-dispatch guard: this hook runs after `runtime-stop.py`
in the Stop chain. The synchronous portion targets <200 ms; embedding work is
fire-and-forget in Phase 3 (T-3.2). The wrapper enforces a 25 s soft timeout
on the subprocess to keep the chain budget bounded; the IDE-side hook timeout
in `.claude/settings.json` is set to 10 s as the outer safety net.

Fail-open: any error degrades silently with a `framework_error` event.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import emit_event, get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context

_SUBPROCESS_TIMEOUT_SEC = 25
_COMPONENT = "hook.memory-stop"


def _resolve_memory_cli() -> Path:
    """Locate the canonical memory module path. Sibling of hooks/."""
    return Path(__file__).resolve().parent.parent / "memory"


def _emit_failure(project_root: Path, *, session_id: str | None, reason: str) -> None:
    event = {
        "kind": "framework_error",
        "component": _COMPONENT,
        "outcome": "failure",
        "source": "hook",
        "detail": {
            "hook_kind": "stop",
            "error_code": "memory_stop_failed",
            "reason": reason[:500],
        },
    }
    if session_id:
        event["sessionId"] = session_id
    try:
        emit_event(project_root, event)
    except Exception:
        pass


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "Stop":
        passthrough_stdin(ctx.data)
        return

    project_root = ctx.project_root
    session_id = ctx.session_id

    if not session_id:
        # Without a sessionId we cannot filter framework-events. Skip silently.
        passthrough_stdin(ctx.data)
        return

    memory_dir = _resolve_memory_cli()
    if not memory_dir.exists():
        passthrough_stdin(ctx.data)
        return

    cmd = [
        sys.executable,
        "-m",
        "memory.cli",
        "stop",
        "--session-id",
        session_id,
        "--json",
    ]
    env = {
        "PYTHONPATH": str(memory_dir.parent),
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
            cwd=str(project_root),
            env={**__import__("os").environ, **env},
            check=False,
        )
    except subprocess.TimeoutExpired:
        _emit_failure(
            project_root,
            session_id=session_id,
            reason=f"memory.cli stop exceeded {_SUBPROCESS_TIMEOUT_SEC}s",
        )
        passthrough_stdin(ctx.data)
        return
    except Exception as exc:
        _emit_failure(project_root, session_id=session_id, reason=str(exc))
        passthrough_stdin(ctx.data)
        return

    if result.returncode != 0:
        _emit_failure(
            project_root,
            session_id=session_id,
            reason=(result.stderr or result.stdout or "non-zero exit")[:500],
        )

    # The CLI itself emitted memory_event/episode_stored. Hook stays quiet on
    # success to avoid duplicate events.
    _ = get_correlation_id()
    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(main, component=_COMPONENT, hook_kind="stop")
