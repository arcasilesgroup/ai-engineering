#!/usr/bin/env python3
"""Pre/PostToolUse hook: record tool usage observations for instinct extraction.

Writes observations to ~/.ai-engineering/instincts/projects/<hash>/observations.jsonl.
Replaces former telemetry-agent.sh. Emits agent_dispatched to audit-log when
tool_name == 'Agent'.

Fail-open: exit 0 always -- never blocks IDE.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import (
    append_audit_event,
    get_audit_log,
    get_project_root,
    is_debug_mode,
    passthrough_stdin,
    read_stdin,
)

_SECRET_RE = re.compile(
    r"(?i)(api_key|token|secret|password|authorization|credentials|auth)"
    r"([\"'\s:=]+)"
    r"[^\s\"',;]{4,}",
)

_ALLOWED_ENTRYPOINTS = {"cli", "sdk-ts"}
_INSTINCTS_BASE = Path.home() / ".ai-engineering" / "instincts"
_MAX_TRUNCATE = 5000


def _get_project_hash() -> str:
    """SHA256 of git remote URL (first 8 chars), fallback to cwd hash."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            digest = hashlib.sha256(result.stdout.strip().encode()).hexdigest()[:8]
            return digest
    except Exception:
        pass
    digest = hashlib.sha256(os.getcwd().encode()).hexdigest()[:8]
    return digest


def _scrub_secrets(text: str) -> str:
    """Replace potential secrets with [REDACTED]."""
    if not text:
        return text
    return _SECRET_RE.sub(r"\1\2[REDACTED]", text)


def _truncate(text: str, max_len: int = _MAX_TRUNCATE) -> str:
    """Truncate text to max_len characters."""
    if not text or len(text) <= max_len:
        return text
    return text[:max_len] + "...[truncated]"


def _safe_str(value: object) -> str:
    """Convert value to string for scrubbing/truncation."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, separators=(",", ":"), default=str)
    except Exception:
        return str(value)


def _get_observations_dir(project_hash: str) -> Path:
    """Get or create the observations directory for a project."""
    project_dir = _INSTINCTS_BASE / "projects" / project_hash
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def _update_projects_registry(project_hash: str) -> None:
    """Update projects.json registry with this project."""
    registry_path = _INSTINCTS_BASE / "projects" / "projects.json"
    try:
        registry = {}
        if registry_path.exists():
            with open(registry_path, encoding="utf-8") as f:
                registry = json.load(f)

        if project_hash not in registry:
            project_root = get_project_root()
            registry[project_hash] = {
                "path": str(project_root),
                "name": project_root.name,
                "firstSeen": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lastSeen": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        else:
            registry[project_hash]["lastSeen"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except Exception:
        pass


def _write_observation(project_hash: str, observation: dict) -> None:
    """Append an observation to the project's observations.jsonl."""
    obs_dir = _get_observations_dir(project_hash)
    obs_file = obs_dir / "observations.jsonl"
    try:
        with open(obs_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(observation, separators=(",", ":")) + "\n")
    except Exception:
        pass


def _handle_agent_dispatch(data: dict, project_root: Path) -> None:
    """Emit agent_dispatched event to audit-log when tool_name is Agent."""
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    subagent_type = tool_input.get("subagent_type", tool_input.get("description", ""))
    if not subagent_type:
        return

    normalized = subagent_type.lower()
    if normalized.startswith("ai-"):
        normalized = normalized[3:]
    agent_name = f"ai-{normalized}"

    description = tool_input.get("description", "")
    if isinstance(description, str) and len(description) > 200:
        description = description[:200] + "..."

    audit_log = get_audit_log(project_root)
    append_audit_event(
        audit_log,
        {
            "event": "agent_dispatched",
            "actor": "ai",
            "agent": agent_name,
            "detail": {
                "agent": agent_name,
                "description": description,
            },
        },
        project_root=project_root,
    )


def main() -> None:
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT_NAME", "")
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")

    if entrypoint and entrypoint not in _ALLOWED_ENTRYPOINTS:
        return

    data = read_stdin()

    if data.get("agent_id"):
        passthrough_stdin(data)
        return

    tool_name = data.get("tool_name", "")
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    project_hash = _get_project_hash()
    project_root = get_project_root()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if hook_event == "PreToolUse":
        tool_input = data.get("tool_input", {})
        input_str = _truncate(_scrub_secrets(_safe_str(tool_input)))

        observation = {
            "type": "tool_start",
            "tool": tool_name,
            "input": input_str,
            "session_id": session_id,
            "timestamp": timestamp,
        }
        _write_observation(project_hash, observation)

    elif hook_event == "PostToolUse":
        tool_output = data.get("tool_output", data.get("output", ""))
        output_str = _truncate(_scrub_secrets(_safe_str(tool_output)))

        observation = {
            "type": "tool_complete",
            "tool": tool_name,
            "output": output_str,
            "session_id": session_id,
            "timestamp": timestamp,
        }
        _write_observation(project_hash, observation)

        if tool_name == "Agent":
            _handle_agent_dispatch(data, project_root)

    _update_projects_registry(project_hash)

    if is_debug_mode():
        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            phase = "pre" if hook_event == "PreToolUse" else "post"
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] observe: {phase} tool={tool_name} project={project_hash}\n")
        except Exception:
            pass

    passthrough_stdin(data)


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
