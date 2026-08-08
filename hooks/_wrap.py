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


def deny(name: str, message: str) -> None:
    """Exit 2 denies on Claude Code and Copilot CLI. Cursor reads a JSON reply instead,
    and spells its fields snake_case where VS Code spells them camelCase, so the reply
    carries both. The message is written for a model to act on, because the model is
    shown it verbatim."""
    text = f"[{name}] {message}"
    sys.stderr.write(text + "\n")
    if name not in SECURITY:
        recipe = f'ai-eng plan --skip "<reason>" --guard {name}'
        sys.stderr.write(f"[{name}] A person — not you — can grant one bypass: {recipe}\n")
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
            try:
                reason = fn(payload)
            except BaseException as exc:  # KeyboardInterrupt and MemoryError included
                emit(name, "error", error=repr(exc), outcome="blocked")
                deny(
                    name,
                    "BLOCKED: this guard crashed and cannot say whether the action is "
                    "safe. Fix the guard.",
                )
                raise
            if reason is None:
                return  # a clean pass writes nothing
            fp = payload.get("_fp", "") if payload.get("_dedup") else ""
            if name in FLOW:
                granted = take_bypass(name)
                if granted is not None:
                    emit(name, "bypassed", reason=reason, granted_for=granted, fp=fp)
                    return
            emit(name, "blocked", reason=reason, fp=fp)
            deny(name, f"BLOCKED: {reason}")

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
