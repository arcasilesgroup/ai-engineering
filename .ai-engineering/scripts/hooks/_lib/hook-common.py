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
  * get_session_id()                       -> str|None  (Claude/Antigravity env)
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
    {"claude_code", "codex", "antigravity", "copilot", "ai_engineering"}
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
        # spec-118 memory layer
        "memory_event",
        # spec-119 evaluation layer
        "eval_run",
        # spec-122 Phase C governance — OPA policy_decision
        "policy_decision",
        # spec-123 D-123-26 retention layer
        "retention_applied",
        # spec-139 M2 host preflight (D-139-02). Emitted by
        # ``ai_engineering.adapters.host.probe`` when a skill consults the
        # host before dispatch.
        "host_capacity",
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
# 5. get_session_id -- Claude or Antigravity env, else None
# ---------------------------------------------------------------------------


_SESSION_POINTER_REL = Path(".ai-engineering") / "state" / "runtime" / "session-pointer.json"


def _read_session_pointer() -> str | None:
    """Return the session id persisted at SessionStart, or None (D-190-01).

    ``CLAUDE_SESSION_ID`` is usually unset on the hot path, so the
    ``runtime-session-start`` hook stamps a durable
    ``session-pointer.json``. This reads it back through the same
    project-root resolver used by every other helper here. Stdlib-only,
    never raises — any miss / corruption degrades to None.

    Best-effort only: on a worktree shared by concurrent sessions the
    pointer names whichever session started last, so it is a FALLBACK —
    the current invocation's own session id (env or stdin/ctx) is
    authoritative and always preferred (FINDING 3).
    """
    try:
        path = _resolve_project_root() / _SESSION_POINTER_REL
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    session_id = payload.get("session_id")
    return session_id if isinstance(session_id, str) and session_id else None


def get_session_id(current: str | None = None) -> str | None:
    """Resolve the session id for the CURRENT invocation, else None.

    Resolution order (FINDING 3 — the current invocation's own id wins over
    the shared pointer so concurrent sessions on one worktree are not
    misattributed):

    1. ``CLAUDE_SESSION_ID`` / ``ANTIGRAVITY_SESSION_ID`` env vars
       (authoritative when present);
    2. ``current`` — the session id carried by this invocation's own
       stdin / ctx, threaded in by hot-path emit sites that have it;
    3. the durable ``session-pointer.json`` stamped at SessionStart
       (D-190-01 part 2) — a best-effort FALLBACK only;
    4. else None.
    """
    return (
        os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("ANTIGRAVITY_SESSION_ID")
        or current
        or _read_session_pointer()
        or None
    )


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
    # Sidecar overflow (spec-122-b D-122-23): events whose serialised
    # bytes exceed AIENG_EVENT_SIDECAR_BYTES (default 3 KB) are offloaded
    # to ``RUNTIME_DIR(project_root) / "event-sidecars" / <sha256>.json``
    # (canonical ``.ai-engineering/runtime/event-sidecars/``) and the
    # inline NDJSON line carries only hash + summary. Keeps the
    # cross-IDE concurrent append safely under POSIX_BUF.
    #
    # Spec-126 T-3.4: ``maybe_offload_event`` does NOT mutate the
    # shared chain file (writes only to the per-event sidecar named
    # by content hash) so it stays OUTSIDE the lock. The hash compute
    # (``_read_prev_event_hash``) and the actual append on the chain
    # file move INSIDE the lock to prevent the TOCTOU race.
    try:
        from _lib.audit import maybe_offload_event  # local import; stdlib-only

        payload = maybe_offload_event(project_root, payload)
    except Exception:  # fail-open: never block emit
        pass

    # Spec-126 D-126-05 / T-3.4: hash compute + write under
    # ``with_lock_retry``. Lazy import keeps cold-start hooks fast.
    # Fallback to file-path load when ``_lib`` is not on ``sys.path``
    # (this module is sometimes loaded via ``spec_from_file_location``
    # under a different package name in tests / hook bootstraps).
    with_lock_retry = _load_with_lock_retry()

    try:
        with with_lock_retry(project_root, "framework-events") as _locked:
            payload["prev_event_hash"] = _read_prev_event_hash(path)
            line = json.dumps(payload, sort_keys=True, default=str)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except OSError as exc:
        logger.exception("hook-common: failed to append event: %s", exc)
        return False
    return True


def _load_with_lock_retry():
    """Resolve ``with_lock_retry`` even when ``_lib`` is not on ``sys.path``.

    The hook-common module is sometimes loaded via
    ``spec_from_file_location`` (tests, ad-hoc hook bootstrap shims)
    under a synthetic package name like ``aieng_hook_common``. In that
    case the canonical ``from _lib.locked_append import with_lock_retry``
    raises ``ModuleNotFoundError``. Fall back to a temporary
    ``sys.path`` prepend so the canonical package import resolves
    cleanly, then restore ``sys.path`` to avoid leaking state into
    other tests / hook entry points.
    """
    import importlib

    try:
        return importlib.import_module("_lib.locked_append").with_lock_retry
    except ModuleNotFoundError:
        # Prepend the hooks parent dir so ``_lib`` resolves as a normal
        # implicit-namespace package; do NOT mutate ``sys.modules`` with
        # a synthetic ``_lib`` (would shadow downstream loads of sibling
        # modules like ``_lib.hook_common`` and ``_lib.observability``).
        import contextlib

        hooks_parent = str(Path(__file__).parent.parent)
        added = hooks_parent not in sys.path
        if added:
            sys.path.insert(0, hooks_parent)
        try:
            module = importlib.import_module("_lib.locked_append")
            return module.with_lock_retry
        finally:
            if added:
                with contextlib.suppress(ValueError):
                    sys.path.remove(hooks_parent)


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


def _record_error_coalesced(
    project_root: Path,
    *,
    component: str,
    error_code: str,
    summary: str,
    session_id: str | None,
) -> dict:
    """Route an error/integrity emit through the storm coalescer (spec-190 D-190-02).

    Returns the ``record_error`` verdict augmented with the ``fingerprint``.
    Fail-open: any import/compute failure yields a first-occurrence verdict so
    no incident is dropped and the audit chain keeps its entry.
    """
    try:
        from _lib.runtime_state import error_fingerprint, record_error

        fingerprint = error_fingerprint(component, error_code, session_id, summary)
        verdict = record_error(
            project_root,
            fingerprint,
            component=component,
            error_code=error_code,
            summary=summary,
        )
        verdict["fingerprint"] = fingerprint
    except Exception:
        return {
            "emit_full": True,
            "occurrences": 1,
            "storm_triggered": False,
            "is_rollup": False,
            "fingerprint": "",
        }
    else:
        return verdict


def _emit_error_storm_control(
    project_root: Path,
    *,
    component: str,
    error_code: str,
    fingerprint: str,
    occurrences: int,
    hook_kind: str,
) -> None:
    """Emit ONE control_outcome storm alarm (spec-190 D-190-02).

    Fired the first time repeats cross ``AIENG_ERROR_STORM_THRESHOLD`` so the
    operator sees the storm without scanning the raw NDJSON. Fail-open.
    """
    try:
        # FINDING 6: match the accompanying framework_error engine (env or
        # claude_code) instead of the divergent "ai_engineering" so the two
        # hook-side dual-writer events carry a consistent engine.
        engine = os.environ.get("AIENG_HOOK_ENGINE") or "claude_code"
        event = {
            "kind": "control_outcome",
            "engine": engine,
            "frameworkVersion": _resolve_framework_version(project_root),
            "timestamp": _now_iso(),
            "component": component,
            "outcome": "failure",
            "correlationId": get_correlation_id(),
            "schemaVersion": "1.0",
            "project": project_root.name,
            "source": "hook",
            "detail": {
                "category": "observability",
                "control": "framework_error_storm",
                "error_code": error_code,
                "fingerprint": fingerprint,
                "occurrences": occurrences,
                "hook_kind": hook_kind,
            },
        }
        session_id = get_session_id()
        if session_id:
            event["sessionId"] = session_id
        emit_event(project_root, event)
    except Exception:
        pass


def _emit_hook_error(*, component: str, hook_kind: str, exc: BaseException) -> None:
    """Append the framework_error event when main_fn raised (spec-112 D-112-04).

    Repeats are coalesced via the spec-190 storm coalescer: the first crash in
    a window emits the full event, subsequent identical crashes are suppressed
    but a rollup carrying ``detail.occurrences`` is emitted on the threshold
    cadence, and a storm alarm fires once per window.
    """
    try:
        project_root = _resolve_project_root()
        engine = os.environ.get("AIENG_HOOK_ENGINE") or "claude_code"
        summary = str(exc)[:200]
        session_id = get_session_id()
        error_code = "hook_execution_failed"
        verdict = _record_error_coalesced(
            project_root,
            component=component,
            error_code=error_code,
            summary=summary,
            session_id=session_id,
        )
        if verdict.get("emit_full", True):
            detail: dict = {
                "error_code": error_code,
                "summary": summary,
                "hook_kind": hook_kind,
            }
            if verdict.get("is_rollup"):
                detail["occurrences"] = verdict.get("occurrences")
            event = {
                "kind": "framework_error",
                "engine": engine,
                "frameworkVersion": _resolve_framework_version(project_root),
                "timestamp": _now_iso(),
                "component": component,
                "outcome": "failure",
                "correlationId": get_correlation_id(),
                "schemaVersion": "1.0",
                "project": project_root.name,
                "source": "hook",
                "detail": detail,
            }
            if session_id:
                event["sessionId"] = session_id
            emit_event(project_root, event)
        if verdict.get("storm_triggered"):
            _emit_error_storm_control(
                project_root,
                component=component,
                error_code=error_code,
                fingerprint=verdict.get("fingerprint", ""),
                occurrences=verdict.get("occurrences", 0),
                hook_kind=hook_kind,
            )
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
    """Log integrity mismatch as ``framework_error`` regardless of mode.

    Routed through the spec-190 storm coalescer so a mis-pinned manifest (which
    re-fires on every hook invocation, historically ~15k lines) collapses into
    one full event + periodic rollups + a single storm alarm per window.
    """
    try:
        project_root = _resolve_project_root()
        engine = os.environ.get("AIENG_HOOK_ENGINE") or "claude_code"
        summary = reason[:200]
        session_id = get_session_id()
        error_code = "hook_integrity_violation"
        verdict = _record_error_coalesced(
            project_root,
            component=component,
            error_code=error_code,
            summary=summary,
            session_id=session_id,
        )
        if verdict.get("emit_full", True):
            detail: dict = {
                "error_code": error_code,
                "summary": summary,
                "hook_kind": hook_kind,
                "mode": mode,
            }
            if verdict.get("is_rollup"):
                detail["occurrences"] = verdict.get("occurrences")
            event = {
                "kind": "framework_error",
                "engine": engine,
                "frameworkVersion": _resolve_framework_version(project_root),
                "timestamp": _now_iso(),
                "component": component,
                "outcome": "failure",
                "correlationId": get_correlation_id(),
                "schemaVersion": "1.0",
                "project": project_root.name,
                "source": "hook",
                "detail": detail,
            }
            if session_id:
                event["sessionId"] = session_id
            emit_event(project_root, event)
        if verdict.get("storm_triggered"):
            _emit_error_storm_control(
                project_root,
                component=component,
                error_code=error_code,
                fingerprint=verdict.get("fingerprint", ""),
                occurrences=verdict.get("occurrences", 0),
                hook_kind=hook_kind,
            )
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
        # spec-131 sub-004 T-4.C: surface the reason on stderr BEFORE
        # exiting so operators see a one-line actionable signal. Distinct
        # exit code 3 separates integrity drift from injection deny
        # (exit 2). Contract is documented inline:
        #   0 = ok
        #   2 = injection deny (prompt-injection-guard semantics)
        #   3 = integrity violation (hooks-manifest sha256 mismatch
        #       or unenrolled hook in enforce mode)
        reason = integrity_reason or "manifest mismatch"
        sys.stderr.write(
            f"[hook-integrity] refusing to run {hook_kind}: {reason}\n"
            "[hook-integrity] regenerate with: python3 "
            ".ai-engineering/scripts/regenerate-hooks-manifest.py\n"
        )
        sys.stderr.flush()
        sys.exit(3)

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


def _resolve_framework_version(project_root: Path) -> str:
    """Resolve the pinned framework version for inline event stamping (FINDING 5).

    Reuses the stdlib ``_read_framework_version`` resolver from the sibling
    ``_lib/observability`` hook module (stdlib-only — NOT the pip package) so
    the hot-path ``framework_error`` / ``control_outcome`` events this module
    emits inline carry ``frameworkVersion`` like every other framework event.
    Fail-open: any import / resolution failure degrades to the ``"0.0.0"``
    sentinel so an error/control emit is never blocked.
    """
    try:
        from _lib.observability import _read_framework_version

        return _read_framework_version(project_root)
    except Exception:
        return "0.0.0"


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
