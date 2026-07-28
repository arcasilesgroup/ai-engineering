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


def detect_engine() -> str:
    """Return the active IDE / harness engine label. **Reads no stdin.**

    Detection priority:
    1. AIENG_HOOK_ENGINE env var (explicitly set in hook command strings)
    2. CLAUDE_PROJECT_DIR -> claude_code
    3. ANTIGRAVITY_PROJECT_DIR -> antigravity
    4. CWD markers: .codex/ -> codex, .agents/ -> antigravity, .claude/ -> claude_code
    5. AIENG_HOOK_ENGINE_DEFAULT, else the terminal literal ``unknown``

    Extracted from ``get_hook_context`` by spec-201 D-201-06 so the four
    inline emit sites in ``_lib/hook-common.py`` — which each guessed
    ``claude_code`` — resolve through the same ladder. Two implementations
    of "which engine am I?" is worse than either one alone: under a foreign
    harness the ladder produced ``unknown`` while hook-common produced
    ``claude_code``, so some events were dropped and the rest were
    mislabelled as Claude Code.

    Honest ``unknown`` beats a guess: misconfiguration surfaces instead of
    silently attributing a foreign host's telemetry to Claude Code.

    Hot path: the env branches short-circuit before any filesystem access,
    so the dominant surface (Claude Code sets CLAUDE_PROJECT_DIR) costs
    zero ``is_dir()`` syscalls. The three stats are paid only by a host
    with neither an engine env var nor a project-dir env var.
    """
    engine = os.environ.get("AIENG_HOOK_ENGINE", "").strip()
    if engine:
        return engine
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude_code"
    if os.environ.get("ANTIGRAVITY_PROJECT_DIR"):
        return "antigravity"
    # Infer from project markers
    cwd = Path.cwd()
    if (cwd / ".codex").is_dir():
        return "codex"
    if (cwd / ".agents").is_dir():
        return "antigravity"
    if (cwd / ".claude").is_dir():
        return "claude_code"
    return os.environ.get("AIENG_HOOK_ENGINE_DEFAULT", "").strip() or "unknown"


def get_hook_context() -> HookContext:
    """Detect IDE and return normalized hook context.

    Engine detection is delegated to :func:`detect_engine` (spec-201
    D-201-06) — this function adds the stdin read, the project root, the
    session id and the event-name normalization on top.
    """
    # Read stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    engine = detect_engine()

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
