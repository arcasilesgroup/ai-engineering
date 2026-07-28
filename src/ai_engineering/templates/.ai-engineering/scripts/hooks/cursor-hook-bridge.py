"""Cursor hook bridge — spec-133 D-133-06, repaired by spec-201 D-201-17.

Cursor ships native hooks whose stdio contract is shaped like Claude Code's.
This adapter reads the Cursor payload from stdin, runs the matching canonical
guards, and translates their exit codes into Cursor's deny protocol.

It had never fired once. Four independent defects, all fixed here:

1. **Handlers that do not exist.** The old dispatch resolved
   ``hooks_root / f"{canonical.lower()}.py"`` — ``pretooluse.py``,
   ``posttooluse.py``, ``stop.py``. No such files have ever existed, so every
   invocation hit the "no canonical handler" branch and returned 0.
   :data:`_GUARD_MAP` now names real scripts, and
   :func:`missing_guard_scripts` makes a typo a test failure rather than a
   silent allow.
2. **A ``"python"`` spawn.** The old code ran the literal ``python``, which is
   absent on macOS and most modern Linux. Now :data:`sys.executable` — the
   bridge is already running under the >=3.11 interpreter ``_lib/run-hook.sh``
   resolved, so re-resolving would be pure hot-path cost.
3. **No deny envelope.** The bridge wrote nothing to stdout, so it was
   structurally incapable of expressing a denial no matter what the guard
   decided. Cursor's protocol (``packages/hooks/src/validators/``
   ``beforeCommandExecutionHookResponse.ts``) is a JSON object on stdout —
   ``{"permission": "allow"|"deny"|"ask", "user_message"?, "agent_message"?}``
   — consumed as ``if (A?.permission === "deny") throw ...``. A non-zero exit
   is a hook *error* to Cursor, not a denial, so :func:`_deny_envelope` writes
   the envelope and exits 0.
4. **The event key.** Cursor injects ``hook_event_name: <step>`` into the
   payload (verified in the 3.12.17 ``executeHookForStep`` builder); the bridge
   only looked at ``event`` / ``hookEventName``, so a real Cursor payload was
   rejected as "missing 'event'". All three keys are accepted now.

Also removed: the ``subagentStart -> SubagentStop`` mis-map. Cursor's
``subagentStart`` is a *start* lifecycle event and has no canonical Stop
analogue; mapping it to the Stop handler emitted a session-end rollup at
session begin.

Reference: https://cursor.com/docs/hooks
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Final

# ``openai_compatible``, NOT ``cursor``.
#
# ``_ALLOWED_ENGINES`` (``_lib/observability.py``) is a closed enum and
# ``cursor`` is not a member; spec-201 D-201-06 admits ``openai_compatible``
# for exactly "any OpenAI-shaped host (OpenCode, Cursor, a bare
# /v1/chat/completions driver)". The unadmitted literal used to drop the event
# silently and now raises a ``framework_error`` per refused event.
_HOOK_ENGINE: Final[str] = "openai_compatible"

_DENY_EXIT: Final[int] = 2
_INTEGRITY_EXIT: Final[int] = 3

# Cursor step -> the canonical guards that step should run, in short-circuit
# order. Every value must be a file that exists under this directory.
#
# This is the bridge's CAPABILITY, not the registration. ``.cursor/hooks.json``
# deliberately registers only ``beforeShellExecution`` and ``beforeReadFile``,
# because Cursor also loads ``<workspace>/.claude/settings.json`` natively and
# projects Claude's lifecycle events onto ``stop`` / ``sessionStart`` /
# ``sessionEnd`` / ``beforeSubmitPrompt`` / ``preCompact`` / ``preToolUse`` /
# ``postToolUse`` / ``subagentStop``. Its dedupe keys on the literal command
# string, so registering those steps here would DOUBLE-fire them rather than
# add coverage. The mappings stay so a Cursor-only consumer (no
# ``.claude/settings.json``) can register them deliberately.
_GUARD_MAP: Final[dict[str, tuple[str, ...]]] = {
    "beforeShellExecution": ("no-verify-guard.py", "prompt-injection-guard.py"),
    "preToolUse": ("no-verify-guard.py", "prompt-injection-guard.py"),
    "beforeReadFile": ("injection-read-guard.py",),
    "postToolUse": ("injection-read-guard.py",),
    "beforeSubmitPrompt": ("runtime-progressive-disclosure.py",),
    "stop": ("runtime-stop.py",),
    "sessionStart": ("runtime-session-start.py",),
    "sessionEnd": ("runtime-session-end.py",),
    "subagentStop": ("runtime-subagent-stop.py",),
    "preCompact": ("runtime-compact.py",),
}

# Cursor step -> the canonical event name the guards expect on stdin.
_CANONICAL_EVENT: Final[dict[str, str]] = {
    "beforeShellExecution": "PreToolUse",
    "preToolUse": "PreToolUse",
    "beforeReadFile": "PostToolUse",
    "postToolUse": "PostToolUse",
    "beforeSubmitPrompt": "UserPromptSubmit",
    "stop": "Stop",
    "sessionStart": "SessionStart",
    "sessionEnd": "SessionEnd",
    "subagentStop": "SubagentStop",
    "preCompact": "PreCompact",
}


def hooks_root() -> Path:
    return Path(__file__).resolve().parent


def missing_guard_scripts() -> list[str]:
    """Return every `_GUARD_MAP` entry with no file on disk (should be empty).

    The original defect class was a dispatch that named handlers which never
    existed, so this is asserted by test rather than trusted.
    """
    root = hooks_root()
    return sorted(
        {script for scripts in _GUARD_MAP.values() for script in scripts}
        - {p.name for p in root.glob("*.py")}
    )


def _resolve_step(payload: dict) -> str:
    """Cursor 3.x sends `hook_event_name`; older builds sent `event`."""
    for key in ("hook_event_name", "event", "hookEventName"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _canonical_payload(step: str, payload: dict) -> dict:
    """Translate a Cursor payload into the shape the canonical guards read."""
    out: dict = dict(payload)
    out["hook_event_name"] = _CANONICAL_EVENT.get(step, step)
    if step == "beforeShellExecution":
        out["tool_name"] = "Bash"
        out["tool_input"] = {"command": payload.get("command") or ""}
    elif step == "beforeReadFile":
        # `injection-read-guard._is_external()` allowlists `Read`; the file body
        # is the untrusted content, so it goes where the guard looks for it.
        out["tool_name"] = "Read"
        out["tool_input"] = {"file_path": payload.get("file_path") or ""}
        out["tool_response"] = payload.get("content") or ""
    if payload.get("session_id") and not out.get("session_id"):
        out["session_id"] = payload["session_id"]
    out["__bridge"] = {
        "engine": _HOOK_ENGINE,
        "cursor_step": step,
        "canonical_event": out["hook_event_name"],
    }
    return out


def _deny_envelope(reason: str) -> None:
    """Write Cursor's deny envelope to stdout.

    Cursor treats a non-zero exit as a hook error, so the process still exits 0
    — the envelope is what denies.
    """
    json.dump(
        {"permission": "deny", "agent_message": reason, "user_message": reason},
        sys.stdout,
    )
    sys.stdout.write("\n")
    sys.stdout.flush()


def _deny_reason(script: str, stdout: str) -> str:
    """Recover the guard's own reason string from its block body."""
    try:
        body = json.loads(stdout.strip())
    except (json.JSONDecodeError, ValueError):
        body = None
    if isinstance(body, dict):
        reason = body.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return f"{script} denied this call."


def _run_guard(script: str, payload: dict) -> subprocess.CompletedProcess:
    """Run one canonical guard, capturing its streams.

    Capture is load-bearing: guards write their own JSON body (and
    `passthrough_stdin` echoes the payload) to stdout, which would corrupt the
    single envelope Cursor parses.
    """
    return subprocess.run(
        [sys.executable, str(hooks_root() / script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "AIENG_HOOK_ENGINE": _HOOK_ENGINE},
    )


def main() -> int:
    """Read the Cursor payload, run the mapped guards, emit Cursor's verdict."""
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"cursor-hook-bridge: invalid stdin JSON: {exc}\n")
        return 1
    if not isinstance(payload, dict):
        sys.stderr.write("cursor-hook-bridge: stdin payload must be a JSON object\n")
        return 1

    step = _resolve_step(payload)
    if not step:
        sys.stderr.write("cursor-hook-bridge: missing 'hook_event_name' in payload\n")
        return 1

    guards = _GUARD_MAP.get(step)
    if not guards:
        # Unknown or deliberately unmapped Cursor step: observe-only.
        return 0

    canonical = _canonical_payload(step, payload)
    for script in guards:
        result = _run_guard(script, canonical)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.returncode == _DENY_EXIT:
            _deny_envelope(_deny_reason(script, result.stdout))
            return 0
        if result.returncode != 0:
            # Fail-open plumbing (gate-policy.md): an integrity mismatch (3) or
            # a crash is a defect in the guard, not a verdict on the user's
            # call. Loud on stderr, never a silent deny.
            sys.stderr.write(
                f"cursor-hook-bridge: {script} exited {result.returncode} "
                f"({'integrity' if result.returncode == _INTEGRITY_EXIT else 'error'}); "
                "passing through as allow.\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
