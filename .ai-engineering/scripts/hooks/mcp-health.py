#!/usr/bin/env python3
"""PreToolUse + PostToolUseFailure hook: MCP server health monitoring.

Tracks MCP server health state with exponential backoff. Blocks calls to
unhealthy servers (PreToolUse, exit 2) and marks servers unhealthy on
failure patterns (PostToolUseFailure).

Uses file locking for concurrent session safety.
"""

import contextlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import is_debug_mode, passthrough_stdin
from _lib.hook_common import run_hook_safe
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

# spec-107 D-107-01: conservative allowlist of MCP server binaries.
# Anything outside this set requires an active risk-acceptance entry in
# ``decision-store.json`` keyed on ``mcp-binary-<binary>``. The escape
# hatch reuses the spec-105 risk-accept lifecycle so exceptions remain
# auditable, time-bounded, and listable via ``ai-eng risk list``.
_ALLOWED_MCP_BINARIES: frozenset[str] = frozenset(
    {"npx", "node", "python3", "bunx", "deno", "cargo", "go", "dotnet"}
)


def _lock_shared(handle) -> None:
    if _fcntl is None:
        return
    _fcntl.flock(handle.fileno(), _fcntl.LOCK_SH)


def _lock_exclusive(handle) -> None:
    if _fcntl is None:
        return
    _fcntl.flock(handle.fileno(), _fcntl.LOCK_EX)


def _unlock(handle) -> None:
    if _fcntl is None:
        return
    _fcntl.flock(handle.fileno(), _fcntl.LOCK_UN)


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


def _decision_store_path(project_root: Path) -> Path:
    """Resolve the project decision-store.json location."""
    return project_root / ".ai-engineering" / "state" / "decision-store.json"


def _parse_decision_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp from a decision-store entry.

    Returns ``None`` for missing or unparseable values so downstream callers
    can treat the entry as non-expiring (matches Pydantic ``Decision.expires_at``
    semantics where ``None`` means perpetual).
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _find_active_mcp_binary_acceptance(
    project_root: Path,
    binary: str,
    *,
    now: datetime | None = None,
) -> dict | None:
    """Look up an active risk-acceptance for a given MCP binary.

    Mirrors the spec-105 ``find_active_risk_acceptance`` lookup primitive
    (``policy/checks/_accept_lookup.finding_is_accepted``) but operates
    directly on the raw decision-store JSON because the hook intentionally
    avoids importing ``ai_engineering.*`` (stdlib-only contract per
    ``_lib/observability.py`` header).

    A match must satisfy ALL of:
    - ``finding_id`` (or alias ``findingId``) equals ``mcp-binary-<binary>``
    - ``status`` equals ``"active"`` (case-insensitive)
    - ``risk_category`` (or ``riskCategory``) equals ``"risk-acceptance"``
    - ``expires_at`` (or ``expiresAt``) is absent OR strictly greater than ``now``

    Returns the matching decision dict, or ``None`` if no acceptance is active.
    Failures opening/parsing the store are treated as "no acceptance" — the
    hook never crashes the host on malformed state.
    """
    reference = now or _now_utc()
    canonical_finding = f"mcp-binary-{binary}"
    store_path = _decision_store_path(project_root)
    if not store_path.exists():
        return None
    try:
        raw = store_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        return None
    for entry in decisions:
        if not isinstance(entry, dict):
            continue
        finding_id = entry.get("finding_id") or entry.get("findingId")
        if finding_id != canonical_finding:
            continue
        status = (entry.get("status") or "").lower()
        if status != "active":
            continue
        risk_category = (entry.get("risk_category") or entry.get("riskCategory") or "").lower()
        if risk_category != "risk-acceptance":
            continue
        expires_at = _parse_decision_timestamp(entry.get("expires_at") or entry.get("expiresAt"))
        if expires_at is not None and expires_at <= reference:
            continue
        return entry
    return None


def _emit_binary_decision(
    project_root: Path,
    *,
    server_name: str,
    binary: str,
    outcome: str,
    control: str,
    metadata: dict | None = None,
) -> None:
    """Emit a canonical control_outcome event for binary-allowlist decisions."""
    detail: dict = {"server": server_name, "binary": binary}
    if metadata:
        detail.update(metadata)
    # Telemetry must never crash the hook. Swallow defensively.
    with contextlib.suppress(Exception):
        emit_control_outcome(
            project_root,
            category="mcp-sentinel",
            control=control,
            component="hook.mcp-health",
            outcome=outcome,
            source="hook",
            metadata=detail,
        )


def _binary_allowed(
    binary: str,
    *,
    project_root: Path | None = None,
    server_name: str | None = None,
    cmd_kind: str = "probe",
) -> bool:
    """Return True when ``binary`` may be invoked by the MCP-health hook.

    Resolution order:
    1. ``binary in _ALLOWED_MCP_BINARIES`` → permit silently.
    2. Active risk-acceptance ``mcp-binary-<binary>`` in decision-store →
       permit + emit ``binary-allowed-via-dec`` telemetry event.
    3. Otherwise → deny + log WARN with the canonical remediation hint
       (spec-107 D-107-01).
    """
    if binary in _ALLOWED_MCP_BINARIES:
        return True
    if project_root is not None:
        decision = _find_active_mcp_binary_acceptance(project_root, binary)
        if decision is not None:
            dec_id = decision.get("id") or decision.get("decision_id")
            _emit_binary_decision(
                project_root,
                server_name=server_name or "<unknown>",
                binary=binary,
                outcome="success",
                control="binary-allowed-via-dec",
                metadata={
                    "dec_id": dec_id,
                    "cmd_kind": cmd_kind,
                },
            )
            return True
    sys.stderr.write(
        f"WARN [mcp-health] MCP cmd binary '{binary}' not in allowlist. "
        f"To enable, run: ai-eng risk accept --finding-id mcp-binary-{binary} "
        '--severity low --justification "..." --spec spec-107 --follow-up "..."\n'
    )
    if project_root is not None:
        _emit_binary_decision(
            project_root,
            server_name=server_name or "<unknown>",
            binary=binary,
            outcome="failure",
            control="binary-rejected",
            metadata={"cmd_kind": cmd_kind},
        )
    return False


def _probe_server(server_name: str, project_root: Path | None = None) -> bool:
    """Probe an MCP server to check health.

    Uses environment variables for server connection info:
    - AIE_MCP_URL_<SERVER>: HTTP URL to probe
    - AIE_MCP_CMD_<SERVER>: Command to spawn for health check

    spec-107 D-107-01: ``AIE_MCP_CMD_<SERVER>`` first token must be in
    ``_ALLOWED_MCP_BINARIES`` OR have an active risk-acceptance entry
    keyed on ``mcp-binary-<binary>``. Otherwise the probe is rejected.
    """
    env_key = server_name.upper().replace("-", "_")

    url = os.environ.get(f"AIE_MCP_URL_{env_key}")
    if url:
        if not re.match(r"^https?://[^\s;|&$`]+$", url):
            return False
        try:
            result = subprocess.run(
                ["curl", "-sf", "--max-time", str(_PROBE_TIMEOUT), "--", url],
                capture_output=True,
                timeout=_PROBE_TIMEOUT + 2,
            )
            return result.returncode == 0
        except Exception:
            return False

    cmd = os.environ.get(f"AIE_MCP_CMD_{env_key}")
    if cmd:
        try:
            args = shlex.split(cmd)
        except ValueError:
            return False
        if not args:
            return False
        if not _binary_allowed(
            args[0],
            project_root=project_root,
            server_name=server_name,
            cmd_kind="probe",
        ):
            return False
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                timeout=_PROBE_TIMEOUT,
            )
            return result.returncode == 0
        except Exception:
            return False

    return True


def _attempt_reconnect(server_name: str, project_root: Path | None = None) -> bool:
    """Attempt to reconnect an MCP server using env-configured command.

    spec-107 D-107-01: same allowlist + risk-accept escape applied to
    ``AIE_MCP_RECONNECT_<SERVER>`` first token.
    """
    env_key = server_name.upper().replace("-", "_")
    reconnect_cmd = os.environ.get(f"AIE_MCP_RECONNECT_{env_key}")
    if not reconnect_cmd:
        return False
    try:
        args = shlex.split(reconnect_cmd)
    except ValueError:
        return False
    if not args:
        return False
    if not _binary_allowed(
        args[0],
        project_root=project_root,
        server_name=server_name,
        cmd_kind="reconnect",
    ):
        return False
    try:
        result = subprocess.run(
            args,
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

        is_healthy = _probe_server(server_name, project_root)
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

        is_healthy = _probe_server(server_name, project_root)
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

    reconnected = _attempt_reconnect(server_name, project_root)
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
    run_hook_safe(main, component="hook.mcp-health", hook_kind="pre-tool-use")
