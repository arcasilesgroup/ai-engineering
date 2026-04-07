"""Shared canonical framework-event helpers for Python hooks."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_AIE_MARKER = ".ai-engineering"


def get_project_root() -> Path:
    if env_dir := os.environ.get("CLAUDE_PROJECT_DIR"):
        p = Path(env_dir)
        if p.is_dir():
            return p
    cwd = Path.cwd()
    current = cwd
    for _ in range(20):
        if (current / _AIE_MARKER).is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return cwd


def get_git_metadata(project_root: Path) -> tuple[str, str]:
    def _run(cmd: list[str]) -> str:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(project_root), timeout=3
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]), _run(
        ["git", "rev-parse", "--short", "HEAD"]
    )


def get_session_id() -> str:
    return os.environ.get("CLAUDE_SESSION_ID", "default")


def get_hook_event_name() -> str:
    return os.environ.get("CLAUDE_HOOK_EVENT_NAME", "")


def is_debug_mode() -> bool:
    return os.environ.get("AIENG_TELEMETRY_DEBUG") == "1"


def read_stdin(max_bytes: int = 1_048_576) -> dict:
    import sys

    try:
        raw = sys.stdin.read(max_bytes)
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        return {}


def passthrough_stdin(data: dict) -> None:
    import sys

    try:
        engine = os.environ.get("AIENG_HOOK_ENGINE", "").strip()
        # Codex validates hook stdout as structured hook output, so echoing the
        # input payload back is invalid there. Other providers keep the legacy
        # behavior until their adapters are migrated.
        if engine == "codex":
            return
        sys.stdout.write(json.dumps(data, separators=(",", ":")))
        sys.stdout.flush()
    except Exception:
        pass
