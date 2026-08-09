"""Two decorators, and the whole root pattern is cured.

The previous framework's wrapper ended in sys.exit(0) no matter what — even after
catching an exception, even for a guard. A guard that crashed reported "no objection,
go ahead". The cure is not a bigger wrapper: it is that a hook declares its class at
the top of its own file, where it cannot be overlooked, and the class decides what
happens when it fails.

    @guard      fails CLOSED. If it cannot decide, nothing passes.
    @telemetry  fails OPEN. It observes; it never opines.

You cannot write a fail-open guard without noticing, because "fails open" lives in a
decorator called telemetry.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from _emit import emit, home

# Security guards have NO bypass, and their denial message never prints the recipe: a
# model that may already be obeying injected instructions does not get handed the key
# inside the error text.
SECURITY = {"injection_guard", "no_verify_guard", "self_protect"}

# Flow guards allow a one-off bypass, but only one a person granted at a keyboard.
FLOW = {"design_gate", "loop_guard"}


def _bypass_file() -> Path:
    return home() / "cache" / "bypass.json"


def take_bypass(name: str) -> str | None:
    """Consume a one-off bypass granted by a human at a real keyboard. The agent has no
    keyboard, and that is the gate."""
    path = _bypass_file()
    try:
        grant = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if grant.get("guard") != name or grant.get("expires", 0) < time.time():
        return None
    path.unlink(missing_ok=True)
    return grant.get("reason", "no reason given")


def deny(name: str, message: str, structured: bool = False) -> None:
    """One denial protocol per surface, rather than a JSON reply and an exit status mixed
    together and hoped over.

    Claude Code documents its own PreToolUse answer: exit 0, with the decision in JSON. On
    exit 2 it ignores the JSON entirely and reads stderr — and the model can then treat an
    automated gate the way it treats a person refusing permission, and simply stop. That
    was observed twice in one session: a denied tool result, the turn-duration record three
    milliseconds later, no assistant message at all, and work resuming only when the person
    asked why. A guard blocks one operation; it does not turn an autonomous task back into
    somebody typing "continue".

    Everything else enforces by process status. Exit 2 denies on Copilot CLI, Cursor reads
    a JSON reply and spells its fields snake_case where VS Code spells them camelCase, so
    that reply carries both, and OpenCode's adapter turns the status into a throw. The
    message is written for a model to act on, because the model is shown it verbatim."""
    text = f"[{name}] {message}"
    sys.stderr.write(text + "\n")
    if name not in SECURITY:
        recipe = f'ai-eng plan --skip "<reason>" --guard {name}'
        sys.stderr.write(f"[{name}] A person — not you — can grant one bypass: {recipe}\n")
    if structured:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": text,
                    }
                }
            )
        )
        sys.exit(0)  # the call is denied by the decision above, not by the status
    print(
        json.dumps(
            {
                "permission": "deny",
                "continue": False,
                "user_message": text,
                "userMessage": text,
                "stop_reason": text,
                "stopReason": text,
            }
        )
    )
    sys.exit(2)


def guard(name: str):
    """Fails CLOSED. The hook returns None to allow, or a reason string to deny."""

    def decorate(fn):
        def run(payload: dict) -> None:
            def refuse(message: str) -> None:
                # What was said, where the dispatcher can cache it: a second delivery of
                # the same call gets this guard's own words, not a placeholder about it.
                payload["_denied"] = (name, message)
                deny(name, message, structured=bool(payload.get("_structured")))

            try:
                reason = fn(payload)
            except BaseException as exc:  # KeyboardInterrupt and MemoryError included
                emit(name, "error", error=repr(exc), outcome="blocked")
                refuse(
                    "BLOCKED: this guard crashed and cannot say whether the action is "
                    "safe. Fix the guard."
                )
            if reason is None:
                return  # a clean pass writes nothing
            fp = payload.get("_fp", "") if payload.get("_dedup") else ""
            if name in FLOW:
                granted = take_bypass(name)
                if granted is not None:
                    emit(name, "bypassed", reason=reason, granted_for=granted, fp=fp)
                    return
            emit(name, "blocked", reason=reason, fp=fp)
            refuse(f"BLOCKED: {reason}")

        run.hook_class = "guard"
        run.hook_name = name
        return run

    return decorate


def telemetry(name: str):
    """Fails OPEN. If this hook crashes, the action still stands."""

    def decorate(fn):
        def run(payload: dict) -> None:
            try:
                fn(payload)
            except Exception as exc:
                emit(name, "error", error=repr(exc), outcome="ignored")

        run.hook_class = "telemetry"
        run.hook_name = name
        return run

    return decorate
