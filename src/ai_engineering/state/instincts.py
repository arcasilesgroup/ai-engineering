"""Project-local instinct learning artifacts for spec-080, v2 schema (spec-090)."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ai_engineering.state.io import read_ndjson_entries, write_json_model
from ai_engineering.state.models import FrameworkEvent, InstinctMeta, InstinctObservation
from ai_engineering.state.observability import framework_events_path

OBSERVATION_RETENTION_DAYS = 30
MAX_SUMMARY_LEN = 160
INSTINCTS_SCHEMA_VERSION = "2.0"
INSTINCT_OBSERVATIONS_REL = Path(".ai-engineering/state/observation-events.ndjson")
INSTINCTS_REL = Path(".ai-engineering/observations/observations.yml")
INSTINCT_META_REL = Path(".ai-engineering/observations/meta.json")

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


def instinct_meta_path(project_root: Path) -> Path:
    return project_root / INSTINCT_META_REL


def default_instincts_document() -> dict[str, Any]:
    return {
        "schemaVersion": INSTINCTS_SCHEMA_VERSION,
        "updatedAt": _iso_now(),
        "corrections": [],
        "recoveries": [],
        "workflows": [],
    }


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

    meta_path = instinct_meta_path(project_root)
    if not meta_path.exists():
        write_json_model(meta_path, InstinctMeta())


def load_instinct_meta(project_root: Path) -> InstinctMeta:
    """Load instinct meta, fail-open on parse / IO errors.

    A concurrent writer can race a reader mid-flush. Returning a fresh
    default on corruption is safer than re-raising and breaking the
    extract-instincts pipeline.
    """
    ensure_instinct_artifacts(project_root)
    path = instinct_meta_path(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        print(f"[instincts] load_instinct_meta could not parse {path}: {exc}", file=sys.stderr)
        return InstinctMeta()
    try:
        return InstinctMeta.model_validate(raw)
    except ValidationError as exc:
        print(
            f"[instincts] load_instinct_meta validation error on {path}: {exc}",
            file=sys.stderr,
        )
        return InstinctMeta()


def save_instinct_meta(project_root: Path, meta: InstinctMeta) -> None:
    write_json_model(instinct_meta_path(project_root), meta)


def load_instincts_document(project_root: Path) -> dict[str, Any]:
    """Load observations.yml, fail-open on parse / IO errors."""
    ensure_instinct_artifacts(project_root)
    path = instincts_path(project_root)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError, ValueError) as exc:
        print(
            f"[instincts] load_instincts_document parse/IO error on {path}: {exc}",
            file=sys.stderr,
        )
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    if raw.get("schemaVersion") != "2.0":
        raw = _migrate_v1_to_v2(raw)
    doc = default_instincts_document()
    doc.update(raw)
    doc["corrections"] = list(doc.get("corrections") or [])
    doc["recoveries"] = list(doc.get("recoveries") or [])
    doc["workflows"] = list(doc.get("workflows") or [])
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

    # Recoveries (error -> recovery tool patterns)
    recovery_counts = _detect_error_recoveries(sessions)
    _merge_counter(
        document["recoveries"],
        recovery_counts,
        builder=_build_recovery_entry,
    )

    # Workflows (skill -> skill sequences from framework events)
    workflow_counts = _detect_skill_workflows(project_root)
    _merge_counter(
        document["workflows"],
        workflow_counts,
        builder=_build_workflow_entry,
    )

    # Apply confidence scoring to all merged entries
    for family in ("recoveries", "workflows"):
        for entry in document[family]:
            entry["confidence"] = confidence_for_count(entry.get("evidenceCount", 1))

    save_instincts_document(project_root, document)

    newest = max((entry.timestamp for entry in new_observations), default=None)
    meta.last_extracted_at = newest
    save_instinct_meta(project_root, meta)
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


def _build_recovery_entry(key: str, count: int, last_seen: str) -> dict[str, Any]:
    failed_tool, recovery_tool = key.split(" -> ", maxsplit=1)
    return {
        "key": key,
        "trigger": f"{failed_tool} failure",
        "action": f"Invoke {recovery_tool}",
        "guidance": f"After {failed_tool} errors, {recovery_tool} is a common recovery step.",
        "evidenceCount": count,
        "confidence": confidence_for_count(count),
        "lastSeenAt": last_seen,
    }


def _build_workflow_entry(key: str, count: int, last_seen: str) -> dict[str, Any]:
    left_skill, right_skill = key.split(" -> ", maxsplit=1)
    return {
        "key": key,
        "trigger": f"{left_skill} completed",
        "action": f"Invoke {right_skill}",
        "guidance": f"Common skill workflow: {key}.",
        "evidenceCount": count,
        "confidence": confidence_for_count(count),
        "lastSeenAt": last_seen,
    }


def _detect_skill_workflows(project_root: Path) -> Counter[str]:
    """Detect skill-to-skill workflow sequences from framework events."""
    path = framework_events_path(project_root)
    if not path.exists():
        return Counter()
    events = read_ndjson_entries(path, FrameworkEvent)
    skill_events = [e for e in events if e.kind == "skill_invoked"]
    if not skill_events:
        return Counter()

    grouped: dict[str, list[FrameworkEvent]] = defaultdict(list)
    for event in skill_events:
        session_key = event.correlation_id or event.session_id or "default"
        grouped[session_key].append(event)

    counts: Counter[str] = Counter()
    for entries in grouped.values():
        entries.sort(key=lambda e: e.timestamp)
        skill_names = []
        for entry in entries:
            skill = entry.detail.get("skill") or entry.component or ""
            if skill:
                skill_names.append(str(skill))
        for left, right in pairwise(skill_names):
            counts[f"{left} -> {right}"] += 1
    return counts


def confidence_for_count(n: int) -> float:
    """Return a confidence score based on evidence count."""
    if n >= 10:
        return 0.85
    if n >= 6:
        return 0.7
    if n >= 3:
        return 0.5
    return 0.3


def _migrate_v1_to_v2(document: dict[str, Any]) -> dict[str, Any]:
    """Migrate a v1 instincts document to v2 schema."""
    workflows: list[dict[str, Any]] = []
    for entry in document.get("toolSequences", []):
        if int(entry.get("evidenceCount", 0)) >= 5:
            key = str(entry.get("key", ""))
            parts = key.split(" -> ", maxsplit=1)
            trigger = f"{parts[0]} completed" if len(parts) == 2 else key
            action = f"Invoke {parts[1]}" if len(parts) == 2 else key
            workflows.append(
                {
                    "key": key,
                    "trigger": trigger,
                    "action": action,
                    "guidance": entry.get("guidance", f"Common skill workflow: {key}."),
                    "evidenceCount": entry.get("evidenceCount", 0),
                    "confidence": confidence_for_count(entry.get("evidenceCount", 0)),
                    "lastSeenAt": entry.get("lastSeenAt", _iso_now()),
                }
            )

    return {
        "schemaVersion": "2.0",
        "updatedAt": document.get("updatedAt", _iso_now()),
        "corrections": [],
        "recoveries": [],
        "workflows": workflows,
    }


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
