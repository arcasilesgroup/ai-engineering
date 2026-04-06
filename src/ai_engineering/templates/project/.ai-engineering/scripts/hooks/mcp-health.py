#!/usr/bin/env python3
"""PreToolUse + PostToolUseFailure hook: MCP server health monitoring.

Tracks MCP server health state with exponential backoff. Blocks calls to
unhealthy servers (PreToolUse, exit 2) and marks servers unhealthy on
failure patterns (PostToolUseFailure).

Uses file locking for concurrent session safety.
"""

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import is_debug_mode, passthrough_stdin
from _lib.hook_context import get_hook_context
from _lib.observability import emit_control_outcome

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows fallback
    _fcntl: Any = None

_STATE_FILE = Path.home() / ".ai-engineering" / "state" / "mcp-health.json"
_STATE_VERSION = 1

_TTL_SECONDS = 120
_PROBE_TIMEOUT = 5
_BACKOFF_BASE = 30
_BACKOFF_MAX = 600

_MCP_TOOL_RE = re.compile(r"^mcp__([^_]+)__(.+)$")

_FAILURE_PATTERNS = re.compile(
    r"(401|403|429|503|connection\s+refused|ECONNREFUSED|timeout|ETIMEDOUT"
    r"|transport\s+error|socket\s+hang\s+up|ECONNRESET|network\s+error"
    r"|certificate|SSL|TLS|EPIPE|broken\s+pipe)",
    re.IGNORECASE,
)


def _lock_shared(handle) -> None:
    if _fcntl is None:
        return
    flock = getattr(_fcntl, "flock", None)
    lock_sh = getattr(_fcntl, "LOCK_SH", None)
    if flock is None or lock_sh is None:
        return
    flock(handle.fileno(), lock_sh)


def _lock_exclusive(handle) -> None:
    if _fcntl is None:
        return
    flock = getattr(_fcntl, "flock", None)
    lock_ex = getattr(_fcntl, "LOCK_EX", None)
    if flock is None or lock_ex is None:
        return
    flock(handle.fileno(), lock_ex)


def _unlock(handle) -> None:
    if _fcntl is None:
        return
    flock = getattr(_fcntl, "flock", None)
    lock_un = getattr(_fcntl, "LOCK_UN", None)
    if flock is None or lock_un is None:
        return
    flock(handle.fileno(), lock_un)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    """Parse ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return _now_utc()


def _extract_server_name(data: dict) -> str | None:
    """Extract MCP server name from tool_name or server field."""
    tool_name = data.get("tool_name", "")
    match = _MCP_TOOL_RE.match(tool_name)
    if match:
        return match.group(1)

    server = data.get("server", "")
    if server:
        return server

    return None


def _load_state() -> dict:
    """Load MCP health state from file with locking."""
    try:
        if not _STATE_FILE.exists():
            return {"version": _STATE_VERSION, "servers": {}}
        with open(_STATE_FILE, encoding="utf-8") as f:
            _lock_shared(f)
            try:
                state = json.load(f)
            finally:
                _unlock(f)
        if not isinstance(state, dict) or state.get("version") != _STATE_VERSION:
            return {"version": _STATE_VERSION, "servers": {}}
        return state
    except Exception:
        return {"version": _STATE_VERSION, "servers": {}}


def _save_state(state: dict) -> None:
    """Save MCP health state to file with locking."""
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            _lock_exclusive(f)
            try:
                json.dump(state, f, indent=2)
            finally:
                _unlock(f)
    except Exception:
        pass


def _get_server_state(state: dict, server_name: str) -> dict:
    """Get or create server state entry."""
    servers = state.setdefault("servers", {})
    if server_name not in servers:
        servers[server_name] = {
            "status": "healthy",
            "checkedAt": _now_iso(),
            "expiresAt": (_now_utc() + timedelta(seconds=_TTL_SECONDS)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "failureCount": 0,
            "lastError": None,
            "nextRetryAt": None,
        }
    return servers[server_name]


def _calculate_backoff(failure_count: int) -> int:
    """Exponential backoff: base * 2^(failures-1), capped at max."""
    if failure_count <= 0:
        return _BACKOFF_BASE
    delay = _BACKOFF_BASE * (2 ** (failure_count - 1))
    return min(delay, _BACKOFF_MAX)


def _probe_server(server_name: str) -> bool:
    """Probe an MCP server to check health.

    Uses environment variables for server connection info:
    - AIE_MCP_URL_<SERVER>: HTTP URL to probe
    - AIE_MCP_CMD_<SERVER>: Command to spawn for health check
    """
    env_key = server_name.upper().replace("-", "_")

    url = os.environ.get(f"AIE_MCP_URL_{env_key}")
    if url:
        try:
            result = subprocess.run(
                ["curl", "-sf", "--max-time", str(_PROBE_TIMEOUT), url],
                capture_output=True,
                timeout=_PROBE_TIMEOUT + 2,
            )
            return result.returncode == 0
        except Exception:
            return False

    cmd = os.environ.get(f"AIE_MCP_CMD_{env_key}")
    if cmd:
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                timeout=_PROBE_TIMEOUT,
            )
            return result.returncode == 0
        except Exception:
            return False

    return True


def _attempt_reconnect(server_name: str) -> bool:
    """Attempt to reconnect an MCP server using env-configured command."""
    env_key = server_name.upper().replace("-", "_")
    reconnect_cmd = os.environ.get(f"AIE_MCP_RECONNECT_{env_key}")
    if not reconnect_cmd:
        return False
    try:
        result = subprocess.run(
            reconnect_cmd.split(),
            capture_output=True,
            timeout=_PROBE_TIMEOUT + 5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _emit_health_change(
    project_root: Path,
    server_name: str,
    old_status: str,
    new_status: str,
    error: str = "",
) -> None:
    """Emit a canonical control outcome for MCP health changes."""
    emit_control_outcome(
        project_root,
        category="platform",
        control="mcp-health",
        component="hook.mcp-health",
        outcome="failure" if new_status == "unhealthy" else "success",
        source="hook",
        metadata={
            "server": server_name,
            "old_status": old_status,
            "new_status": new_status,
            "error": error,
        },
    )


def _handle_pre_tool_use(data: dict, server_name: str, project_root: Path) -> None:
    """Handle PreToolUse: check server health, probe if needed."""
    state = _load_state()
    server = _get_server_state(state, server_name)
    now = _now_utc()

    if server["status"] == "healthy":
        expires_at = _parse_iso(server["expiresAt"])
        if now < expires_at:
            passthrough_stdin(data)
            return

        is_healthy = _probe_server(server_name)
        if is_healthy:
            server["checkedAt"] = _now_iso()
            server["expiresAt"] = (now + timedelta(seconds=_TTL_SECONDS)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            _save_state(state)
            passthrough_stdin(data)
            return
        else:
            old_status = server["status"]
            server["status"] = "unhealthy"
            server["failureCount"] = server.get("failureCount", 0) + 1
            backoff = _calculate_backoff(server["failureCount"])
            server["nextRetryAt"] = (now + timedelta(seconds=backoff)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            server["checkedAt"] = _now_iso()
            server["lastError"] = "probe failed"
            _save_state(state)
            _emit_health_change(project_root, server_name, old_status, "unhealthy", "probe failed")

    if server["status"] == "unhealthy":
        next_retry = server.get("nextRetryAt")
        if next_retry:
            retry_at = _parse_iso(next_retry)
            if now < retry_at:
                fail_open = os.environ.get("AIE_MCP_HEALTH_FAIL_OPEN") == "1"
                if fail_open:
                    passthrough_stdin(data)
                    return
                feedback = {
                    "decision": "block",
                    "reason": (
                        f"MCP server '{server_name}' is unhealthy. "
                        f"Next retry at {next_retry}. "
                        "Set AIE_MCP_HEALTH_FAIL_OPEN=1 to bypass."
                    ),
                }
                sys.stdout.write(json.dumps(feedback))
                sys.stdout.flush()
                sys.exit(2)

        is_healthy = _probe_server(server_name)
        if is_healthy:
            old_status = server["status"]
            server["status"] = "healthy"
            server["failureCount"] = 0
            server["lastError"] = None
            server["nextRetryAt"] = None
            server["checkedAt"] = _now_iso()
            server["expiresAt"] = (now + timedelta(seconds=_TTL_SECONDS)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            _save_state(state)
            _emit_health_change(project_root, server_name, old_status, "healthy")
            passthrough_stdin(data)
            return
        else:
            server["failureCount"] = server.get("failureCount", 0) + 1
            backoff = _calculate_backoff(server["failureCount"])
            server["nextRetryAt"] = (now + timedelta(seconds=backoff)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            server["checkedAt"] = _now_iso()
            server["lastError"] = "probe failed after retry"
            _save_state(state)

            fail_open = os.environ.get("AIE_MCP_HEALTH_FAIL_OPEN") == "1"
            if fail_open:
                passthrough_stdin(data)
                return
            feedback = {
                "decision": "block",
                "reason": (
                    f"MCP server '{server_name}' is unhealthy (probe failed). "
                    f"Backoff: {backoff}s. Set AIE_MCP_HEALTH_FAIL_OPEN=1 to bypass."
                ),
            }
            sys.stdout.write(json.dumps(feedback))
            sys.stdout.flush()
            sys.exit(2)


def _handle_post_tool_use_failure(data: dict, server_name: str, project_root: Path) -> None:
    """Handle PostToolUseFailure: detect failure, mark unhealthy, attempt reconnect."""
    error_str = ""
    tool_output = data.get("tool_output", data.get("output", data.get("error", "")))
    if isinstance(tool_output, dict):
        error_str = json.dumps(tool_output)
    elif isinstance(tool_output, str):
        error_str = tool_output
    else:
        error_str = str(tool_output)

    if not _FAILURE_PATTERNS.search(error_str):
        return

    state = _load_state()
    server = _get_server_state(state, server_name)
    now = _now_utc()

    old_status = server["status"]
    server["status"] = "unhealthy"
    server["failureCount"] = server.get("failureCount", 0) + 1
    server["lastError"] = error_str[:500]
    server["checkedAt"] = _now_iso()
    backoff = _calculate_backoff(server["failureCount"])
    server["nextRetryAt"] = (now + timedelta(seconds=backoff)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _save_state(state)

    if old_status != "unhealthy":
        _emit_health_change(project_root, server_name, old_status, "unhealthy", error_str[:200])

    reconnected = _attempt_reconnect(server_name)
    if reconnected:
        server["status"] = "healthy"
        server["failureCount"] = 0
        server["lastError"] = None
        server["nextRetryAt"] = None
        server["checkedAt"] = _now_iso()
        server["expiresAt"] = (now + timedelta(seconds=_TTL_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _save_state(state)
        _emit_health_change(
            project_root, server_name, "unhealthy", "healthy", "reconnect succeeded"
        )


def main() -> None:
    ctx = get_hook_context()

    server_name = _extract_server_name(ctx.data)
    if not server_name:
        passthrough_stdin(ctx.data)
        return

    if ctx.event_name == "PreToolUse":
        _handle_pre_tool_use(ctx.data, server_name, ctx.project_root)
    elif ctx.event_name == "PostToolUseFailure":
        _handle_post_tool_use_failure(ctx.data, server_name, ctx.project_root)
    else:
        passthrough_stdin(ctx.data)

    if is_debug_mode():
        debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            timestamp = _now_iso()
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] mcp-health: event={ctx.event_name} server={server_name}\n")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
    except Exception:
        pass
    sys.exit(0)
