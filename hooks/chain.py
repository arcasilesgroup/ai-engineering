#!/usr/bin/env python3
"""The dispatcher. One process per call, and the only way to run anything.

Five Python starts cost about 130 ms per tool call; one costs about 20 ms. That matters
because a slow guard is a disabled guard on the surfaces that time out and carry on:
here latency is a security property, not a convenience. It also means "fail closed" has
exactly one place to be implemented instead of five.

Two things it owes the surfaces that are not Claude Code:

  * it fingerprints each decision by (session, tool, arguments) and returns the cached
    verdict if the same call arrives twice, so double registration — VS Code Copilot
    legitimately reads Claude's settings file — is harmless rather than a bug;
  * it normalises the payload itself, snake_case and camelCase alike, and does its own
    matcher evaluation, because VS Code parses Claude's matchers and then ignores them.

The guards sit beside this file and are imported by name: Python puts a script's own
folder on the search path, which is the whole of the mechanism. Nothing here imports
the installed package.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
import time
from pathlib import Path

from _emit import emit, home, session_id
from _wrap import deny

# event -> [(hook, tool matcher)]. Adding an entry point means adding a row here, and
# this table is what emits: there is no way to add a hook without instrumentation.
TABLE: dict[str, list[tuple[str, str]]] = {
    "PreToolUse": [
        ("self_protect", r"Edit|Write|MultiEdit|NotebookEdit|Bash"),
        ("no_verify_guard", r"Bash"),
        ("injection_guard", r"Read|NotebookRead"),
        ("loop_guard", r".*"),
        ("design_gate", r"Edit|Write|MultiEdit|NotebookEdit"),
    ],
    "PostToolUse": [
        ("injection_guard", r"WebFetch|Fetch|WebSearch|mcp__.*"),
        ("loop_guard", r".*"),
        ("autoformat", r"Edit|Write|MultiEdit"),
    ],
    "SessionStart": [("session", r".*")],
    "SessionEnd": [("session", r".*")],
    "Stop": [("session", r".*")],
}

# The two that observe. Everything else in TABLE can block, and a test reads this set
# against the decorator each module actually carries: registering telemetry as a gate, or
# a gate as telemetry, turns CI red with a message that names it.
TELEMETRY = {"autoformat", "session"}

ALIASES = {
    "toolName": "tool_name",
    "toolInput": "tool_input",
    "toolResponse": "tool_response",
    "sessionId": "session_id",
    "hookEventName": "hook_event_name",
    "toolUseId": "tool_use_id",
    "filePath": "file_path",
    "workspaceRoot": "cwd",
    "workspacePath": "cwd",
}


def normalise(raw: dict) -> dict:
    """Both spellings, one shape. Without this a guard scoped to file edits receives
    every tool call in a shape it does not expect, crashes, and correctly blocks
    everything — which is how you deny a whole surface by installing on it."""
    out = {ALIASES.get(key, key): value for key, value in raw.items()}
    out.setdefault("tool_name", out.get("tool") or "")
    out.setdefault("tool_input", out.get("input") or {})
    if isinstance(out["tool_input"], dict):
        out["tool_input"] = {ALIASES.get(k, k): v for k, v in out["tool_input"].items()}
    return out


def fingerprint(payload: dict) -> str:
    """One physical tool call. The identifier the surface gives the call is what makes
    two deliveries of the same call the same call — and what keeps a genuine retry loop
    from looking like one, which is the difference between deduplicating a double
    registration and blinding loop_guard."""
    body = json.dumps(
        [
            session_id(),
            payload.get("tool_name", ""),
            payload.get("tool_input", {}),
            payload.get("tool_use_id", ""),
        ],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def deduplicable(payload: dict) -> bool:
    return bool(payload.get("tool_use_id"))


def cache_file() -> Path:
    return home() / "cache" / "verdicts" / f"{session_id()}.json"


def cached(fp: str) -> dict | None:
    try:
        return json.loads(cache_file().read_text()).get(fp)
    except (OSError, ValueError):
        return None


def remember(fp: str, verdict: dict) -> None:
    path = cache_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        book = json.loads(path.read_text()) if path.exists() else {}
        book[fp] = verdict
        path.write_text(json.dumps(dict(list(book.items())[-500:])))
    except (OSError, ValueError):
        pass


def selected(event: str, tool: str) -> list[str]:
    rows = TABLE.get(event, [])
    return [n for n, m in rows if m == r".*" or re.fullmatch(m, tool or "")]


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        return 0  # nothing was decided, so there is nothing to judge
    try:
        payload = normalise(json.loads(raw))
    except ValueError:
        emit("chain", "error", error="payload is not JSON")
        deny(
            "chain",
            "BLOCKED: the hook payload could not be read, so nothing here "
            "can say whether this action is safe.",
        )
    event = sys.argv[1] if len(sys.argv) > 1 else payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    fp = fingerprint(payload)
    payload["_fp"], payload["_event"] = fp, event
    payload["_dedup"] = deduplicable(payload)

    dedup = deduplicable(payload) and event == "PreToolUse"
    verdict = cached(fp) if dedup else None
    if verdict is not None:
        if verdict["deny"]:
            deny(verdict["by"], verdict["message"])
        return 0  # same call, same answer: no guard decides the same call twice

    started = time.perf_counter()
    for name in selected(event, tool):
        try:
            module = importlib.import_module(name)
        except BaseException as broken:
            if name in TELEMETRY:
                emit(name, "error", error=repr(broken), outcome="ignored")
                continue
            emit(name, "error", error=repr(broken), outcome="blocked")
            deny(
                name,
                "BLOCKED: this guard could not even be loaded, so nothing here can "
                "say whether the action is safe. Fix the guard.",
            )
        try:
            module.run(payload)
        except SystemExit as stop:
            if stop.code == 2:
                remember(
                    fp,
                    {
                        "deny": True,
                        "by": name,
                        "message": "this call was already denied in this session",
                    },
                )
            raise
    if event == "PreToolUse":
        remember(fp, {"deny": False})
    elapsed = time.perf_counter() - started
    if elapsed > 0.2:
        emit("chain", "error", error="hot path over 200 ms", event=event, ms=int(elapsed * 1000))
    return 0


if __name__ == "__main__":
    sys.exit(main())
