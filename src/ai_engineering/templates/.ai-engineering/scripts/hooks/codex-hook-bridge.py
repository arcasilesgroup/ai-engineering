#!/usr/bin/env python3
"""Codex CLI hook bridge (spec-112 T-2.2).

Reads stdin JSON conforming to the Codex CLI hooks contract:
    {
        "event": "PreToolUse" | "PostToolUse" | "UserPromptSubmit" | "Stop",
        "tool_name": "...",
        "tool_input": {...},
        "prompt": "...",
        ...
    }

Normalizes the payload to a unified ``FrameworkEvent`` and delegates to
``_lib.hook-common.emit_event()`` so every Codex-originated event lands
in ``framework-events.ndjson`` with ``engine: "codex"``.

Fail-open: any unhandled error returns 0 so the IDE flow is never blocked
(spec-112 R-1). Codex does not require a JSON response on stdout.

Contract reference (cited in this docstring per spec-112 R-1): version
captured 2026-04 from `developers.openai.com/codex/hooks`.
"""

from __future__ import annotations

import importlib.util
import os
import re
from datetime import UTC, datetime
from pathlib import Path

_SKILL_RE = re.compile(r"^\s*/ai-([a-zA-Z0-9_-]+)")
_HOOK_KIND_MAP: dict[str, str] = {
    "PreToolUse": "pre-tool-use",
    "PostToolUse": "post-tool-use",
    "UserPromptSubmit": "user-prompt-submit",
    "Stop": "stop",
    "SessionStart": "session-start",
    "SessionEnd": "session-end",
}


def _load_hook_common():
    """Load `_lib/hook-common.py` (hyphenated filename) by spec_from_file_location."""
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
    """Compose the canonical wire format event for Codex bridge emissions."""
    event: dict = {
        "kind": kind,
        "engine": "codex",
        "timestamp": _now_iso(),
        "component": "hook.codex-bridge",
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


def _emit_skill_or_malformed(
    hc, project_root: Path, prompt: str, correlation_id: str, session_id: str | None
) -> None:
    match = _SKILL_RE.search(prompt or "")
    if not match:
        event = _build_event(
            project_root=project_root,
            kind="ide_hook",
            detail={
                "hook_kind": "user-prompt-submit",
                "reason": "no_ai_prefix" if prompt else "empty_prompt",
                "skill": None,
            },
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
    tool_name = payload.get("tool_name") or payload.get("toolName")
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


def main() -> None:
    hc = _load_hook_common()
    payload = hc.read_stdin_json()
    correlation_id = hc.get_correlation_id()
    session_id = hc.get_session_id()

    project_root_env = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR")
    project_root = Path(project_root_env) if project_root_env else hc._resolve_project_root()

    event_name = payload.get("event") or payload.get("hook_event_name") or ""
    if event_name == "UserPromptSubmit":
        _emit_skill_or_malformed(
            hc, project_root, payload.get("prompt", ""), correlation_id, session_id
        )
        return
    if event_name in _HOOK_KIND_MAP:
        _emit_ide_hook(hc, project_root, event_name, payload, correlation_id, session_id)
        return

    # Unknown / missing event: still surface as malformed so observability stays honest.
    event = _build_event(
        project_root=project_root,
        kind="ide_hook",
        detail={"hook_kind": "unknown", "raw_event": str(event_name)[:80]},
        correlation_id=correlation_id,
        session_id=session_id,
        outcome="warn",
    )
    hc.emit_event(project_root, event)


if __name__ == "__main__":
    # Lazy load so we can invoke run_hook_safe with the resolved module.
    hc_mod = _load_hook_common()
    hc_mod.run_hook_safe(
        main, component="hook.codex-bridge", hook_kind="codex-bridge", script_path=Path(__file__)
    )
