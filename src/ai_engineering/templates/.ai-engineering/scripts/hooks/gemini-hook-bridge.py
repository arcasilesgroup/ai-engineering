#!/usr/bin/env python3
"""Gemini CLI hook bridge (spec-112 T-2.6).

Reads stdin JSON conforming to the Gemini CLI hooks contract:
    {
        "eventType": "BeforeTool" | "AfterTool" | "BeforeAgent"
                   | "AfterAgent" | "SessionStart" | "SessionEnd",
        "toolName": "...",
        "toolArgs": {...},
        "prompt": "...",
        ...
    }

Normalizes the payload to the unified ``FrameworkEvent`` schema and
delegates to ``_lib.hook-common.emit_event()`` so every Gemini-originated
event lands in ``framework-events.ndjson`` with ``engine: "gemini"``.

Gemini hooks MUST return a JSON object on stdout. The bridge always
writes ``{"action": "continue"}`` (or ``"block"`` on explicit deny
decisions) so Gemini's parser cannot fail. Even on malformed stdin we
emit a JSON response and exit 0 (fail-open per spec-112 R-1).

Contract reference (per spec-112 R-1): version captured 2026-04 from
`geminicli.com/docs/hooks/`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

_SKILL_RE = re.compile(r"^\s*/ai-([a-zA-Z0-9_-]+)")

# Gemini event names normalized to canonical hook_kind. The same map covers
# both the Gemini-native verbs and the Claude-style verbs that show up when
# the bridge is reused from a unified config.
_HOOK_KIND_MAP: dict[str, str] = {
    "BeforeTool": "pre-tool-use",
    "AfterTool": "post-tool-use",
    "BeforeAgent": "user-prompt-submit",
    "AfterAgent": "stop",
    "SessionStart": "session-start",
    "SessionEnd": "session-end",
    "PreToolUse": "pre-tool-use",
    "PostToolUse": "post-tool-use",
    "UserPromptSubmit": "user-prompt-submit",
    "Stop": "stop",
}


def _load_hook_common():
    """Load `_lib/hook-common.py` (hyphenated filename) by file location."""
    here = Path(__file__).resolve().parent
    hook_common_path = here / "_lib" / "hook-common.py"
    spec = importlib.util.spec_from_file_location("aieng_hook_common", hook_common_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load hook-common at {hook_common_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_event(
    *,
    project_root: Path,
    kind: str,
    detail: dict,
    correlation_id: str,
    session_id: str | None,
    outcome: str = "success",
) -> dict:
    event: dict = {
        "kind": kind,
        "engine": "gemini",
        "timestamp": _now_iso(),
        "component": "hook.gemini-bridge",
        "outcome": outcome,
        "correlationId": correlation_id,
        "schemaVersion": "1.0",
        "project": project_root.name,
        "source": "hook",
        "detail": detail,
    }
    if session_id:
        event["sessionId"] = session_id
    return event


def _resolve_project_root(hc) -> Path:
    env_root = os.environ.get("GEMINI_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root)
    return hc._resolve_project_root()


def _emit_skill_or_malformed(
    hc, project_root: Path, prompt: str, correlation_id: str, session_id: str | None
) -> None:
    match = _SKILL_RE.search(prompt or "")
    if not match:
        event = _build_event(
            project_root=project_root,
            kind="skill_invoked_malformed",
            detail={"reason": "no_ai_prefix" if prompt else "empty_prompt"},
            correlation_id=correlation_id,
            session_id=session_id,
            outcome="warn",
        )
        hc.emit_event(project_root, event)
        return
    skill_name = f"ai-{match.group(1).lower()}"
    event = _build_event(
        project_root=project_root,
        kind="skill_invoked",
        detail={"skill": skill_name},
        correlation_id=correlation_id,
        session_id=session_id,
    )
    hc.emit_event(project_root, event)


def _emit_ide_hook(
    hc,
    project_root: Path,
    event_name: str,
    payload: dict,
    correlation_id: str,
    session_id: str | None,
) -> None:
    hook_kind = _HOOK_KIND_MAP.get(event_name, event_name.lower())
    detail: dict = {"hook_kind": hook_kind}
    tool_name = payload.get("toolName") or payload.get("tool_name")
    if tool_name:
        detail["tool_name"] = tool_name
    event = _build_event(
        project_root=project_root,
        kind="ide_hook",
        detail=detail,
        correlation_id=correlation_id,
        session_id=session_id,
    )
    hc.emit_event(project_root, event)


def _write_response(action: str = "continue") -> None:
    """Always emit a JSON object on stdout per Gemini hook contract."""
    sys.stdout.write(json.dumps({"action": action}))
    sys.stdout.flush()


def main() -> None:
    hc = _load_hook_common()
    payload = hc.read_stdin_json()
    correlation_id = hc.get_correlation_id()
    session_id = hc.get_session_id()
    project_root = _resolve_project_root(hc)

    event_name = payload.get("eventType") or payload.get("event") or ""

    # Both BeforeAgent (Gemini userPromptSubmitted analog) and the legacy
    # UserPromptSubmit are routed through skill detection because some
    # Gemini configs forward prompts via either field.
    if event_name in {"BeforeAgent", "UserPromptSubmit"}:
        _emit_skill_or_malformed(
            hc,
            project_root,
            payload.get("prompt", "") or payload.get("userPrompt", ""),
            correlation_id,
            session_id,
        )
        _write_response()
        return

    if event_name in _HOOK_KIND_MAP:
        _emit_ide_hook(hc, project_root, event_name, payload, correlation_id, session_id)
        _write_response()
        return

    # Unknown event kind: surface as warn-outcome ide_hook so observability
    # remains honest, and still respond so Gemini does not block.
    event = _build_event(
        project_root=project_root,
        kind="ide_hook",
        detail={"hook_kind": "unknown", "raw_event": str(event_name)[:80]},
        correlation_id=correlation_id,
        session_id=session_id,
        outcome="warn",
    )
    hc.emit_event(project_root, event)
    _write_response()


if __name__ == "__main__":
    # Even on hard failure we want a stdout response so Gemini's parser
    # does not error. The wrapper around run_hook_safe ensures a JSON
    # response is written before any exception is surfaced.
    try:
        main()
    except Exception:
        _write_response()
        sys.exit(0)
