"""Shared audit-log append for all Python hooks."""

import json
import os
import subprocess
from datetime import UTC, datetime
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


def get_audit_log(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "audit-log.ndjson"


def append_audit_event(audit_log: Path, event: dict, project_root: Path | None = None) -> None:
    try:
        if project_root is None:
            project_root = get_project_root()
        branch, commit = get_git_metadata(project_root)
        enriched = {
            "actor": event.get("actor", "ai"),
            "branch": event.get("branch") or branch,
            "commit_sha": event.get("commit_sha") or commit,
            "detail": event.get("detail", {}),
            "event": event["event"],
            "source": "hook",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for k, v in event.items():
            if k not in ("source", "timestamp", "branch", "commit_sha") and k not in enriched:
                enriched[k] = v
        audit_log = Path(audit_log)
        audit_log.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(enriched, separators=(",", ":")) + "\n")
    except Exception:
        pass


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
        sys.stdout.write(json.dumps(data, separators=(",", ":")))
        sys.stdout.flush()
    except Exception:
        pass
