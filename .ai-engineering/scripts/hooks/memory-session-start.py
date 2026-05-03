#!/usr/bin/env python3
"""spec-118 T-5.1 -- SessionStart hook: cross-session memory injection.

Reads the active spec, plan, recent edits, and last failures from
`runtime/checkpoint.json`, derives a recovery-context query, then shells out
to `ai-eng memory remember --top-k 5 --json` (or `python3 -m memory.cli ...`)
and renders an injection block on stdout for the IDE to surface.

Stdlib-only. Fail-open: any error degrades silently. Latency budget < 1.5s
p95; the subprocess is given 4s to keep the budget bounded.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import emit_event, run_hook_safe
from _lib.hook_context import get_hook_context

_SUBPROCESS_TIMEOUT_SEC = 4
_TOP_K = 5
_COMPONENT = "hook.memory-session-start"


def _resolve_memory_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "memory"


def _read_checkpoint(project_root: Path) -> dict:
    path = project_root / ".ai-engineering" / "state" / "runtime" / "checkpoint.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _derive_query(checkpoint: dict) -> str:
    """Build a focused query from the live work-plane context."""
    fragments: list[str] = []
    active = checkpoint.get("activeWork") or {}
    if isinstance(active, dict):
        for key in ("spec", "plan"):
            val = active.get(key)
            if isinstance(val, str) and val:
                fragments.append(val)
    edits = checkpoint.get("recentEdits") or []
    if isinstance(edits, list):
        fragments.extend(str(e) for e in edits[:3] if isinstance(e, str))
    failures = checkpoint.get("recentToolCalls") or []
    if isinstance(failures, list):
        for r in failures[-3:]:
            err = r.get("errorSummary") if isinstance(r, dict) else None
            if isinstance(err, str) and err:
                fragments.append(err[:120])
    if not fragments:
        return "session start"
    return " ".join(fragments)[:512]


def _emit_failure(project_root: Path, *, session_id: str | None, reason: str) -> None:
    event = {
        "kind": "framework_error",
        "component": _COMPONENT,
        "outcome": "failure",
        "source": "hook",
        "detail": {
            "hook_kind": "session-start",
            "error_code": "memory_session_start_failed",
            "reason": reason[:500],
        },
    }
    if session_id:
        event["sessionId"] = session_id
    try:
        emit_event(project_root, event)
    except Exception:
        pass


def _render_injection(payload: dict) -> str:
    if payload.get("status") != "ok":
        return ""
    results = payload.get("results") or []
    if not results:
        return ""
    lines = ["", "## Memory: relevant prior context", ""]
    for r in results[:5]:
        kind = r.get("target_kind", "?")
        score = r.get("score", 0.0)
        summary = (r.get("summary") or "")[:140]
        lines.append(f"- [{kind}] score={score:.3f} -- {summary}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "SessionStart":
        passthrough_stdin(ctx.data)
        return

    project_root = ctx.project_root
    session_id = ctx.session_id
    memory_dir = _resolve_memory_dir()
    if not memory_dir.exists():
        passthrough_stdin(ctx.data)
        return

    checkpoint = _read_checkpoint(project_root)
    query = _derive_query(checkpoint)

    cmd = [
        sys.executable,
        "-m",
        "memory.cli",
        "remember",
        query,
        "--top-k",
        str(_TOP_K),
        "--json",
    ]
    env = {
        **os.environ,
        "PYTHONPATH": str(memory_dir.parent) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
            cwd=str(project_root),
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _emit_failure(
            project_root,
            session_id=session_id,
            reason=f"memory.cli remember exceeded {_SUBPROCESS_TIMEOUT_SEC}s",
        )
        passthrough_stdin(ctx.data)
        return
    except Exception as exc:
        _emit_failure(project_root, session_id=session_id, reason=str(exc))
        passthrough_stdin(ctx.data)
        return

    if result.returncode != 0:
        # remember Exit(1) when status != ok is normal; only log truly unexpected
        # exits with stderr contents.
        if result.stderr.strip():
            _emit_failure(
                project_root,
                session_id=session_id,
                reason=result.stderr.strip()[:500],
            )
        passthrough_stdin(ctx.data)
        return

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        passthrough_stdin(ctx.data)
        return

    block = _render_injection(payload)
    if block:
        sys.stdout.write(block)

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(main, component=_COMPONENT, hook_kind="session-start")
