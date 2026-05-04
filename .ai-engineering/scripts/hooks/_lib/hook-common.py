"""Sealed shared lib for Python hooks (spec-112 G-12, T-1.8).

**Sealed contract**: this module imports ONLY from the Python stdlib
(`pathlib`, `json`, `hashlib`, `time`, `uuid`, `os`, `sys`, `logging`).
It must NOT import from `ai_engineering.*` -- circular imports would
otherwise pull state writers into hook scripts that intentionally run
outside the package install (per D-112-04 + R-9 mitigation).

The schema validator delegates to a stdlib mirror of
`ai_engineering.state.event_schema.validate_event_schema` so the wire
contract stays in sync without crossing the seal.

Six functions per G-12:
  * emit_event(project_root, event)        -> bool      (G-12, write or refuse)
  * read_stdin_json()                      -> dict      (parse stdin, never raise)
  * compute_event_hash(event_dict)         -> str       (canonical sha256)
  * get_correlation_id()                   -> str       (env or uuid4)
  * get_session_id()                       -> str|None  (Claude/Gemini env)
  * validate_event_schema(event)           -> bool      (delegates to validator)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import cast

logger = logging.getLogger("aieng.hook_common")

# Spec-110 D-110-03: chain pointer lives at root of the JSON object on disk.
_PREV_HASH_KEYS: frozenset[str] = frozenset({"prev_event_hash", "prevEventHash"})

# Spec-112 D-112-02: required-at-root keys + `engine` enum.
_REQUIRED_KEYS: tuple[str, ...] = (
    "kind",
    "engine",
    "timestamp",
    "component",
    "outcome",
    "correlationId",
    "schemaVersion",
    "project",
)
_ALLOWED_ENGINES: frozenset[str] = frozenset(
    {"claude_code", "codex", "gemini", "copilot", "ai_engineering"}
)
_ENGINE_ALIASES: dict[str, str] = {"github_copilot": "copilot"}
_ALLOWED_KINDS: frozenset[str] = frozenset(
    {
        "skill_invoked",
        "agent_dispatched",
        "context_load",
        "ide_hook",
        "framework_error",
        "git_hook",
        "control_outcome",
        "framework_operation",
        "task_trace",
    }
)

_FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _normalize_engine_id(engine: str) -> str:
    return _ENGINE_ALIASES.get(engine, engine)


# ---------------------------------------------------------------------------
# 1. validate_event_schema -- mirrors src/ai_engineering/state/event_schema.py
# ---------------------------------------------------------------------------


def validate_event_schema(event: object) -> bool:
    """Return True iff event matches the unified schema (spec-112 G-4)."""
    if not isinstance(event, dict):
        return False
    event_dict = cast("dict[str, object]", event)
    for key in _REQUIRED_KEYS:
        if key not in event_dict:
            return False
        value = event_dict[key]
        if value is None or value == "":
            return False
    engine = event_dict.get("engine")
    if not isinstance(engine, str) or engine not in _ALLOWED_ENGINES:
        return False
    kind = event_dict.get("kind")
    if not isinstance(kind, str) or kind not in _ALLOWED_KINDS:
        return False
    detail = event_dict.get("detail", {})
    return isinstance(detail, dict)


# ---------------------------------------------------------------------------
# 2. compute_event_hash -- canonical sha256 with chain-pointer exclusion
# ---------------------------------------------------------------------------


def compute_event_hash(event: dict) -> str:
    """SHA-256 of the canonical-JSON form of the event.

    The chain-pointer fields are excluded so re-hashing an event that
    was written with `prev_event_hash: <hex>` produces the same digest
    as the same event without the pointer (mirrors
    `ai_engineering.state.audit_chain.compute_entry_hash`).
    """
    stripped = {k: v for k, v in event.items() if k not in _PREV_HASH_KEYS}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 3. read_stdin_json -- never raises; returns {} on failure
# ---------------------------------------------------------------------------


def read_stdin_json(max_bytes: int = 1_048_576) -> dict:
    """Parse stdin as JSON; return {} on empty or malformed input."""
    try:
        raw = sys.stdin.read(max_bytes)
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


# ---------------------------------------------------------------------------
# 4. get_correlation_id -- env first, uuid4 hex fallback
# ---------------------------------------------------------------------------


def get_correlation_id() -> str:
    """Return the active trace id or a fresh uuid4 hex (32 chars)."""
    env = os.environ.get("CLAUDE_TRACE_ID")
    if env:
        return env
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# 5. get_session_id -- Claude or Gemini env, else None
# ---------------------------------------------------------------------------


def get_session_id() -> str | None:
    """Resolve the IDE-provided session id or return None."""
    return os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("GEMINI_SESSION_ID") or None


# ---------------------------------------------------------------------------
# 6. emit_event -- validate + chain + append
# ---------------------------------------------------------------------------


def _read_prev_event_hash(path: Path) -> str | None:
    """Compute the SHA-256 of the canonical JSON of the last entry, if any."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip():
        return None
    last_line = text.strip().splitlines()[-1].strip()
    if not last_line:
        return None
    try:
        prior = json.loads(last_line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(prior, dict):
        return None
    return compute_event_hash(prior)


def _events_path(project_root: Path) -> Path:
    return project_root / _FRAMEWORK_EVENTS_REL


def emit_event(project_root: Path, event: dict) -> bool:
    """Append `event` to NDJSON if valid; return True on write, False on refusal.

    Spec-112 G-4: malformed events are refused (logged to stderr) so the
    audit stream stays trustworthy. Spec-110 D-110-03: stamps
    `prev_event_hash` at the **root** of the on-disk JSON object.
    """
    normalized_event = dict(event)
    engine = normalized_event.get("engine")
    if isinstance(engine, str):
        normalized_event["engine"] = _normalize_engine_id(engine)
    if not validate_event_schema(normalized_event):
        logger.error(
            "hook-common: refusing to emit malformed event (kind=%s engine=%s)",
            normalized_event.get("kind") if isinstance(normalized_event, dict) else None,
            normalized_event.get("engine") if isinstance(normalized_event, dict) else None,
        )
        return False
    path = _events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = normalized_event
    payload["prev_event_hash"] = _read_prev_event_hash(path)
    line = json.dumps(payload, sort_keys=True, default=str)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as exc:
        logger.error("hook-common: failed to append event: %s", exc)
        return False
    return True


# ---------------------------------------------------------------------------
# Convenience: hot-path duration timer (used by Phase 3 SLO instrumentation
# but exposed here so hooks can wrap their work without re-importing time).
# ---------------------------------------------------------------------------


def now_monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


# ---------------------------------------------------------------------------
# Convenience: shared exception-safety wrapper used by every Python hook.
# Replaces the 25-line `if __name__ == "__main__"` boilerplate that was
# copy-pasted across hook scripts.
# ---------------------------------------------------------------------------


def _emit_hook_heartbeat(
    *,
    component: str,
    hook_kind: str,
    duration_ms: int,
    outcome: str,
    budget_ms: int | None = None,
    over_budget: bool = False,
) -> None:
    """Append a hot-path heartbeat event carrying duration_ms (spec-114 G-2).

    Best-effort: any failure here is swallowed so the hook still exits 0.
    The event uses `kind: ide_hook` so existing readers (doctor, audit
    chain) treat it as a normal hook outcome record.

    Spec-115 G-1 adds `budget_ms` and `over_budget` to surface SLO breaches
    inline so downstream rollups don't have to re-derive thresholds.
    """
    try:
        project_root = _resolve_project_root()
        engine = os.environ.get("AIENG_HOOK_ENGINE") or "claude_code"
        detail: dict = {
            "hook_kind": hook_kind,
            "outcome": outcome,
            "duration_ms": duration_ms,
        }
        if budget_ms is not None:
            detail["budget_ms"] = budget_ms
            detail["over_budget"] = over_budget
        event = {
            "kind": "ide_hook",
            "engine": engine,
            "timestamp": _now_iso(),
            "component": component,
            "outcome": outcome,
            "correlationId": get_correlation_id(),
            "schemaVersion": "1.0",
            "project": project_root.name,
            "source": "hook",
            "detail": detail,
        }
        session_id = get_session_id()
        if session_id:
            event["sessionId"] = session_id
        emit_event(project_root, event)
    except Exception:
        pass


def _emit_hook_error(*, component: str, hook_kind: str, exc: BaseException) -> None:
    """Append the framework_error event when main_fn raised (spec-112 D-112-04)."""
    try:
        project_root = _resolve_project_root()
        engine = os.environ.get("AIENG_HOOK_ENGINE") or "claude_code"
        event = {
            "kind": "framework_error",
            "engine": engine,
            "timestamp": _now_iso(),
            "component": component,
            "outcome": "failure",
            "correlationId": get_correlation_id(),
            "schemaVersion": "1.0",
            "project": project_root.name,
            "source": "hook",
            "detail": {
                "error_code": "hook_execution_failed",
                "summary": str(exc)[:200],
                "hook_kind": hook_kind,
            },
        }
        session_id = get_session_id()
        if session_id:
            event["sessionId"] = session_id
        emit_event(project_root, event)
    except Exception:
        pass


# Hot-path SLO budgets (spec-114 G-2 follow-up). Heartbeats whose
# `duration_ms` exceeds the matching budget tag the event with
# `detail.over_budget = True` so `ai-eng doctor --check hot-path` and the
# offline rollups can flag regressions without re-deriving thresholds.
_HOT_PATH_BUDGET_MS: dict[str, int] = {
    "pre-tool-use": 1000,
    "post-tool-use": 1000,
    "user-prompt-submit": 1000,
    "stop": 5000,
    "subagent-stop": 1000,
    "session-start": 5000,
    "session-end": 5000,
    "pre-compact": 5000,
}
_HOT_PATH_DEFAULT_BUDGET_MS = 1000


def _hot_path_budget_ms(hook_kind: str) -> int:
    return _HOT_PATH_BUDGET_MS.get(hook_kind, _HOT_PATH_DEFAULT_BUDGET_MS)


def _verify_caller_integrity(
    *,
    component: str,
    hook_kind: str,
    script_path: Path | str | None = None,
) -> tuple[bool, str | None, str]:
    """Best-effort integrity check on the calling hook script.

    Returns ``(allowed, reason, mode)``. ``allowed`` is False only when
    the configured mode is ``enforce`` AND the manifest declares a
    different sha256 for this script (or — in enforce mode — the script
    is missing from the manifest entirely). All other paths (warn, off,
    no manifest, unenrolled hook in non-enforce, import failure) return
    True so the caller decides whether to surface the reason via telemetry.

    ``script_path`` is now passed in by ``run_hook_safe`` (resolved from
    ``__file__`` at the hook entry). Earlier versions used ``inspect.stack()``
    here, which walked the whole Python call stack on every hook invocation
    and cost 5-30 ms per call.
    """
    try:
        from _lib.integrity import (
            integrity_mode,
            verify_hook_integrity,
        )
    except Exception:  # pragma: no cover - defensive
        return True, None, "off"
    mode = integrity_mode()
    if mode == "off":
        return True, None, mode
    if script_path is None:
        # Fallback: legacy callers without explicit path. Best-effort only —
        # `inspect.stack()` is the slow path; warn-mode + skip rather than pay.
        return True, None, mode
    try:
        resolved = Path(script_path).resolve()
    except (OSError, TypeError):
        return True, None, mode
    project_root = _resolve_project_root()
    ok, reason = verify_hook_integrity(resolved, project_root)
    if ok:
        return True, None, mode
    return mode != "enforce", reason, mode


def _emit_integrity_violation(*, component: str, hook_kind: str, reason: str, mode: str) -> None:
    """Log integrity mismatch as ``framework_error`` regardless of mode."""
    try:
        project_root = _resolve_project_root()
        engine = os.environ.get("AIENG_HOOK_ENGINE") or "claude_code"
        event = {
            "kind": "framework_error",
            "engine": engine,
            "timestamp": _now_iso(),
            "component": component,
            "outcome": "failure",
            "correlationId": get_correlation_id(),
            "schemaVersion": "1.0",
            "project": project_root.name,
            "source": "hook",
            "detail": {
                "error_code": "hook_integrity_violation",
                "summary": reason[:200],
                "hook_kind": hook_kind,
                "mode": mode,
            },
        }
        session_id = get_session_id()
        if session_id:
            event["sessionId"] = session_id
        emit_event(project_root, event)
    except Exception:
        pass


def run_hook_safe(
    main_fn,
    *,
    component: str,
    hook_kind: str,
    script_path: Path | str | None = None,
) -> None:
    """Run `main_fn` with hot-path instrumentation; always exit 0.

    Spec-112 T-1.10 introduced this wrapper to centralise the fail-open
    boilerplate. Spec-114 G-2 extends it with `time.perf_counter()`
    measurement and a heartbeat event carrying `detail.duration_ms` so
    `ai-eng doctor --check hot-path` can compute rolling p95 per hook.

    Spec-115 G-1 layers two extras on top:
      * Hot-path budget tagging (`detail.over_budget`) using the
        per-hook-kind table in ``_HOT_PATH_BUDGET_MS``.
      * Hook script integrity verification against
        ``hooks-manifest.json``. Mode is governed by env
        ``AIENG_HOOK_INTEGRITY_MODE`` (warn|enforce|off).

    Hooks may exit non-zero intentionally via `SystemExit` (e.g.
    injection-guard deny); we re-raise without writing the heartbeat
    so deny semantics stay legible to operators reading the NDJSON.

    Imported lazily by hooks; the seal contract still holds because
    this function performs no `ai_engineering.*` imports.
    """
    integrity_ok, integrity_reason, integrity_mode_val = _verify_caller_integrity(
        component=component, hook_kind=hook_kind, script_path=script_path
    )
    if integrity_reason is not None:
        _emit_integrity_violation(
            component=component,
            hook_kind=hook_kind,
            reason=integrity_reason,
            mode=integrity_mode_val,
        )
    if not integrity_ok:
        # Enforce-mode mismatch: refuse execution. Exit 2 mirrors the
        # injection-guard deny semantics so operators can grep for it.
        sys.exit(2)

    start = time.perf_counter()
    outcome = "success"
    raised: BaseException | None = None
    try:
        main_fn()
    except SystemExit:
        # Intentional exit (e.g. injection deny) — bypass heartbeat
        # so the explicit exit code is preserved without an extra event.
        raise
    except Exception as exc:
        outcome = "failure"
        raised = exc
    duration_ms = max(0, round((time.perf_counter() - start) * 1000))
    budget_ms = _hot_path_budget_ms(hook_kind)
    over_budget = duration_ms > budget_ms
    _emit_hook_heartbeat(
        component=component,
        hook_kind=hook_kind,
        duration_ms=duration_ms,
        outcome=outcome,
        budget_ms=budget_ms,
        over_budget=over_budget,
    )
    if raised is not None:
        _emit_hook_error(component=component, hook_kind=hook_kind, exc=raised)
    sys.exit(0)


def _resolve_project_root() -> Path:
    """Walk up from CWD looking for `.ai-engineering` marker; honor env override."""
    if env_dir := os.environ.get("CLAUDE_PROJECT_DIR"):
        candidate = Path(env_dir)
        if candidate.is_dir():
            return candidate
    current = Path.cwd()
    for _ in range(20):
        if (current / ".ai-engineering").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd()


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 form used by the schema."""
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "compute_event_hash",
    "emit_event",
    "get_correlation_id",
    "get_session_id",
    "now_monotonic_ms",
    "read_stdin_json",
    "run_hook_safe",
    "validate_event_schema",
]
