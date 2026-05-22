"""Shared hook context detection for cross-IDE compatibility."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Antigravity -> Claude event name normalization.
#
# WARNING: BeforeAgent / AfterAgent are NOT symmetric with UserPromptSubmit /
# Stop. Antigravity's "agent" lifecycle is broader than a Claude "user prompt" — a
# BeforeAgent may fire for non-prompt agent boots. Hooks gated to
# UserPromptSubmit (e.g. runtime-progressive-disclosure) should add an extra
# guard against ``ctx.engine == "antigravity"`` if firing on agent-boot is unwanted.
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


# ---------------------------------------------------------------------------
# Canonical state-plane subdir locations (spec-125 Wave 2).
#
# Source of truth for the relocated subdirs. Hook scripts and cross-IDE
# wrappers import these helpers instead of hardcoding the path so a
# future move only requires editing this file. Both helpers take the
# already-resolved ``project_root`` (see ``get_hook_context``) and return
# the absolute directory path. Callers are responsible for ``mkdir`` as
# needed; the helpers perform pure path arithmetic so they remain safe
# to call inside fast-path probes.
# ---------------------------------------------------------------------------


def RUNTIME_DIR(project_root: Path) -> Path:
    """Return ``<project_root>/.ai-engineering/runtime`` (canonical runtime dir)."""
    return project_root / ".ai-engineering" / "runtime"


def CACHE_DIR(project_root: Path) -> Path:
    """Return ``<project_root>/.ai-engineering/cache`` (canonical cache umbrella)."""
    return project_root / ".ai-engineering" / "cache"


@dataclass
class HookContext:
    engine: str  # claude_code, antigravity, github_copilot, codex
    project_root: Path
    session_id: str | None
    event_name: str  # Normalized to Claude convention
    event_name_raw: str  # As received from IDE
    data: dict  # Parsed stdin JSON
    # spec-131 sub-004 T-4.A: distinguishes a Task-tool sub-agent dispatch
    # ("subagent") from a main-thread invocation ("main"). Sub-agent posture
    # unlocks the positive-allow-list lane in prompt-injection-guard.py
    # for read-only commands (rg/grep/find/ls/cat without redirects).
    agent_kind: str = "main"


def _looks_like_subagent_transcript(transcript_path: object) -> bool:
    """Return True when ``transcript_path`` basename looks like a sub-agent log.

    Claude Code writes sub-agent transcripts to
    ``.claude/projects/<project>/subagent-<id>.jsonl``. Defensive: a
    non-string value (e.g. malformed payload where the field is an int)
    returns False so the heuristic never raises.
    """
    if not isinstance(transcript_path, str) or not transcript_path:
        return False
    try:
        basename = Path(transcript_path).name
    except (ValueError, TypeError):
        return False
    return basename.startswith("subagent-")


def _resolve_agent_kind(data: dict) -> str:
    """Detect ``main`` vs ``subagent`` from the stdin payload.

    spec-131 sub-004 D-131-11 / E-1 heuristic:
    - ``parent_session_id`` or alias ``parent_session`` set -> subagent.
    - ``is_subagent`` is True (Codex bridge / Copilot adapter flag) ->
      subagent.
    - ``transcript_path`` basename starts with ``subagent-`` -> subagent.
    - Otherwise -> main (false-negative is safer than false-positive — a
      main-thread call mistakenly tagged subagent would skip the IOC
      pattern scan that should run).
    """
    if not isinstance(data, dict):
        return "main"
    if data.get("parent_session_id") or data.get("parent_session"):
        return "subagent"
    if data.get("is_subagent") is True:
        return "subagent"
    if _looks_like_subagent_transcript(data.get("transcript_path")):
        return "subagent"
    return "main"


def get_hook_context() -> HookContext:
    """Detect IDE and return normalized hook context.

    Detection priority:
    1. AIENG_HOOK_ENGINE env var (explicitly set in hook command strings)
    2. CLAUDE_PROJECT_DIR -> claude_code
    3. ANTIGRAVITY_PROJECT_DIR -> antigravity
    4. Fallback: check CWD for .codex/ or .agents/ markers
    """
    # Read stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    # Detect engine. Earlier versions silently fell back to "claude_code"
    # whenever no env var or filesystem marker matched, which misclassified
    # any future runtime in audit telemetry. Now require an explicit env-var
    # opt-in for the silent fallback so misconfiguration surfaces loudly.
    engine = os.environ.get("AIENG_HOOK_ENGINE", "").strip()
    if not engine:
        if os.environ.get("CLAUDE_PROJECT_DIR"):
            engine = "claude_code"
        elif os.environ.get("ANTIGRAVITY_PROJECT_DIR"):
            engine = "antigravity"
        else:
            # Infer from project markers
            cwd = Path.cwd()
            if (cwd / ".codex").is_dir():
                engine = "codex"
            elif (cwd / ".agents").is_dir():
                engine = "antigravity"
            elif (cwd / ".claude").is_dir():
                engine = "claude_code"
            else:
                engine = os.environ.get("AIENG_HOOK_ENGINE_DEFAULT", "").strip() or "unknown"

    # Detect project root
    project_root_str = (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("ANTIGRAVITY_PROJECT_DIR")
        or data.get("cwd")
        or str(Path.cwd())
    )
    project_root = Path(project_root_str)

    # Detect session ID
    session_id = (
        os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("ANTIGRAVITY_SESSION_ID")
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
        agent_kind=_resolve_agent_kind(data),
    )


def passthrough_context(ctx: HookContext) -> None:
    """Write the original stdin data back to stdout for hook chaining."""
    if ctx.data:
        json.dump(ctx.data, sys.stdout)
