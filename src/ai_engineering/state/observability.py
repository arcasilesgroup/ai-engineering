"""Canonical framework observability artifacts for spec-082."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.state.io import append_ndjson, write_json_model
from ai_engineering.state.models import (
    CapabilityDescriptor,
    FrameworkCapabilitiesCatalog,
    FrameworkEvent,
)

FRAMEWORK_EVENT_SCHEMA_VERSION = "1.0"
FRAMEWORK_CAPABILITIES_SCHEMA_VERSION = "1.0"

FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
FRAMEWORK_CAPABILITIES_REL = Path(".ai-engineering") / "state" / "framework-capabilities.json"

CONTEXT_CLASS_NAMES: tuple[str, ...] = (
    "language",
    "framework",
    "shared-framework",
    "team",
    "project-identity",
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


def append_framework_event(project_root: Path, entry: FrameworkEvent) -> None:
    """Append a canonical framework event to the new NDJSON stream."""
    append_ndjson(framework_events_path(project_root), entry)


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
) -> FrameworkEvent:
    """Build a canonical framework event with explicit degraded capture semantics."""
    outcome, missing_fields = _capture_outcome(engine, session_id=session_id, trace_id=trace_id)
    payload = dict(detail or {})
    if missing_fields:
        payload["degraded_reason"] = "missing-host-metadata"
        payload["missing_fields"] = missing_fields

    return FrameworkEvent.model_validate(
        {
            "schemaVersion": FRAMEWORK_EVENT_SCHEMA_VERSION,
            "timestamp": datetime.now(tz=UTC),
            "project": _project_name(project_root),
            "engine": engine,
            "kind": kind,
            "outcome": force_outcome or outcome,
            "component": component,
            "source": source,
            "correlationId": correlation_id or uuid4().hex,
            "sessionId": session_id,
            "traceId": trace_id,
            "parentId": parent_id,
            "detail": payload,
        }
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
) -> FrameworkEvent:
    """Emit a canonical ``skill_invoked`` event."""
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
) -> FrameworkEvent:
    """Emit a canonical ``agent_dispatched`` event."""
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

    # Static state/spec contexts required by the framework workflow.
    fixed_contexts = (
        ("project-identity", "project-identity", root / "contexts" / "project-identity.md"),
        ("spec", "spec", root / "specs" / "spec.md"),
        ("plan", "plan", root / "specs" / "plan.md"),
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

    return FrameworkCapabilitiesCatalog.model_validate(
        {
            "schemaVersion": FRAMEWORK_CAPABILITIES_SCHEMA_VERSION,
            "skills": skills,
            "agents": agents,
            "contextClasses": context_classes,
            "hookKinds": hook_kinds,
        }
    )


def write_framework_capabilities(project_root: Path) -> FrameworkCapabilitiesCatalog:
    """Persist the canonical capability catalog under ``.ai-engineering/state``."""
    catalog = build_framework_capabilities(project_root)
    write_json_model(framework_capabilities_path(project_root), catalog)
    return catalog
