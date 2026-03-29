"""Stdlib-only instinct learning for hook scripts.

Replicates the behaviour of ``ai_engineering.state.instincts`` without
Pydantic models or pip-package imports.  Uses plain dicts + NDJSON I/O.

``_detect_skill_agent_preferences`` is intentionally excluded to avoid a
circular dependency on FrameworkEvent via Pydantic.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

try:
    import yaml

    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False

# ---------------------------------------------------------------------------
# Constants (match ai_engineering.state.instincts exactly)
# ---------------------------------------------------------------------------

OBSERVATION_RETENTION_DAYS = 30
MAX_SUMMARY_LEN = 160
MAX_CONTEXT_ITEMS = 5
INSTINCTS_SCHEMA_VERSION = "1.0"
INSTINCT_CONTEXT_HEADER = "# Instinct Context"

INSTINCT_OBSERVATIONS_REL = ".ai-engineering/state/instinct-observations.ndjson"
INSTINCTS_REL = ".ai-engineering/instincts/instincts.yml"
INSTINCT_CONTEXT_REL = ".ai-engineering/instincts/context.md"
INSTINCT_META_REL = ".ai-engineering/instincts/meta.json"

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

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _obs_path(project_root: Path) -> Path:
    return project_root / INSTINCT_OBSERVATIONS_REL


def _instincts_path(project_root: Path) -> Path:
    return project_root / INSTINCTS_REL


def _context_path(project_root: Path) -> Path:
    return project_root / INSTINCT_CONTEXT_REL


def _meta_path(project_root: Path) -> Path:
    return project_root / INSTINCT_META_REL


# ---------------------------------------------------------------------------
# NDJSON I/O (replaces ai_engineering.state.io)
# ---------------------------------------------------------------------------


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def _append_ndjson(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, default=_json_serializer) + "\n")


def _write_ndjson(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, sort_keys=True, default=_json_serializer) for e in entries]
    path.write_text(("\n".join(lines) + ("\n" if lines else "")), encoding="utf-8")


# ---------------------------------------------------------------------------
# JSON / YAML helpers
# ---------------------------------------------------------------------------


def _json_serializer(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    # Accept both "...Z" and "+00:00" suffixes
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON file, gracefully handling missing yaml lib."""
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    if _HAS_YAML:
        return yaml.safe_load(raw) or {}
    return json.loads(raw) if raw else {}


def _dump_yaml_or_json(path: Path, data: dict[str, Any]) -> None:
    """Write a dict as YAML (preferred) or JSON (fallback)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if _HAS_YAML:
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(
            json.dumps(data, indent=2, sort_keys=False, default=_json_serializer) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Default document / meta factories
# ---------------------------------------------------------------------------


def _default_instincts_document() -> dict[str, Any]:
    return {
        "schemaVersion": INSTINCTS_SCHEMA_VERSION,
        "updatedAt": _iso_now(),
        "toolSequences": [],
        "errorRecoveries": [],
    }


def _default_meta() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "lastExtractedAt": None,
        "lastContextGeneratedAt": None,
        "pendingContextRefresh": False,
        "deltaThreshold": 10,
        "contextMaxAgeHours": 24,
    }


def _default_context_text() -> str:
    return (
        f"{INSTINCT_CONTEXT_HEADER}\n\n"
        "No active instincts yet. Capture more sessions before loading this context.\n"
    )


# ---------------------------------------------------------------------------
# ensure_instinct_artifacts
# ---------------------------------------------------------------------------


def ensure_instinct_artifacts(project_root: Path) -> None:
    """Create observation, instincts, context, and meta files if missing."""
    obs = _obs_path(project_root)
    obs.parent.mkdir(parents=True, exist_ok=True)
    if not obs.exists():
        obs.write_text("", encoding="utf-8")

    inst = _instincts_path(project_root)
    inst.parent.mkdir(parents=True, exist_ok=True)
    if not inst.exists():
        _dump_yaml_or_json(inst, _default_instincts_document())

    ctx = _context_path(project_root)
    if not ctx.exists():
        ctx.write_text(_default_context_text(), encoding="utf-8")

    meta = _meta_path(project_root)
    if not meta.exists():
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(
            json.dumps(_default_meta(), indent=2, default=_json_serializer) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Meta load / save
# ---------------------------------------------------------------------------


def _load_meta(project_root: Path) -> dict[str, Any]:
    ensure_instinct_artifacts(project_root)
    path = _meta_path(project_root)
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = _default_meta()
    meta.update(raw)
    return meta


def _save_meta(project_root: Path, meta: dict[str, Any]) -> None:
    path = _meta_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(meta, indent=2, default=_json_serializer) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Instincts document load / save
# ---------------------------------------------------------------------------


def _load_instincts_document(project_root: Path) -> dict[str, Any]:
    ensure_instinct_artifacts(project_root)
    raw = _load_yaml_or_json(_instincts_path(project_root))
    doc = _default_instincts_document()
    doc.update(raw)
    doc["toolSequences"] = list(doc.get("toolSequences") or [])
    doc["errorRecoveries"] = list(doc.get("errorRecoveries") or [])
    return doc


def _save_instincts_document(project_root: Path, document: dict[str, Any]) -> None:
    ensure_instinct_artifacts(project_root)
    document["schemaVersion"] = INSTINCTS_SCHEMA_VERSION
    document["updatedAt"] = _iso_now()
    _dump_yaml_or_json(_instincts_path(project_root), document)


# ---------------------------------------------------------------------------
# Observation reading / writing / pruning
# ---------------------------------------------------------------------------


def _read_observations(project_root: Path) -> list[dict[str, Any]]:
    ensure_instinct_artifacts(project_root)
    return _read_ndjson(_obs_path(project_root))


def _write_observations(project_root: Path, entries: list[dict[str, Any]]) -> None:
    _write_ndjson(_obs_path(project_root), entries)


def prune_instinct_observations(
    project_root: Path,
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Remove observations older than OBSERVATION_RETENTION_DAYS."""
    cutoff = (now or datetime.now(tz=UTC)) - timedelta(days=OBSERVATION_RETENTION_DAYS)
    all_obs = _read_observations(project_root)
    kept = [entry for entry in all_obs if _obs_timestamp(entry) >= cutoff]
    _write_observations(project_root, kept)
    return kept


def _obs_timestamp(entry: dict[str, Any]) -> datetime:
    """Parse the ISO timestamp from an observation dict."""
    ts = _parse_iso(str(entry.get("timestamp", "")))
    if ts is None:
        return datetime.min.replace(tzinfo=UTC)
    return ts


# ---------------------------------------------------------------------------
# Text / mapping helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Outcome derivation
# ---------------------------------------------------------------------------


def _derive_outcome(data: dict[str, Any]) -> str:
    for key in ("error", "tool_error", "exception"):
        if data.get(key):
            return "failure"
    result = _coerce_text(data.get("result") or data.get("tool_result"))
    if result and any(token in result.lower() for token in _ERROR_HINTS):
        return "failure"
    return "success" if data.get("tool_name") else "unknown"


# ---------------------------------------------------------------------------
# Observation detail builder
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Session ID extraction
# ---------------------------------------------------------------------------


def _extract_session_id(data: dict[str, Any]) -> str | None:
    value = data.get("session_id") or data.get("sessionId")
    return str(value) if value else None


# ---------------------------------------------------------------------------
# Filtering / grouping
# ---------------------------------------------------------------------------


def _filter_new_observations(
    observations: list[dict[str, Any]],
    last_extracted_at: datetime | None,
) -> list[dict[str, Any]]:
    if last_extracted_at is None:
        return observations
    return [entry for entry in observations if _obs_timestamp(entry) > last_extracted_at]


def _group_by_session(
    observations: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in observations:
        grouped[entry.get("sessionId") or "default"].append(entry)
    for entries in grouped.values():
        entries.sort(key=lambda item: item.get("timestamp", ""))
    return grouped


# ---------------------------------------------------------------------------
# Pattern detectors
# ---------------------------------------------------------------------------


def _detect_tool_sequences(
    sessions: dict[str, list[dict[str, Any]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entries in sessions.values():
        sequence = [e["tool"] for e in entries if e.get("kind") == "tool_start"]
        for left, right in pairwise(sequence):
            counts[f"{left} -> {right}"] += 1
    return counts


def _detect_error_recoveries(
    sessions: dict[str, list[dict[str, Any]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entries in sessions.values():
        for current, nxt in pairwise(entries):
            if current.get("kind") != "tool_complete" or current.get("outcome") != "failure":
                continue
            if nxt.get("kind") != "tool_start":
                continue
            counts[f"{current['tool']} -> {nxt['tool']}"] += 1
    return counts


# ---------------------------------------------------------------------------
# Merge / select helpers
# ---------------------------------------------------------------------------


def _build_error_recovery_entry(key: str, count: int, last_seen: str) -> dict[str, Any]:
    failed_tool, recovery_tool = key.split(" -> ", maxsplit=1)
    return {
        "key": key,
        "guidance": f"After {failed_tool} errors, {recovery_tool} is a common recovery step.",
        "evidenceCount": count,
        "lastSeenAt": last_seen,
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


def _select_context_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for key in ("toolSequences", "errorRecoveries"):
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def append_instinct_observation(
    project_root: Path,
    *,
    engine: str,
    hook_event: str,
    data: dict[str, Any],
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Append a single instinct observation.  Returns the dict or None."""
    ensure_instinct_artifacts(project_root)

    tool = str(data.get("tool_name") or "").strip()
    if not tool:
        return None

    observation: dict[str, Any] = {
        "schemaVersion": "1.0",
        "timestamp": _iso_now(),
        "engine": engine,
        "kind": "tool_start" if hook_event == "PreToolUse" else "tool_complete",
        "tool": tool,
        "outcome": _derive_outcome(data),
        "sessionId": session_id or _extract_session_id(data),
        "detail": _build_observation_detail(data, hook_event=hook_event),
    }

    # Prune old entries, then append new
    entries = prune_instinct_observations(project_root)
    entries.append(observation)
    _write_observations(project_root, entries)
    return observation


def extract_instincts(project_root: Path) -> bool:
    """Extract tool-sequence and error-recovery patterns.  Returns True if new."""
    ensure_instinct_artifacts(project_root)
    meta = _load_meta(project_root)
    observations = prune_instinct_observations(project_root)
    last_extracted = _parse_iso(meta.get("lastExtractedAt"))
    new_observations = _filter_new_observations(observations, last_extracted)
    if not new_observations:
        return False

    document = _load_instincts_document(project_root)
    sessions = _group_by_session(new_observations)
    sequence_counts = _detect_tool_sequences(sessions)
    recovery_counts = _detect_error_recoveries(sessions)

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
    _save_instincts_document(project_root, document)

    # Update meta bookkeeping
    newest = max(
        (_obs_timestamp(e) for e in new_observations),
        default=None,
    )
    if newest:
        meta["lastExtractedAt"] = newest.strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["pendingContextRefresh"] = True
    _save_meta(project_root, meta)
    return True


def maybe_refresh_instinct_context(project_root: Path) -> bool:
    """Regenerate context.md if needed.  Returns True if refreshed."""
    should_refresh, _ = _needs_context_refresh(project_root)
    if not should_refresh:
        return False
    _refresh_instinct_context(project_root)
    return True


# ---------------------------------------------------------------------------
# Context refresh internals
# ---------------------------------------------------------------------------


def _needs_context_refresh(
    project_root: Path,
    *,
    now: datetime | None = None,
) -> tuple[bool, dict[str, Any]]:
    ensure_instinct_artifacts(project_root)
    current = now or datetime.now(tz=UTC)
    meta = _load_meta(project_root)
    observations = prune_instinct_observations(project_root, now=current)
    ctx = _context_path(project_root)
    last_context = _parse_iso(meta.get("lastContextGeneratedAt"))
    delta_count = sum(
        1 for entry in observations if last_context is None or _obs_timestamp(entry) > last_context
    )
    max_age_hours = int(meta.get("contextMaxAgeHours", 24))
    stale = (
        last_context is None
        or not ctx.exists()
        or (current - last_context) >= timedelta(hours=max_age_hours)
    )
    threshold = int(meta.get("deltaThreshold", 10))
    should_refresh = bool(meta.get("pendingContextRefresh")) or stale or delta_count >= threshold
    return should_refresh, {
        "delta_count": delta_count,
        "stale": stale,
        "pending_context_refresh": bool(meta.get("pendingContextRefresh")),
    }


def _refresh_instinct_context(project_root: Path) -> str:
    ensure_instinct_artifacts(project_root)
    document = _load_instincts_document(project_root)
    lines = [INSTINCT_CONTEXT_HEADER, ""]
    items = _select_context_items(document)
    if not items:
        lines.append("No active instincts yet. Capture more sessions before loading this context.")
    else:
        for item in items:
            lines.append(f"- {item['guidance']} Evidence: {item['evidenceCount']} observations.")
    content = "\n".join(lines).rstrip() + "\n"
    _context_path(project_root).write_text(content, encoding="utf-8")

    meta = _load_meta(project_root)
    meta["lastContextGeneratedAt"] = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["pendingContextRefresh"] = False
    _save_meta(project_root, meta)
    return content
