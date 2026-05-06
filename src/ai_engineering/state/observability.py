"""Canonical framework observability artifacts for spec-082."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.state.capabilities import build_capability_cards
from ai_engineering.state.control_plane import resolve_constitution_context_path
from ai_engineering.state.defaults import projection_update_metadata
from ai_engineering.state.event_schema import ALLOWED_EVENT_KINDS, normalize_engine_id
from ai_engineering.state.io import _json_serializer
from ai_engineering.state.locking import artifact_lock
from ai_engineering.state.models import (
    CapabilityDescriptor,
    FrameworkCapabilitiesCatalog,
    FrameworkEvent,
)
from ai_engineering.state.work_plane import resolve_active_work_plane

FRAMEWORK_EVENT_SCHEMA_VERSION = "1.0"
FRAMEWORK_CAPABILITIES_SCHEMA_VERSION = "1.0"

FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
FRAMEWORK_CAPABILITIES_REL = Path(".ai-engineering") / "state" / "framework-capabilities.json"


def _declared_work_plane_contexts(project_root: Path) -> tuple[tuple[str, str, Path], ...]:
    """Return declared spec/plan context paths from the active work-plane contract."""
    work_plane = resolve_active_work_plane(project_root)
    return (
        ("spec", "spec", work_plane.spec_path),
        ("plan", "plan", work_plane.plan_path),
    )


CONTEXT_CLASS_NAMES: tuple[str, ...] = (
    "language",
    "framework",
    "shared-framework",
    "team",
    "constitution",
    "spec",
    "plan",
    "decision-store",
)

HOOK_KIND_DESCRIPTORS: tuple[tuple[str, str], ...] = (
    ("session-start", "ide"),
    ("session-end", "ide"),
    ("user-prompt-submit", "ide"),
    ("pre-tool-use", "ide"),
    ("post-tool-use", "ide"),
    ("stop", "ide"),
    ("error-occurred", "ide"),
    ("pre-commit", "git"),
    ("commit-msg", "git"),
    ("pre-push", "git"),
)

_DEGRADED_HOSTS: frozenset[str] = frozenset({"codex"})
_SECRET_RE = re.compile(
    r"(?i)(api_key|token|secret|password|authorization|credentials|auth)"
    r"([\"'\s:=]+)"
    r"[^\s\"',;]{4,}",
)
_MAX_SUMMARY_LEN = 200


def framework_events_path(project_root: Path) -> Path:
    """Return the canonical framework event stream path."""
    return project_root / FRAMEWORK_EVENTS_REL


def framework_capabilities_path(project_root: Path) -> Path:
    """Return the canonical framework capability catalog path."""
    return project_root / FRAMEWORK_CAPABILITIES_REL


def _read_prev_event_hash(path: Path) -> str | None:
    """Compute the SHA256 of the last entry in the events ndjson, if any.

    Spec-107 D-107-10 (H2): each new event carries a ``prev_event_hash``
    pointer to the canonical-JSON SHA256 of the prior entry, forming a
    tamper-evident chain. Missing or empty file returns ``None`` (chain
    anchor). Malformed last line is treated as missing -- additive
    backward-compat: the chain restarts rather than refusing the write.
    """
    from ai_engineering.state.audit_chain import compute_entry_hash

    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    last_line = text.strip().splitlines()[-1].strip()
    if not last_line:
        return None
    try:
        prior = json.loads(last_line)
    except json.JSONDecodeError:
        return None
    if not isinstance(prior, dict):
        return None
    return compute_entry_hash(prior)


def _append_framework_event_locked(project_root: Path, entry: FrameworkEvent) -> None:
    """Append a canonical framework event while the caller holds the event lock."""
    _append_framework_events_locked(project_root, [entry])


def _append_framework_events_locked(project_root: Path, entries: list[FrameworkEvent]) -> None:
    """Append canonical framework events while the caller holds the event lock."""
    if not entries:
        return

    path = framework_events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    from ai_engineering.state.audit_chain import compute_entry_hash

    previous_hash = _read_prev_event_hash(path)
    lines: list[str] = []
    for entry in entries:
        data = entry.model_dump(by_alias=True, exclude_none=True)
        kind = data.get("kind")
        if kind not in ALLOWED_EVENT_KINDS:
            msg = f"Unsupported framework event kind: {kind!r}"
            raise ValueError(msg)
        data["engine"] = normalize_engine_id(str(data["engine"]))
        data["prev_event_hash"] = previous_hash
        line = json.dumps(data, sort_keys=True, default=_json_serializer)
        lines.append(line)
        previous_hash = compute_entry_hash(json.loads(line))

    with path.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def append_framework_event(
    project_root: Path,
    entry: FrameworkEvent,
    *,
    lock_acquired: bool = False,
) -> None:
    """Append a canonical framework event to the NDJSON stream.

    Spec-110 D-110-03: stamps the ``prev_event_hash`` chain pointer at
    the *root* of the on-disk JSON object (sibling of ``kind`` /
    ``detail``) rather than nesting it under ``detail``. The pointer is
    the SHA256 of the last entry on disk, anchoring the tamper-evident
    chain. The pre-spec-110 layout placed the pointer inside
    ``detail.prev_event_hash`` -- the dual-read in ``audit_chain``
    transparently consumes both layouts during the 30-day grace window
    that closes 2026-05-29 (T-3.4).

    The :class:`FrameworkEvent` model is intentionally not extended with
    a ``prev_event_hash`` field; the pointer lives only on disk. This
    keeps the in-memory model parity with the stdlib ``_lib`` mirror
    used by hooks (which also returns the pointer-free dict from
    ``emit_*`` helpers and stamps the pointer in :func:`append_framework_event`
    only on the on-disk copy).
    """
    if lock_acquired:
        _append_framework_event_locked(project_root, entry)
        return

    with artifact_lock(project_root, "framework-events"):
        _append_framework_event_locked(project_root, entry)


def append_framework_events(
    project_root: Path,
    entries: list[FrameworkEvent],
    *,
    lock_acquired: bool = False,
) -> None:
    """Append multiple canonical framework events with one hash-chain read."""
    if lock_acquired:
        _append_framework_events_locked(project_root, entries)
        return

    with artifact_lock(project_root, "framework-events"):
        _append_framework_events_locked(project_root, entries)


def _project_name(project_root: Path) -> str:
    config = load_manifest_config(project_root)
    return config.name or project_root.name


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


def _capture_outcome(
    engine: str, *, session_id: str | None, trace_id: str | None
) -> tuple[str, list[str]]:
    missing_fields: list[str] = []
    if engine in _DEGRADED_HOSTS:
        if not session_id:
            missing_fields.append("sessionId")
        if not trace_id:
            missing_fields.append("traceId")
    return ("degraded", missing_fields) if missing_fields else ("success", [])


def _bounded_summary(text: str | None) -> str | None:
    if not text:
        return None
    redacted = _SECRET_RE.sub(r"\1\2[REDACTED]", text)
    if len(redacted) <= _MAX_SUMMARY_LEN:
        return redacted
    return redacted[:_MAX_SUMMARY_LEN] + "...[truncated]"


def _normalize_artifact_refs(
    artifact_refs: tuple[str, ...] | list[str] | None,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in artifact_refs or ():
        path = value.strip()
        if not path or path in seen:
            continue
        seen.add(path)
        normalized.append(path)
    return normalized


def _shape_genai_block(usage: dict[str, object]) -> dict[str, object] | None:
    """Reshape a flat ``usage`` dict into the OTel-mirroring nested block.

    Spec-120 §4.1: callers pass a flat dict like
    ``{"input_tokens": 1234, "output_tokens": 567,
       "model": "claude-sonnet-4-5", "system": "anthropic",
       "cost_usd": 0.0143}`` so call sites stay clean. This helper
    reshapes it into the nested form mirroring OTel GenAI conventions:

    .. code-block:: jsonc

        {
          "system":  "anthropic",
          "request": {"model": "claude-sonnet-4-5"},
          "usage":   {
            "input_tokens":  1234,
            "output_tokens": 567,
            "total_tokens":  1801,
            "cost_usd":      0.0143
          }
        }

    Returns ``None`` when the input is malformed (missing required
    ``input_tokens`` / ``output_tokens``); the caller surfaces a
    ``framework_error`` with ``error_code = "genai_usage_malformed"``.
    """
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None

    usage_block: dict[str, object] = {
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

    block: dict[str, object] = {"usage": usage_block}
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
    detail: dict[str, object] | None = None,
    source: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
    correlation_id: str | None = None,
    force_outcome: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    usage: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Build a canonical framework event with explicit degraded capture semantics.

    Spec-120 §4.1 additions (all optional, additive):

    * ``span_id`` -- 16-hex span identifier; auto-generated via
      ``new_span_id()`` when omitted so every event carries a unique
      span.
    * ``parent_span_id`` -- 16-hex logical parent for span-tree
      reconstruction; ``None`` for root spans.
    * ``trace_id`` -- 32-hex W3C trace identifier; when omitted *and*
      ``parent_span_id`` is also omitted, the helper inherits the active
      context from
      :func:`ai_engineering.state.trace_context.current_trace_context`
      (which fresh-fallbacks to a brand-new trace_id with NULL parent
      when no context exists).
    * ``usage`` -- flat dict of token / model metadata (see
      :func:`_shape_genai_block`); reshaped into ``detail.genai`` when
      well-formed. Malformed payloads are dropped silently and a
      ``framework_error`` of ``error_code = "genai_usage_malformed"`` is
      emitted best-effort -- the original event is still built so the
      caller's flow is not derailed.

    Degradation semantics (codex without host metadata) are preserved:
    ``_capture_outcome`` is called with the **original** (pre-auto-fill)
    ``trace_id`` so a missing host trace still surfaces in
    ``missing_fields``. Auto-fill happens after outcome capture solely
    for wire-format completeness.
    """
    canonical_engine = normalize_engine_id(engine)
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

    # Spec-120 §4.1 trace-context auto-fill. Must lazy-import to avoid a
    # circular import (`trace_context` corruption fallback emits a
    # framework_error which itself imports observability).
    from ai_engineering.state.trace_context import current_trace_context, new_span_id

    resolved_span_id = span_id or new_span_id()
    resolved_trace_id = trace_id
    resolved_parent_span_id = parent_span_id
    if trace_id is None and parent_span_id is None:
        resolved_trace_id, resolved_parent_span_id = current_trace_context(project_root)

    # Spec-120 §4.1 OTel `genai` block. Malformed `usage` is treated
    # best-effort: surface a `framework_error` and skip the block, but
    # still build the original event so the caller's flow is not
    # derailed.
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

    event_data: dict[str, object] = {
        "schemaVersion": FRAMEWORK_EVENT_SCHEMA_VERSION,
        "timestamp": datetime.now(tz=UTC),
        "project": _project_name(project_root),
        "engine": canonical_engine,
        "kind": kind,
        "outcome": force_outcome or outcome,
        "component": component,
        "source": source,
        "correlationId": correlation_id or uuid4().hex,
        "sessionId": session_id,
        "traceId": resolved_trace_id,
        "parentId": parent_id,
        "spanId": resolved_span_id,
        "parentSpanId": resolved_parent_span_id,
        "detail": payload,
    }
    return FrameworkEvent.model_validate(event_data)


def _emit_genai_usage_malformed(
    project_root: Path,
    *,
    engine: str,
    component: str,
    summary: str,
) -> None:
    """Best-effort framework_error emission for malformed `usage` payloads.

    Spec-120 §4.1: malformed `usage` must NOT raise from the caller's
    perspective -- the event is still built, the genai block is just
    skipped. We surface the malformation as a framework_error so it
    appears in the audit chain for debugging.

    Best-effort: any exception during the error-emit is swallowed
    (we don't want to compound a malformed-usage report into a hard
    crash on the caller's flow).
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
    metadata: dict[str, object] | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    usage: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical ``skill_invoked`` event.

    Spec-120 §4.1 additive kwargs (``span_id`` / ``parent_span_id`` /
    ``usage``) are forwarded as-is to :func:`build_framework_event`;
    see that helper's docstring for the auto-fill and OTel-genai
    semantics. All existing positional/keyword arguments stay
    unchanged -- callers that ignore the new kwargs see no behaviour
    change at the wire level beyond the new auto-filled
    ``traceId`` / ``spanId`` fields.
    """
    detail = {"skill": _normalize_skill_name(skill_name)}
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
    metadata: dict[str, object] | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    usage: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical ``agent_dispatched`` event.

    Spec-120 §4.1 additive kwargs (``span_id`` / ``parent_span_id`` /
    ``usage``) are forwarded as-is to :func:`build_framework_event`;
    see that helper's docstring for the auto-fill and OTel-genai
    semantics. All existing positional/keyword arguments stay
    unchanged -- callers that ignore the new kwargs see no behaviour
    change at the wire level beyond the new auto-filled
    ``traceId`` / ``spanId`` fields.
    """
    detail = {"agent": _normalize_agent_name(agent_name)}
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
    metadata: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical ``context_load`` event."""
    detail: dict[str, object] = {
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
) -> list[FrameworkEvent]:
    """Emit declared context loads implied by the framework contract for a skill flow."""
    root = project_root / ".ai-engineering"
    config = load_manifest_config(project_root)
    events: list[FrameworkEvent] = []

    constitution_path = resolve_constitution_context_path(project_root)

    # Static state/spec contexts required by the framework workflow.
    fixed_contexts = (
        ("constitution", "constitution", constitution_path),
        *_declared_work_plane_contexts(project_root),
        ("decision-store", "decision-store", root / "state" / "decision-store.json"),
    )
    for context_class, context_name, path in fixed_contexts:
        events.append(
            emit_context_load(
                project_root,
                engine=engine,
                context_class=context_class,
                context_name=context_name,
                component=component,
                source=source,
                initiator_kind=initiator_kind,
                initiator_name=initiator_name,
                load_mode="declared",
                path=path.relative_to(project_root).as_posix(),
                session_id=session_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                force_outcome="success" if path.exists() else "failure",
            )
        )

    shared_contexts = (
        ("shared-framework", "cli-ux", root / "contexts" / "cli-ux.md"),
        (
            "shared-framework",
            "mcp-integrations",
            root / "contexts" / "mcp-integrations.md",
        ),
    )
    for context_class, context_name, path in shared_contexts:
        events.append(
            emit_context_load(
                project_root,
                engine=engine,
                context_class=context_class,
                context_name=context_name,
                component=component,
                source=source,
                initiator_kind=initiator_kind,
                initiator_name=initiator_name,
                load_mode="declared",
                path=path.relative_to(project_root).as_posix(),
                session_id=session_id,
                trace_id=trace_id,
                correlation_id=correlation_id,
                force_outcome="success" if path.exists() else "failure",
            )
        )

    team_dir = root / "contexts" / "team"
    if team_dir.is_dir():
        for path in sorted(team_dir.glob("*.md")):
            events.append(
                emit_context_load(
                    project_root,
                    engine=engine,
                    context_class="team",
                    context_name=path.stem,
                    component=component,
                    source=source,
                    initiator_kind=initiator_kind,
                    initiator_name=initiator_name,
                    load_mode="declared",
                    path=path.relative_to(project_root).as_posix(),
                    session_id=session_id,
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    force_outcome="success",
                )
            )

    language_dir = root / "contexts" / "languages"
    framework_dir = root / "contexts" / "frameworks"
    for name in config.providers.stacks:
        language_path = language_dir / f"{name}.md"
        if language_path.exists():
            events.append(
                emit_context_load(
                    project_root,
                    engine=engine,
                    context_class="language",
                    context_name=name,
                    component=component,
                    source=source,
                    initiator_kind=initiator_kind,
                    initiator_name=initiator_name,
                    load_mode="declared",
                    path=language_path.relative_to(project_root).as_posix(),
                    session_id=session_id,
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    force_outcome="success",
                )
            )

        framework_path = framework_dir / f"{name}.md"
        if framework_path.exists():
            events.append(
                emit_context_load(
                    project_root,
                    engine=engine,
                    context_class="framework",
                    context_name=name,
                    component=component,
                    source=source,
                    initiator_kind=initiator_kind,
                    initiator_name=initiator_name,
                    load_mode="declared",
                    path=framework_path.relative_to(project_root).as_posix(),
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
    metadata: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical IDE hook outcome event."""
    detail = {"hook_kind": hook_kind}
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
    metadata: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical framework error event with stable codes and bounded summary."""
    detail: dict[str, object] = {"error_code": error_code}
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


def emit_git_hook_outcome(
    project_root: Path,
    *,
    hook_kind: str,
    checks: dict[str, str],
    failed_checks: list[str],
    failure_reasons: dict[str, str],
    component: str = "gate-engine",
    source: str | None = None,
    correlation_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical git hook or gate outcome event."""
    detail: dict[str, object] = {
        "hook_kind": hook_kind,
        "checks": checks,
        "failed_checks": failed_checks,
        "failure_reasons": {
            name: _bounded_summary(reason) or "" for name, reason in failure_reasons.items()
        },
    }
    if metadata:
        detail.update(metadata)
    entry = build_framework_event(
        project_root,
        engine="ai_engineering",
        kind="git_hook",
        component=component,
        source=source,
        correlation_id=correlation_id,
        force_outcome="success" if not failed_checks else "failure",
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
    metadata: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical governance, security, or quality control outcome."""
    detail: dict[str, object] = {
        "category": category,
        "control": control,
    }
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
    metadata: dict[str, object] | None = None,
) -> FrameworkEvent:
    """Emit a canonical framework lifecycle or maintenance operation event."""
    detail: dict[str, object] = {"operation": operation}
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


def build_task_trace_event(
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
) -> FrameworkEvent:
    """Build an append-only task trace from an authoritative task mutation."""
    normalized_task_id = task_id.strip()
    normalized_phase = lifecycle_phase.strip()
    if not normalized_task_id:
        msg = "task_trace requires a non-empty task_id"
        raise ValueError(msg)
    if not normalized_phase:
        msg = "task_trace requires a non-empty lifecycle_phase"
        raise ValueError(msg)

    return build_framework_event(
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
    lock_acquired: bool = False,
) -> FrameworkEvent:
    """Emit an append-only task trace from an authoritative task mutation."""
    entry = build_task_trace_event(
        project_root,
        task_id=task_id,
        lifecycle_phase=lifecycle_phase,
        component=component,
        artifact_refs=artifact_refs,
        engine=engine,
        source=source,
        session_id=session_id,
        trace_id=trace_id,
        parent_id=parent_id,
        correlation_id=correlation_id,
    )
    append_framework_event(project_root, entry, lock_acquired=lock_acquired)
    return entry


def build_framework_capabilities(project_root: Path) -> FrameworkCapabilitiesCatalog:
    """Build the capability catalog from manifest registry metadata plus static taxonomy."""
    config = load_manifest_config(project_root)

    skills = [
        CapabilityDescriptor(name=name, kind=entry.type or None, tags=list(entry.tags))
        for name, entry in sorted(config.skills.registry.items())
    ]
    agents = [
        CapabilityDescriptor(name=name if name.startswith("ai-") else f"ai-{name}")
        for name in sorted(config.agents.names)
    ]
    context_classes = [CapabilityDescriptor(name=name) for name in CONTEXT_CLASS_NAMES]
    hook_kinds = [
        CapabilityDescriptor(name=name, surface=surface) for name, surface in HOOK_KIND_DESCRIPTORS
    ]
    capability_cards = build_capability_cards(config)

    return FrameworkCapabilitiesCatalog.model_validate(
        {
            "schemaVersion": FRAMEWORK_CAPABILITIES_SCHEMA_VERSION,
            "updateMetadata": projection_update_metadata(
                context="framework capability catalog",
                source=".ai-engineering/manifest.yml registry metadata",
            ),
            "skills": skills,
            "agents": agents,
            "contextClasses": context_classes,
            "hookKinds": hook_kinds,
            "capabilityCards": capability_cards,
        }
    )


def write_framework_capabilities(project_root: Path) -> FrameworkCapabilitiesCatalog:
    """Persist the canonical capability catalog into state.db.

    Spec-125 cutover: the capability catalog moved from
    ``framework-capabilities.json`` to the ``tool_capabilities``
    singleton row in state.db (table created by migration 0005). The
    JSON sink is retired; this writer now UPSERTs the row.
    """
    catalog = build_framework_capabilities(project_root)

    # Lazy imports keep ``observability`` free of an eager dependency on
    # the state-db connection helpers.
    import json as _json
    from datetime import UTC as _UTC
    from datetime import datetime as _datetime

    from ai_engineering.state.state_db import connect, projection_write

    # Lazy bootstrap so a fresh state.db has the ``tool_capabilities``
    # table before the UPSERT. ``projection_write`` itself uses
    # ``apply_migrations=False`` to avoid double work on warm DBs.
    _bootstrap = connect(project_root, read_only=False, apply_migrations=None)
    _bootstrap.close()

    payload = catalog.model_dump(mode="json", by_alias=True)
    schema_version = str(payload.get("schemaVersion", "1.0"))
    generated_at = payload.get("generatedAt", "")
    if not isinstance(generated_at, str):
        generated_at = str(generated_at)
    agents = payload.get("agents") or []
    skills = payload.get("skills") or []
    cards = payload.get("capabilityCards") or []
    catalog_json = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
    updated_at = _datetime.now(_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    with projection_write(project_root) as conn:
        conn.execute(
            """
            INSERT INTO tool_capabilities
              (id, schema_version, generated_at, agents_count,
               skills_count, capability_cards_count, catalog_json, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              schema_version          = excluded.schema_version,
              generated_at            = excluded.generated_at,
              agents_count            = excluded.agents_count,
              skills_count            = excluded.skills_count,
              capability_cards_count  = excluded.capability_cards_count,
              catalog_json            = excluded.catalog_json,
              updated_at              = excluded.updated_at
            """,
            (
                schema_version,
                generated_at,
                len(agents),
                len(skills),
                len(cards),
                catalog_json,
                updated_at,
            ),
        )
    return catalog
