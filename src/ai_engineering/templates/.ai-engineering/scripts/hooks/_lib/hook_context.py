"""Shared hook context detection for cross-IDE compatibility."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Gemini -> Claude event name normalization
_EVENT_NAME_MAP: dict[str, str] = {
    "BeforeTool": "PreToolUse",
    "AfterTool": "PostToolUse",
    "BeforeAgent": "UserPromptSubmit",
    "AfterAgent": "Stop",
    # Copilot camelCase (handled by wrappers, but just in case)
    "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse",
    "userPromptSubmitted": "UserPromptSubmit",
    "sessionEnd": "Stop",
    "sessionStart": "SessionStart",
    "errorOccurred": "PostToolUseFailure",
}


@dataclass
class HookContext:
    engine: str  # claude_code, gemini, github_copilot, codex
    project_root: Path
    session_id: str | None
    event_name: str  # Normalized to Claude convention
    event_name_raw: str  # As received from IDE
    data: dict  # Parsed stdin JSON


def get_hook_context() -> HookContext:
    """Detect IDE and return normalized hook context.

    Detection priority:
    1. AIENG_HOOK_ENGINE env var (explicitly set in hook command strings)
    2. CLAUDE_PROJECT_DIR -> claude_code
    3. GEMINI_PROJECT_DIR -> gemini
    4. Fallback: check CWD for .codex/ or .gemini/ markers
    """
    # Read stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    # Detect engine
    engine = os.environ.get("AIENG_HOOK_ENGINE", "").strip()
    if not engine:
        if os.environ.get("CLAUDE_PROJECT_DIR"):
            engine = "claude_code"
        elif os.environ.get("GEMINI_PROJECT_DIR"):
            engine = "gemini"
        else:
            # Infer from project markers
            cwd = Path.cwd()
            if (cwd / ".codex").is_dir():
                engine = "codex"
            elif (cwd / ".gemini").is_dir():
                engine = "gemini"
            else:
                engine = "claude_code"  # default fallback

    # Detect project root
    project_root_str = (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("GEMINI_PROJECT_DIR")
        or data.get("cwd")
        or str(Path.cwd())
    )
    project_root = Path(project_root_str)

    # Detect session ID
    session_id = (
        os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("GEMINI_SESSION_ID")
        or data.get("session_id")
    )

    # Normalize event name
    event_name_raw = os.environ.get("CLAUDE_HOOK_EVENT_NAME") or data.get("hook_event_name") or ""
    event_name = _EVENT_NAME_MAP.get(event_name_raw, event_name_raw)

    return HookContext(
        engine=engine,
        project_root=project_root,
        session_id=session_id,
        event_name=event_name,
        event_name_raw=event_name_raw,
        data=data,
    )


def passthrough_context(ctx: HookContext) -> None:
    """Write the original stdin data back to stdout for hook chaining."""
    if ctx.data:
        json.dump(ctx.data, sys.stdout)
