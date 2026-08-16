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
import os
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
        ("change_scope_guard", r"Edit|Write|MultiEdit|NotebookEdit"),
        ("claim_scope_guard", r"Edit|Write|MultiEdit|NotebookEdit"),
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

# The floor, and the reason it is a floor rather than the whole table. A surface whose
# spelling is missing here sends a shape the guards do not expect; a guard that crashes is a
# guard that denies, and denying every call on a surface is how you disable a whole product
# by installing it. So these are built in and cannot be removed by editing a data file.
BUILT_IN_ALIASES = {
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
ADAPTERS = Path(__file__).resolve().parent.parent / "policy" / "adapters"


def adapter_aliases() -> dict:
    """Every spelling the declared adapters translate, over the built-in floor.

    `policy/adapters/*.json` and `policy/surface-adapter-v1.schema.json` described a
    translation table that nothing in the product read: the tests read it, the dispatcher
    normalised from its own hardcoded dict, and the two were free to disagree for as long as
    nobody checked. A contract with no consumer is a document, and this repository's whole
    argument is that a document is not a control.

    Read here rather than in the package, because this file may never import it — and read
    on each call, because a dispatcher process lives for one call. It costs a directory
    listing and a few kilobytes of JSON against a 20 ms budget.

    Unreadable is not fatal and deliberately so. The one thing normalisation must never do
    is fail: the floor above is what the guards need, and an adapter file somebody broke
    should cost its surface's extra spellings, not every call on every surface.
    """

    aliases = dict(BUILT_IN_ALIASES)
    try:
        files = sorted(ADAPTERS.glob("*.adapter.json"))
    except OSError:
        return aliases
    for path in files:
        try:
            declared = json.loads(path.read_text(encoding="utf-8"))
            fields = declared["translations"]["payload_field"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not isinstance(fields, dict):
            continue
        # The key is our canonical name and the value is what that surface sends, because
        # that is what the schema declares: `payload_field` is closed on our four names, so
        # a typo in a key is refused rather than silently becoming a translation nobody
        # asked for. This function needs the other direction, so it inverts.
        #
        # It read the pair the wrong way round until the second adapter landed. The only one
        # that existed mapped every name to itself, so both readings agreed and neither the
        # schema nor this loop could be wrong — and the first non-identity adapter would have
        # renamed `tool_input` to `args` on every surface at once, emptying the payload every
        # write guard reads. Two identity mappings are not a test of a translation.
        for ours, sent in fields.items():
            if isinstance(sent, str) and isinstance(ours, str) and sent and ours:
                aliases[sent] = ours
    return aliases


def adapter_version(surface_id: str) -> str:
    """The version the surface's adapter declares, or that it could not be read.

    One more reader of `policy/adapters/`, and deliberately the same directory the aliases
    come from: an adapter that translates a payload and an adapter that stamps the record
    have to be the same file, or the record names a version that translated nothing.
    """

    try:
        declared = json.loads((ADAPTERS / f"{surface_id}.adapter.json").read_text("utf-8"))
        version = declared.get("adapter_version")
    except (OSError, ValueError, TypeError):
        return "undetermined"
    return str(version) if version else "undetermined"


def normalise(raw: dict) -> dict:
    """Both spellings, one shape. Without this a guard scoped to file edits receives
    every tool call in a shape it does not expect, crashes, and correctly blocks
    everything — which is how you deny a whole surface by installing on it."""
    aliases = adapter_aliases()
    out = {aliases.get(key, key): value for key, value in raw.items()}
    out.setdefault("tool_name", out.get("tool") or "")
    out.setdefault("tool_input", out.get("input") or {})
    if isinstance(out["tool_input"], dict):
        out["tool_input"] = {aliases.get(k, k): v for k, v in out["tool_input"].items()}
        # The notebook tools send notebook_path and nothing else. Both guards on their
        # rows read file_path, so without this the table claimed coverage of two tools
        # that always passed.
        if not out["tool_input"].get("file_path"):
            out["tool_input"]["file_path"] = out["tool_input"].get("notebook_path", "")
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
    """A remembered verdict, or nothing. Anything malformed is nothing.

    A truthy read of `entry["deny"]` would let `{"deny": "no"}` — or a string, or a list —
    decide a call, and the branch below treats "not a denial" as "let it through". So the
    shape is checked and an entry that is not exactly one well-formed verdict is discarded,
    which puts the guards back in the path rather than skipping them.

    What this cannot do is authenticate the file. Anything able to write it can also write
    `hooks/*.py`, so it is not a new way in; it is stated here because a cache that looks
    like a control and is not one is worse than a cache nobody mistook for a control.
    """

    try:
        entry = json.loads(cache_file().read_text()).get(fp)
    except (OSError, ValueError):
        return None
    if not isinstance(entry, dict) or not isinstance(entry.get("deny"), bool):
        return None
    if entry["deny"] and not all(isinstance(entry.get(key), str) for key in ("by", "message")):
        return None
    return entry


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
        # Not just "is it JSON": `null`, `17` and `[1, 2]` all parse, and a payload that
        # is not an object reached the guards as something they could not read. That
        # exits 1, which every surface treats as a non-blocking error — the call went
        # through. Unreadable has one answer here and it is deny.
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError(f"payload is {type(body).__name__}, not an object")
        payload = normalise(body)
    except ValueError:
        emit("chain", "error", error="payload is not JSON")
        deny(
            "chain",
            "BLOCKED: the hook payload could not be read, so nothing here "
            "can say whether this action is safe.",
        )
    # The session the surface sent, adopted before anything computes a fingerprint or opens
    # a cache file. session_id() mints one per process, so the state one call wrote was a
    # file the next call never read: 358 of them on one machine, 48 bytes and one entry
    # each, and the guard that counts repeats could not reach its threshold however long a
    # session ran. Non-empty rather than present, because one surface sends the field as an
    # empty string instead of omitting it.
    if payload.get("session_id"):
        os.environ["AI_ENG_SESSION"] = str(payload["session_id"])
    # Which denial protocol this surface understands, decided by a field the surface itself
    # sends rather than by an install path. `transcript_path` is Claude Code's, in its own
    # snake_case spelling: VS Code Copilot reads the same settings file and would otherwise
    # be mistaken for it, and it sends camelCase, which is not aliased to this key.
    payload["_structured"] = "transcript_path" in body
    # And the record says which surface, or says it could not tell. `transcript_path` is the
    # one signal a surface sends about itself that nothing else here sends: `policy/surfaces
    # .toml` detects by an install path, which says a surface exists on this machine and not
    # that this call came through it. Anything more would be a guess written into the chain
    # as a fact, and the chain is the artefact that has to be trustworthy when everything
    # else is in doubt.
    if payload["_structured"]:
        os.environ.setdefault("AI_ENG_SURFACE", "claude-code")
        os.environ.setdefault("AI_ENG_ADAPTER", adapter_version("claude-code"))
    event = sys.argv[1] if len(sys.argv) > 1 else payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    fp = fingerprint(payload)
    payload["_fp"], payload["_event"] = fp, event
    payload["_dedup"] = deduplicable(payload)

    dedup = deduplicable(payload) and event == "PreToolUse"
    verdict = cached(fp) if dedup else None
    if verdict is not None:
        if verdict["deny"]:
            deny(verdict["by"], verdict["message"], structured=payload["_structured"])
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
            said = (
                "BLOCKED: this guard could not even be loaded, so nothing here can "
                "say whether the action is safe. Fix the guard."
            )
            # Only when this call is one the cache is keyed on. The fingerprint omits the
            # event, so remembering a PostToolUse denial here overwrote the PreToolUse
            # answer for the same call, and a later delivery was denied by a guard that was
            # never on its row.
            if dedup:
                remember(fp, {"deny": True, "by": name, "message": said})
            deny(name, said, structured=payload["_structured"])
        # The class the hook declares about itself, read here and not only in a test. A
        # guard that lost its decorator is a hook the dispatcher would run on a blocking
        # event with no promise about what a crash means — which is a fail-open control
        # wearing a guard's name. Undeclared is refused, not assumed.
        kind = getattr(getattr(module, "run", None), "hook_class", None)
        expected = "telemetry" if name in TELEMETRY else "guard"
        if kind != expected:
            if expected == "telemetry":
                emit(name, "error", error=f"declares {kind!r}, not telemetry", outcome="ignored")
                continue
            emit(name, "error", error=f"declares {kind!r}, not guard", outcome="blocked")
            said = (
                "BLOCKED: this hook runs where a call can be stopped and does not declare "
                "itself a guard, so nothing here can say whether the action is safe."
            )
            # Only when this call is one the cache is keyed on. The fingerprint omits the
            # event, so remembering a PostToolUse denial here overwrote the PreToolUse
            # answer for the same call, and a later delivery was denied by a guard that was
            # never on its row.
            if dedup:
                remember(fp, {"deny": True, "by": name, "message": said})
            deny(name, said, structured=payload["_structured"])
        try:
            module.run(payload)
        except SystemExit:
            # Zero as well as two: Claude Code's denial is a decision in JSON on exit 0,
            # and a denial that is not remembered is one the next delivery asks again.
            if payload.get("_denied"):
                by, said = payload["_denied"]
                remember(fp, {"deny": True, "by": by, "message": said})
            raise
    if event == "PreToolUse":
        remember(fp, {"deny": False})
    elapsed = time.perf_counter() - started
    if elapsed > 0.2:
        emit("chain", "error", error="hot path over 200 ms", event=event, ms=int(elapsed * 1000))
    return 0


if __name__ == "__main__":
    sys.exit(main())
