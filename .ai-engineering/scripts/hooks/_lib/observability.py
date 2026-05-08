"""Stdlib-only framework observability for hook scripts.

Drop-in replacement for ai_engineering.state.observability that uses ONLY
Python stdlib.  Produces identical NDJSON output (sort_keys=True, same
schema fields, same datetime format).

Zero imports from ai_engineering.* -- hooks can run without pip install.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

FRAMEWORK_EVENT_SCHEMA_VERSION = "1.0"
_AI_ENGINEERING_DIR = Path(".ai-engineering")
FRAMEWORK_EVENTS_REL = _AI_ENGINEERING_DIR / "state" / "framework-events.ndjson"
_ACTIVE_WORK_PLANE_POINTER = _AI_ENGINEERING_DIR / "specs" / "active-work-plane.json"
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
    }
)

_DEGRADED_HOSTS: frozenset[str] = frozenset({"codex"})
_SECRET_RE = re.compile(
    r"(?i)(api_key|token|secret|password|authorization|credentials|auth)"
    r"([\"'\s:=]+)"
    r"[^\s\"',;]{4,}",
)
_MAX_SUMMARY_LEN = 200


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _json_serializer(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _normalize_skill_name(skill_name: str) -> str:
    normalized = skill_name.strip().lower()
    if not normalized.startswith("ai-"):
        normalized = f"ai-{normalized}"
    return normalized


def _normalize_agent_name(agent_name: str) -> str:
    normalized = agent_name.strip().lower()
    normalized = normalized.removeprefix("ai:")
    if not normalized.startswith("ai-"):
        normalized = f"ai-{normalized.removeprefix('ai-')}"
    return normalized


def _normalize_engine_id(engine: str) -> str:
    return _ENGINE_ALIASES.get(engine, engine)


def _capture_outcome(
    engine: str, *, session_id: str | None, trace_id: str | None
) -> tuple[str, list[str]]:
    missing: list[str] = []
    if engine in _DEGRADED_HOSTS:
        if not session_id:
            missing.append("sessionId")
        if not trace_id:
            missing.append("traceId")
    return ("degraded", missing) if missing else ("success", [])


def _bounded_summary(text: str | None) -> str | None:
    if not text:
        return None
    redacted = _SECRET_RE.sub(r"\1\2[REDACTED]", text)
    if len(redacted) <= _MAX_SUMMARY_LEN:
        return redacted
    return redacted[:_MAX_SUMMARY_LEN] + "...[truncated]"


def _normalize_artifact_refs(artifact_refs: tuple[str, ...] | list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in artifact_refs or ():
        path = value.strip()
        if not path or path in seen:
            continue
        seen.add(path)
        normalized.append(path)
    return normalized


# ---------------------------------------------------------------------------
# Core event building and persistence
# ---------------------------------------------------------------------------


def framework_events_path(project_root: Path) -> Path:
    return project_root / FRAMEWORK_EVENTS_REL


def _pointer_specs_dir(project_root: Path) -> Path | None:
    pointer_path = project_root / _ACTIVE_WORK_PLANE_POINTER
    if not pointer_path.exists():
        return None

    try:
        payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    specs_dir_value = payload.get("specsDir")
    if not isinstance(specs_dir_value, str) or not specs_dir_value.strip():
        return None

    raw_specs_dir = Path(specs_dir_value)
    if raw_specs_dir.is_absolute():
        return None

    specs_dir = project_root / raw_specs_dir
    try:
        specs_dir.resolve().relative_to(project_root.resolve())
    except ValueError:
        return None
    return specs_dir


def _declared_work_plane_contexts(project_root: Path) -> tuple[tuple[str, str, Path], ...]:
    specs_dir = _pointer_specs_dir(project_root) or (project_root / _AI_ENGINEERING_DIR / "specs")
    return (
        ("spec", "spec", specs_dir / "spec.md"),
        ("plan", "plan", specs_dir / "plan.md"),
    )


def _resolve_constitution_context_path(project_root: Path) -> Path:
    constitution_path = project_root / "CONSTITUTION.md"
    if constitution_path.is_file():
        return constitution_path
    return project_root / _AI_ENGINEERING_DIR / "CONSTITUTION.md"


def _compute_prev_event_hash(path: Path) -> str | None:
    """Spec-107 H2: SHA256 of the canonical-JSON payload of the last entry.

    Stdlib-only mirror of ``ai_engineering.state.audit_chain.compute_entry_hash``
    so the hook-local _lib remains self-contained (no third-party imports).
    Returns ``None`` for missing/empty/malformed-tail files -- the chain
    re-anchors rather than refusing the write (additive backward-compat).
    """
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
    except ValueError:
        return None
    if not isinstance(prior, dict):
        return None
    stripped = {k: v for k, v in prior.items() if k not in ("prev_event_hash", "prevEventHash")}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_framework_event(project_root: Path, entry: dict) -> None:
    path = framework_events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Spec-110 D-110-03: stamp the chain pointer at the *root* of the
    # on-disk JSON object (sibling of ``kind`` / ``detail``) rather than
    # nested under ``detail``. The reader (``audit_chain.iter_validate_chain``)
    # supports both locations during the 30-day dual-read window that
    # closes 2026-05-29. Build a shallow copy so ``entry`` (the caller's
    # in-memory dict) stays free of the disk-only chain pointer; this
    # mirrors the package writer's behavior and keeps parity with the
    # ``model_dump``-based pkg path.
    payload = dict(entry)
    kind = payload.get("kind")
    if kind not in _ALLOWED_KINDS:
        msg = f"Unsupported framework event kind: {kind!r}"
        raise ValueError(msg)
    payload["engine"] = _normalize_engine_id(str(payload["engine"]))

    # Spec-126 D-126-05 / T-3.3: hash compute + write must be inside the
    # same critical section to prevent the TOCTOU race where two
    # concurrent writers observe the same ``prev_event_hash`` and append
    # duplicate-pointer entries. Lazy import keeps the module-load cost
    # flat for callers that never reach this path.
    from _lib.locked_append import with_lock_retry

    with with_lock_retry(project_root, "framework-events") as _locked:
        # ``_locked`` is unused: on fail-open (False) we still proceed
        # with the same write so the user-visible flow is not derailed,
        # mirroring the existing fail-open posture in
        # ``_lib/hook-common.py``. Lock-acquisition telemetry is emitted
        # by ``with_lock_retry`` itself to the sidecar.
        payload["prev_event_hash"] = _compute_prev_event_hash(path)
        line = json.dumps(payload, sort_keys=True, default=_json_serializer)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _shape_genai_block(usage: dict) -> dict | None:
    """Reshape a flat ``usage`` dict into the OTel-mirroring nested block.

    Stdlib-only mirror of
    ``ai_engineering.state.observability._shape_genai_block``. Returns
    ``None`` when the input is malformed (missing required
    ``input_tokens`` / ``output_tokens``); the caller surfaces a
    ``framework_error`` with ``error_code = "genai_usage_malformed"``.
    """
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None

    usage_block: dict = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    total_tokens = usage.get("total_tokens")
    if isinstance(total_tokens, int):
        usage_block["total_tokens"] = total_tokens
    else:
        usage_block["total_tokens"] = input_tokens + output_tokens
    cost_usd = usage.get("cost_usd")
    if isinstance(cost_usd, (int, float)):
        usage_block["cost_usd"] = cost_usd

    block: dict = {"usage": usage_block}
    system = usage.get("system")
    if isinstance(system, str):
        block["system"] = system
    model = usage.get("model")
    if isinstance(model, str):
        block["request"] = {"model": model}
    return block


def build_framework_event(
    project_root: Path,
    *,
    engine: str,
    kind: str,
    component: str,
    detail: dict | None = None,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
    correlation_id: str | None = None,
    force_outcome: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    usage: dict | None = None,
) -> dict:
    """Stdlib-only mirror of :func:`ai_engineering.state.observability.build_framework_event`.

    Spec-120 §4.1 additive kwargs:

    * ``span_id`` -- 16-hex; auto-generated via ``new_span_id()`` when
      omitted.
    * ``parent_span_id`` -- 16-hex logical parent (``None`` for root).
    * ``trace_id`` -- 32-hex W3C trace identifier; when omitted *and*
      ``parent_span_id`` is also omitted, inherits from
      :func:`_lib.trace_context.current_trace_context` (which fresh-
      fallbacks to a brand-new trace_id with NULL parent when no
      context exists).
    * ``usage`` -- flat dict; reshaped into ``detail.genai`` when
      well-formed. Malformed payloads are dropped silently and a
      ``framework_error`` of ``error_code = "genai_usage_malformed"`` is
      emitted best-effort.

    Degraded-host outcome capture runs against the **original**
    pre-auto-fill ``trace_id`` so codex / similar still surface a
    missing host trace in ``missing_fields``.
    """
    canonical_engine = _normalize_engine_id(engine)
    # Capture degraded-host outcome BEFORE auto-fill so codex / similar
    # hosts that omit a session/trace from their payload remain flagged.
    outcome, missing_fields = _capture_outcome(
        canonical_engine,
        session_id=session_id,
        trace_id=trace_id,
    )
    payload = dict(detail or {})
    if missing_fields:
        payload["degraded_reason"] = "missing-host-metadata"
        payload["missing_fields"] = missing_fields

    # Spec-120 §4.1 trace-context auto-fill via the stdlib-only mirror.
    # Lazy import keeps the module-load cost flat for hooks that never
    # touch trace context.
    from . import trace_context as _tc

    resolved_span_id = span_id or _tc.new_span_id()
    resolved_trace_id = trace_id
    resolved_parent_span_id = parent_span_id
    if trace_id is None and parent_span_id is None:
        resolved_trace_id, resolved_parent_span_id = _tc.current_trace_context(project_root)

    # Spec-120 §4.1 OTel `genai` block. Malformed `usage` is best-effort:
    # surface a `framework_error` and skip the block, but still build
    # the original event so the caller's flow is not derailed.
    if usage is not None:
        if isinstance(usage, dict):
            shaped = _shape_genai_block(usage)
            if shaped is not None:
                payload["genai"] = shaped
            else:
                _emit_genai_usage_malformed(
                    project_root,
                    engine=canonical_engine,
                    component=component,
                    summary="missing input_tokens / output_tokens",
                )
        else:
            _emit_genai_usage_malformed(
                project_root,
                engine=canonical_engine,
                component=component,
                summary=f"usage must be a dict, got {type(usage).__name__}",
            )

    entry: dict = {
        "schemaVersion": FRAMEWORK_EVENT_SCHEMA_VERSION,
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": project_root.name,
        "engine": canonical_engine,
        "kind": kind,
        "outcome": force_outcome or outcome,
        "component": component,
        "correlationId": correlation_id or uuid4().hex,
        "detail": payload,
    }
    if source is not None:
        entry["source"] = source
    if session_id is not None:
        entry["sessionId"] = session_id
    if resolved_trace_id is not None:
        entry["traceId"] = resolved_trace_id
    if parent_id is not None:
        entry["parentId"] = parent_id
    # Spec-120 §4.1: spanId is auto-filled (always present); parentSpanId
    # may legitimately be None (root span) and is omitted in that case
    # to match the pkg-side `exclude_none=True` model_dump semantics.
    entry["spanId"] = resolved_span_id
    if resolved_parent_span_id is not None:
        entry["parentSpanId"] = resolved_parent_span_id
    return entry


def _emit_genai_usage_malformed(
    project_root: Path,
    *,
    engine: str,
    component: str,
    summary: str,
) -> None:
    """Best-effort framework_error emission for malformed `usage` payloads.

    Mirrors the pkg-side helper; defensive shield around the actual
    emit so a malformed-usage report never compounds into a hard crash
    on the caller's flow.
    """
    import contextlib

    with contextlib.suppress(Exception):  # defensive shield
        emit_framework_error(
            project_root,
            engine=engine,
            component=component,
            error_code="genai_usage_malformed",
            summary=summary,
        )


# ---------------------------------------------------------------------------
# Emit helpers (each writes NDJSON + returns the dict)
# ---------------------------------------------------------------------------


def emit_skill_invoked(
    project_root: Path,
    *,
    engine: str,
    skill_name: str,
    component: str,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    usage: dict | None = None,
) -> dict:
    """Stdlib-only mirror of the pkg-side ``emit_skill_invoked``.

    Spec-120 §4.1 additive kwargs (``span_id`` / ``parent_span_id`` /
    ``usage``) forward as-is to :func:`build_framework_event`; existing
    positional/keyword arguments stay unchanged so legacy hook call
    sites continue to work.
    """
    detail: dict = {"skill": _normalize_skill_name(skill_name)}
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="skill_invoked",
        component=component,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        detail=detail,
        span_id=span_id,
        parent_span_id=parent_span_id,
        usage=usage,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_agent_dispatched(
    project_root: Path,
    *,
    engine: str,
    agent_name: str,
    component: str,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    usage: dict | None = None,
) -> dict:
    """Stdlib-only mirror of the pkg-side ``emit_agent_dispatched``.

    Spec-120 §4.1 additive kwargs (``span_id`` / ``parent_span_id`` /
    ``usage``) forward as-is to :func:`build_framework_event`; existing
    positional/keyword arguments stay unchanged so legacy hook call
    sites continue to work.
    """
    detail: dict = {"agent": _normalize_agent_name(agent_name)}
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="agent_dispatched",
        component=component,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        detail=detail,
        span_id=span_id,
        parent_span_id=parent_span_id,
        usage=usage,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_context_load(
    project_root: Path,
    *,
    engine: str,
    context_class: str,
    context_name: str,
    component: str,
    source: str | None = None,
    initiator_kind: str | None = None,
    initiator_name: str | None = None,
    load_mode: str = "runtime",
    path: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    force_outcome: str | None = None,
    metadata: dict | None = None,
) -> dict:
    detail: dict = {
        "context_class": context_class,
        "context_name": context_name,
        "load_mode": load_mode,
    }
    if path:
        detail["path"] = path
    if initiator_kind:
        detail["initiator_kind"] = initiator_kind
    if initiator_name:
        detail["initiator_name"] = initiator_name
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="context_load",
        component=component,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        force_outcome=force_outcome,
        detail=detail,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_declared_context_loads(
    project_root: Path,
    *,
    engine: str,
    initiator_kind: str,
    initiator_name: str,
    component: str,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
) -> list[dict]:
    root = project_root / ".ai-engineering"
    events: list[dict] = []

    constitution_path = _resolve_constitution_context_path(project_root)

    fixed_contexts = (
        ("constitution", "constitution", constitution_path),
        *_declared_work_plane_contexts(project_root),
        ("decision-store", "decision-store", root / "state" / "decision-store.json"),
    )
    for ctx_class, ctx_name, ctx_path in fixed_contexts:
        events.append(
            emit_context_load(
                project_root,
                engine=engine,
                context_class=ctx_class,
                context_name=ctx_name,
                component=component,
                source=source,
                initiator_kind=initiator_kind,
                initiator_name=initiator_name,
                load_mode="declared",
                path=ctx_path.relative_to(project_root).as_posix(),
                session_id=session_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                force_outcome="success" if ctx_path.exists() else "failure",
            )
        )

    team_dir = root / "contexts" / "team"
    if team_dir.is_dir():
        for team_path in sorted(team_dir.glob("*.md")):
            events.append(
                emit_context_load(
                    project_root,
                    engine=engine,
                    context_class="team",
                    context_name=team_path.stem,
                    component=component,
                    source=source,
                    initiator_kind=initiator_kind,
                    initiator_name=initiator_name,
                    load_mode="declared",
                    path=team_path.relative_to(project_root).as_posix(),
                    session_id=session_id,
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    force_outcome="success",
                )
            )

    return events


def emit_ide_hook_outcome(
    project_root: Path,
    *,
    engine: str,
    hook_kind: str,
    component: str,
    outcome: str,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    detail: dict = {"hook_kind": hook_kind}
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="ide_hook",
        component=component,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        force_outcome=outcome,
        detail=detail,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_framework_error(
    project_root: Path,
    *,
    engine: str,
    component: str,
    error_code: str,
    summary: str | None = None,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    detail: dict = {"error_code": error_code}
    bounded = _bounded_summary(summary)
    if bounded:
        detail["summary"] = bounded
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="framework_error",
        component=component,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
        force_outcome="failure",
        detail=detail,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_control_outcome(
    project_root: Path,
    *,
    category: str,
    control: str,
    component: str,
    outcome: str,
    source: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    detail: dict = {"category": category, "control": control}
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine="ai_engineering",
        kind="control_outcome",
        component=component,
        source=source,
        correlation_id=correlation_id,
        force_outcome=outcome,
        detail=detail,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_framework_operation(
    project_root: Path,
    *,
    operation: str,
    component: str,
    outcome: str = "success",
    source: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    detail: dict = {"operation": operation}
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine="ai_engineering",
        kind="framework_operation",
        component=component,
        source=source,
        correlation_id=correlation_id,
        force_outcome=outcome,
        detail=detail,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_task_trace(
    project_root: Path,
    *,
    task_id: str,
    lifecycle_phase: str,
    component: str,
    artifact_refs: tuple[str, ...] | list[str] | None = None,
    engine: str = "ai_engineering",
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    normalized_task_id = task_id.strip()
    normalized_phase = lifecycle_phase.strip()
    if not normalized_task_id:
        msg = "task_trace requires a non-empty task_id"
        raise ValueError(msg)
    if not normalized_phase:
        msg = "task_trace requires a non-empty lifecycle_phase"
        raise ValueError(msg)

    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="task_trace",
        component=component,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        parent_id=parent_id,
        correlation_id=correlation_id,
        detail={
            "task_id": normalized_task_id,
            "lifecycle_phase": normalized_phase,
            "artifact_refs": _normalize_artifact_refs(artifact_refs),
        },
    )
    append_framework_event(project_root, entry)
    return entry


# ---------------------------------------------------------------------------
# spec-119 evaluation layer emit helpers (D-119-01)
# All eight emit_eval_* helpers route through _emit_eval_run, which in turn
# routes through append_framework_event so the audit hash chain stays intact.
# ---------------------------------------------------------------------------


_EVAL_RUN_OPERATIONS: frozenset[str] = frozenset(
    {
        "eval_started",
        "scenario_executed",
        "pass_at_k_computed",
        "hallucination_rate_computed",
        "regression_detected",
        "regression_cleared",
        "eval_gated",
        "baseline_updated",
    }
)


def _emit_eval_run(
    project_root: Path,
    *,
    operation: str,
    component: str,
    outcome: str = "success",
    source: str | None = None,
    correlation_id: str | None = None,
    detail_extras: dict | None = None,
) -> dict:
    if operation not in _EVAL_RUN_OPERATIONS:
        msg = f"eval_run operation must be one of {sorted(_EVAL_RUN_OPERATIONS)}; got {operation!r}"
        raise ValueError(msg)
    detail: dict = {"operation": operation}
    if detail_extras:
        detail.update(detail_extras)
    entry = build_framework_event(
        project_root,
        engine="ai_engineering",
        kind="eval_run",
        component=component,
        source=source,
        correlation_id=correlation_id,
        force_outcome=outcome,
        detail=detail,
    )
    append_framework_event(project_root, entry)
    return entry


def emit_eval_started(
    project_root: Path,
    *,
    component: str,
    scenario_pack: str,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    return _emit_eval_run(
        project_root,
        operation="eval_started",
        component=component,
        source=source,
        correlation_id=correlation_id,
        detail_extras={"scenario_pack": scenario_pack},
    )


def emit_scenario_executed(
    project_root: Path,
    *,
    component: str,
    scenario_id: str,
    trial_id: int,
    pass_: bool,
    duration_ms: float | None = None,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    extras: dict = {
        "scenario_id": scenario_id,
        "trial_id": int(trial_id),
        "pass": bool(pass_),
    }
    if duration_ms is not None:
        extras["duration_ms"] = float(duration_ms)
    return _emit_eval_run(
        project_root,
        operation="scenario_executed",
        component=component,
        source=source,
        correlation_id=correlation_id,
        detail_extras=extras,
    )


def emit_pass_at_k_computed(
    project_root: Path,
    *,
    component: str,
    k: int,
    pass_count: int,
    total: int,
    score: float,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    return _emit_eval_run(
        project_root,
        operation="pass_at_k_computed",
        component=component,
        source=source,
        correlation_id=correlation_id,
        detail_extras={
            "k": int(k),
            "pass_count": int(pass_count),
            "total": int(total),
            "score": float(score),
        },
    )


def emit_hallucination_rate_computed(
    project_root: Path,
    *,
    component: str,
    rate: float,
    total_assertions: int,
    failed_assertions: int,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    return _emit_eval_run(
        project_root,
        operation="hallucination_rate_computed",
        component=component,
        source=source,
        correlation_id=correlation_id,
        detail_extras={
            "rate": float(rate),
            "total_assertions": int(total_assertions),
            "failed_assertions": int(failed_assertions),
        },
    )


def emit_regression_detected(
    project_root: Path,
    *,
    component: str,
    delta: float,
    threshold: float,
    tolerance: float,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    return _emit_eval_run(
        project_root,
        operation="regression_detected",
        component=component,
        source=source,
        correlation_id=correlation_id,
        outcome="failure",
        detail_extras={
            "delta": float(delta),
            "threshold": float(threshold),
            "tolerance": float(tolerance),
        },
    )


def emit_regression_cleared(
    project_root: Path,
    *,
    component: str,
    delta: float,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    return _emit_eval_run(
        project_root,
        operation="regression_cleared",
        component=component,
        source=source,
        correlation_id=correlation_id,
        detail_extras={"delta": float(delta)},
    )


def emit_eval_gated(
    project_root: Path,
    *,
    component: str,
    verdict: str,
    regression_delta_vs_baseline: float | None = None,
    failed_scenarios: tuple[str, ...] | list[str] | None = None,
    reason: str | None = None,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    allowed_verdicts = {"GO", "CONDITIONAL", "NO_GO", "SKIPPED"}
    if verdict not in allowed_verdicts:
        msg = f"eval_gated verdict must be one of {sorted(allowed_verdicts)}; got {verdict!r}"
        raise ValueError(msg)
    extras: dict = {"verdict": verdict}
    if regression_delta_vs_baseline is not None:
        extras["regression_delta_vs_baseline"] = float(regression_delta_vs_baseline)
    if failed_scenarios:
        extras["failed_scenarios"] = list(failed_scenarios)
    if reason:
        extras["reason"] = reason
    # NO_GO and SKIPPED are non-success outcomes for downstream consumers.
    outcome = "failure" if verdict == "NO_GO" else "success"
    if verdict == "SKIPPED":
        outcome = "degraded"
    return _emit_eval_run(
        project_root,
        operation="eval_gated",
        component=component,
        source=source,
        correlation_id=correlation_id,
        outcome=outcome,
        detail_extras=extras,
    )


def emit_baseline_updated(
    project_root: Path,
    *,
    component: str,
    prev_pass_at_k: float,
    new_pass_at_k: float,
    correlation_id: str | None = None,
    source: str | None = None,
) -> dict:
    return _emit_eval_run(
        project_root,
        operation="baseline_updated",
        component=component,
        source=source,
        correlation_id=correlation_id,
        detail_extras={
            "prev_pass_at_k": float(prev_pass_at_k),
            "new_pass_at_k": float(new_pass_at_k),
        },
    )
