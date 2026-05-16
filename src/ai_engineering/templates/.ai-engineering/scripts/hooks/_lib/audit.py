"""Shared canonical framework-event helpers for Python hooks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

_AIE_MARKER = ".ai-engineering"

# Sidecar overflow ceiling (spec-122-b D-122-23). Override via
# ``AIENG_EVENT_SIDECAR_BYTES`` for ops that need a different threshold.
_DEFAULT_EVENT_SIDECAR_BYTES = 3072
_SIDECAR_DIR_REL = (".ai-engineering", "state", "runtime", "event-sidecars")


def _event_sidecar_ceiling() -> int:
    raw = os.environ.get("AIENG_EVENT_SIDECAR_BYTES", "").strip()
    if not raw:
        return _DEFAULT_EVENT_SIDECAR_BYTES
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_EVENT_SIDECAR_BYTES
    if value <= 0:
        return _DEFAULT_EVENT_SIDECAR_BYTES
    return value


def maybe_offload_event(project_root: Path, event: dict) -> dict:
    """Return ``event`` or a sidecar-shrunken replacement (D-122-23).

    Stdlib-only mirror of :func:`ai_engineering.state.sidecar.maybe_offload`
    so hook scripts that import ``audit.py`` can stay free of third-party
    deps.
    """
    try:
        payload = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        return event
    ceiling = _event_sidecar_ceiling()
    if len(payload) <= ceiling:
        return event
    digest = hashlib.sha256(payload).hexdigest()
    sidecar_dir = project_root.joinpath(*_SIDECAR_DIR_REL)
    try:
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = sidecar_dir / f"{digest}.json"
        if not sidecar_path.exists():
            tmp_path = sidecar_path.with_suffix(".json.tmp")
            tmp_path.write_bytes(payload)
            os.replace(str(tmp_path), str(sidecar_path))
    except OSError:
        return event  # fail-open: keep oversized inline rather than dropping
    detail = event.get("detail") if isinstance(event, dict) else None
    summary_bits = []
    if isinstance(detail, dict):
        for key in ("operation", "tool", "skill", "agent", "error_code"):
            value = detail.get(key)
            if isinstance(value, str) and value:
                summary_bits.append(f"{key}={value}")
    summary = " ".join(summary_bits) if summary_bits else (event.get("kind") or "event")
    inline = {
        "kind": event.get("kind") or "unknown",
        "engine": event.get("engine") or "unknown",
        "component": event.get("component") or "unknown",
        "outcome": event.get("outcome") or "success",
        "timestamp": event.get("timestamp") or "",
        "sidecar_sha256": digest,
        "sidecar_size_bytes": len(payload),
        "summary": summary[:160],
    }
    for key in (
        "correlationId",
        "correlation_id",
        "session_id",
        "trace_id",
        "prev_event_hash",
    ):
        if isinstance(event, dict) and event.get(key) is not None:
            inline[key] = event[key]
    return inline


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
