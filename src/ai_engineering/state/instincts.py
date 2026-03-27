"""Project-local instinct learning artifacts for spec-080."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

from ai_engineering.state.io import read_ndjson_entries, write_json_model
from ai_engineering.state.models import FrameworkEvent, InstinctMeta, InstinctObservation
from ai_engineering.state.observability import framework_events_path

OBSERVATION_RETENTION_DAYS = 30
MAX_SUMMARY_LEN = 160
MAX_CONTEXT_ITEMS = 5
INSTINCTS_SCHEMA_VERSION = "1.0"
INSTINCT_CONTEXT_HEADER = "# Instinct Context"
INSTINCT_OBSERVATIONS_REL = Path(".ai-engineering/state/instinct-observations.ndjson")
INSTINCTS_REL = Path(".ai-engineering/instincts/instincts.yml")
INSTINCT_CONTEXT_REL = Path(".ai-engineering/instincts/context.md")
INSTINCT_META_REL = Path(".ai-engineering/instincts/meta.json")

_SECRET_RE = re.compile(
    r"(?i)(api_key|token|secret|password|authorization|credentials|auth)"
    r"([\"'\s:=]+)"
    r"[^\s\"',;]{4,}",
)
_ERROR_HINTS = ("error", "exception", "failed", "traceback", "denied", "timeout")
_INPUT_KEYS = (
    "file_path",
    "path",
    "command",
    "description",
    "subagent_type",
    "pattern",
    "query",
    "url",
)
_OUTPUT_KEYS = ("message", "stderr", "stdout", "error", "result", "status", "summary")


def instinct_observations_path(project_root: Path) -> Path:
    return project_root / INSTINCT_OBSERVATIONS_REL


def instincts_path(project_root: Path) -> Path:
    return project_root / INSTINCTS_REL


def instinct_context_path(project_root: Path) -> Path:
    return project_root / INSTINCT_CONTEXT_REL


def instinct_meta_path(project_root: Path) -> Path:
    return project_root / INSTINCT_META_REL


def default_instincts_document() -> dict[str, Any]:
    return {
        "schemaVersion": INSTINCTS_SCHEMA_VERSION,
        "updatedAt": _iso_now(),
        "toolSequences": [],
        "errorRecoveries": [],
        "skillAgentPreferences": [],
    }


def default_instinct_context() -> str:
    return (
        f"{INSTINCT_CONTEXT_HEADER}\n\n"
        "No active instincts yet. Capture more sessions before loading this context.\n"
    )


def ensure_instinct_artifacts(project_root: Path) -> None:
    obs_path = instinct_observations_path(project_root)
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    if not obs_path.exists():
        obs_path.write_text("", encoding="utf-8")

    inst_path = instincts_path(project_root)
    inst_path.parent.mkdir(parents=True, exist_ok=True)
    if not inst_path.exists():
        inst_path.write_text(
            yaml.safe_dump(default_instincts_document(), sort_keys=False),
            encoding="utf-8",
        )

    context_path = instinct_context_path(project_root)
    if not context_path.exists():
        context_path.write_text(default_instinct_context(), encoding="utf-8")

    meta_path = instinct_meta_path(project_root)
    if not meta_path.exists():
        write_json_model(meta_path, InstinctMeta())


def load_instinct_meta(project_root: Path) -> InstinctMeta:
    ensure_instinct_artifacts(project_root)
    path = instinct_meta_path(project_root)
    return InstinctMeta.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_instinct_meta(project_root: Path, meta: InstinctMeta) -> None:
    write_json_model(instinct_meta_path(project_root), meta)


def load_instincts_document(project_root: Path) -> dict[str, Any]:
    ensure_instinct_artifacts(project_root)
    path = instincts_path(project_root)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    doc = default_instincts_document()
    doc.update(raw)
    doc["toolSequences"] = list(doc.get("toolSequences", []))
    doc["errorRecoveries"] = list(doc.get("errorRecoveries", []))
    doc["skillAgentPreferences"] = list(doc.get("skillAgentPreferences", []))
    return doc


def save_instincts_document(project_root: Path, document: dict[str, Any]) -> None:
    ensure_instinct_artifacts(project_root)
    document["schemaVersion"] = INSTINCTS_SCHEMA_VERSION
    document["updatedAt"] = _iso_now()
    instincts_path(project_root).write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )


def read_instinct_observations(project_root: Path) -> list[InstinctObservation]:
    ensure_instinct_artifacts(project_root)
    return read_ndjson_entries(instinct_observations_path(project_root), InstinctObservation)


def prune_instinct_observations(
    project_root: Path,
    *,
    now: datetime | None = None,
) -> list[InstinctObservation]:
    cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=OBSERVATION_RETENTION_DAYS)
    kept = [
        entry for entry in read_instinct_observations(project_root) if entry.timestamp >= cutoff
    ]
    _write_observations(project_root, kept)
    return kept


def append_instinct_observation(
    project_root: Path,
    *,
    engine: str,
    hook_event: str,
    data: dict[str, Any],
    session_id: str | None = None,
) -> InstinctObservation | None:
    ensure_instinct_artifacts(project_root)

    tool = str(data.get("tool_name") or "").strip()
    if not tool:
        return None

    observation = InstinctObservation(
        engine=engine,
        kind="tool_start" if hook_event == "PreToolUse" else "tool_complete",
        tool=tool,
        outcome=_derive_outcome(data),
        session_id=session_id or _extract_session_id(data),
        detail=_build_observation_detail(data, hook_event=hook_event),
    )

    entries = prune_instinct_observations(project_root)
    entries.append(observation)
    _write_observations(project_root, entries)
    return observation


def extract_instincts(project_root: Path) -> bool:
    ensure_instinct_artifacts(project_root)
    meta = load_instinct_meta(project_root)
    observations = prune_instinct_observations(project_root)
    new_observations = _filter_new_observations(observations, meta.last_extracted_at)
    if not new_observations:
        return False

    document = load_instincts_document(project_root)
    sessions = _group_by_session(new_observations)
    sequence_counts = _detect_tool_sequences(sessions)
    recovery_counts = _detect_error_recoveries(sessions)
    preference_counts = _detect_skill_agent_preferences(project_root, sessions.keys())

    _merge_counter(
        document["toolSequences"],
        sequence_counts,
        builder=lambda key, count, last_seen: {
            "key": key,
            "guidance": f"Common tool sequence: {key}.",
            "evidenceCount": count,
            "lastSeenAt": last_seen,
        },
    )
    _merge_counter(
        document["errorRecoveries"],
        recovery_counts,
        builder=_build_error_recovery_entry,
    )
    _merge_counter(
        document["skillAgentPreferences"],
        preference_counts,
        builder=_build_skill_agent_preference_entry,
    )
    save_instincts_document(project_root, document)

    newest = max((entry.timestamp for entry in new_observations), default=None)
    meta.last_extracted_at = newest
    meta.pending_context_refresh = True
    save_instinct_meta(project_root, meta)
    return True


def needs_context_refresh(
    project_root: Path,
    *,
    now: datetime | None = None,
) -> tuple[bool, dict[str, Any]]:
    ensure_instinct_artifacts(project_root)
    current = now or datetime.now(tz=UTC)
    meta = load_instinct_meta(project_root)
    observations = prune_instinct_observations(project_root, now=current)
    context_path = instinct_context_path(project_root)
    last_context = meta.last_context_generated_at
    delta_count = sum(
        1 for entry in observations if last_context is None or entry.timestamp > last_context
    )
    stale = (
        last_context is None
        or not context_path.exists()
        or (current - last_context) >= timedelta(hours=meta.context_max_age_hours)
    )
    should_refresh = meta.pending_context_refresh or stale or delta_count >= meta.delta_threshold
    return should_refresh, {
        "delta_count": delta_count,
        "stale": stale,
        "pending_context_refresh": meta.pending_context_refresh,
    }


def refresh_instinct_context(project_root: Path) -> str:
    ensure_instinct_artifacts(project_root)
    document = load_instincts_document(project_root)
    lines = [INSTINCT_CONTEXT_HEADER, ""]
    items = _select_context_items(document)
    if not items:
        lines.append("No active instincts yet. Capture more sessions before loading this context.")
    else:
        for item in items:
            lines.append(f"- {item['guidance']} Evidence: {item['evidenceCount']} observations.")
    content = "\n".join(lines).rstrip() + "\n"
    instinct_context_path(project_root).write_text(content, encoding="utf-8")

    meta = load_instinct_meta(project_root)
    meta.last_context_generated_at = datetime.now(tz=UTC)
    meta.pending_context_refresh = False
    save_instinct_meta(project_root, meta)
    return content


def maybe_refresh_instinct_context(project_root: Path) -> bool:
    should_refresh, _ = needs_context_refresh(project_root)
    if not should_refresh:
        return False
    refresh_instinct_context(project_root)
    return True


def _write_observations(project_root: Path, entries: list[InstinctObservation]) -> None:
    path = instinct_observations_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(entry.model_dump(by_alias=True, exclude_none=True), default=_json_serializer)
        for entry in entries
    ]
    path.write_text(("\n".join(lines) + ("\n" if lines else "")), encoding="utf-8")


def _json_serializer(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_session_id(data: dict[str, Any]) -> str | None:
    value = data.get("session_id") or data.get("sessionId")
    return str(value) if value else None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        parts = []
        for key in _OUTPUT_KEYS:
            if key in value:
                parts.append(f"{key}={value[key]}")
        if not parts:
            parts = [f"fields={','.join(sorted(value)[:5])}"]
        return ", ".join(parts)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:3])
    return str(value)


def _sanitize_text(value: str | None) -> str | None:
    if not value:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip()
    redacted = _SECRET_RE.sub(r"\1\2[REDACTED]", collapsed)
    return redacted[:MAX_SUMMARY_LEN] + ("..." if len(redacted) > MAX_SUMMARY_LEN else "")


def _summarize_mapping(mapping: dict[str, Any], *, keys: tuple[str, ...]) -> str | None:
    parts: list[str] = []
    for key in keys:
        value = mapping.get(key)
        if value in (None, "", [], {}):
            continue
        safe = _sanitize_text(_coerce_text(value))
        if safe:
            parts.append(f"{key}={safe}")
    if parts:
        return "; ".join(parts)
    if mapping:
        return f"fields={','.join(sorted(mapping)[:5])}"
    return None


def _derive_outcome(data: dict[str, Any]) -> str:
    for key in ("error", "tool_error", "exception"):
        if data.get(key):
            return "failure"
    result = _coerce_text(data.get("result") or data.get("tool_result"))
    if result and any(token in result.lower() for token in _ERROR_HINTS):
        return "failure"
    return "success" if data.get("tool_name") else "unknown"


def _build_observation_detail(data: dict[str, Any], *, hook_event: str) -> dict[str, Any]:
    tool_input = _coerce_mapping(data.get("tool_input"))
    tool_output = (
        _coerce_mapping(data.get("tool_output"))
        or _coerce_mapping(data.get("tool_result"))
        or _coerce_mapping(data.get("result"))
    )
    detail: dict[str, Any] = {
        "hook_event": hook_event,
        "input_summary": _summarize_mapping(tool_input, keys=_INPUT_KEYS),
        "output_summary": _sanitize_text(_coerce_text(tool_output or data.get("error"))),
        "error_flag": _derive_outcome(data) == "failure",
    }
    if file_path := tool_input.get("file_path"):
        detail["file_path"] = str(file_path)
    if subagent := tool_input.get("subagent_type"):
        detail["subagent_type"] = str(subagent)
    return {key: value for key, value in detail.items() if value not in (None, "")}


def _filter_new_observations(
    observations: list[InstinctObservation],
    last_extracted_at: datetime | None,
) -> list[InstinctObservation]:
    if last_extracted_at is None:
        return observations
    return [entry for entry in observations if entry.timestamp > last_extracted_at]


def _group_by_session(
    observations: list[InstinctObservation],
) -> dict[str, list[InstinctObservation]]:
    grouped: dict[str, list[InstinctObservation]] = defaultdict(list)
    for entry in observations:
        grouped[entry.session_id or "default"].append(entry)
    for entries in grouped.values():
        entries.sort(key=lambda item: item.timestamp)
    return grouped


def _detect_tool_sequences(
    sessions: dict[str, list[InstinctObservation]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entries in sessions.values():
        sequence = [entry.tool for entry in entries if entry.kind == "tool_start"]
        for left, right in pairwise(sequence):
            counts[f"{left} -> {right}"] += 1
    return counts


def _detect_error_recoveries(
    sessions: dict[str, list[InstinctObservation]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entries in sessions.values():
        for current, nxt in pairwise(entries):
            if current.kind != "tool_complete" or current.outcome != "failure":
                continue
            if nxt.kind != "tool_start":
                continue
            counts[f"{current.tool} -> {nxt.tool}"] += 1
    return counts


def _build_error_recovery_entry(key: str, count: int, last_seen: str) -> dict[str, Any]:
    failed_tool, recovery_tool = key.split(" -> ", maxsplit=1)
    return {
        "key": key,
        "guidance": (f"After {failed_tool} errors, {recovery_tool} is a common recovery step."),
        "evidenceCount": count,
        "lastSeenAt": last_seen,
    }


def _build_skill_agent_preference_entry(key: str, count: int, last_seen: str) -> dict[str, Any]:
    skill_name, agent_name = key.split(" -> ", maxsplit=1)
    return {
        "key": key,
        "skill": skill_name,
        "agent": agent_name,
        "guidance": (f"Within {skill_name}, {agent_name} is the most common dispatched agent."),
        "evidenceCount": count,
        "lastSeenAt": last_seen,
    }


def _detect_skill_agent_preferences(
    project_root: Path,
    session_ids: set[str],
) -> Counter[str]:
    path = framework_events_path(project_root)
    if not path.exists() or not session_ids:
        return Counter()
    counts: Counter[str] = Counter()
    events = read_ndjson_entries(path, FrameworkEvent)
    for session_id in session_ids:
        session_events = [event for event in events if event.session_id == session_id]
        session_events.sort(key=lambda item: item.timestamp)
        last_skill: str | None = None
        for event in session_events:
            if event.kind == "skill_invoked":
                last_skill = str(event.detail.get("skill") or "")
            elif event.kind == "agent_dispatched" and last_skill:
                agent = str(event.detail.get("agent") or "")
                if agent:
                    counts[f"{last_skill} -> {agent}"] += 1
    return counts


def _merge_counter(
    target: list[dict[str, Any]],
    counts: Counter[str],
    *,
    builder: Any,
) -> None:
    if not counts:
        return
    now = _iso_now()
    indexed = {str(entry.get("key")): entry for entry in target if entry.get("key")}
    for key, count in counts.items():
        if count <= 0:
            continue
        existing = indexed.get(key)
        if existing:
            existing["evidenceCount"] = int(existing.get("evidenceCount", 0)) + count
            existing["lastSeenAt"] = now
        else:
            created = builder(key, count, now)
            target.append(created)
            indexed[key] = created
    target.sort(key=lambda entry: (-int(entry.get("evidenceCount", 0)), str(entry.get("key", ""))))


def _select_context_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for key in ("toolSequences", "errorRecoveries", "skillAgentPreferences"):
        for item in document.get(key, []):
            combined.append(item)
    combined.sort(
        key=lambda entry: (
            -int(entry.get("evidenceCount", 0)),
            str(entry.get("lastSeenAt", "")),
            str(entry.get("key", "")),
        )
    )
    return combined[:MAX_CONTEXT_ITEMS]
