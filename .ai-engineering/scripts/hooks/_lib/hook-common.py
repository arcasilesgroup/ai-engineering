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

_FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


# ---------------------------------------------------------------------------
# 1. validate_event_schema -- mirrors src/ai_engineering/state/event_schema.py
# ---------------------------------------------------------------------------


def validate_event_schema(event: object) -> bool:
    """Return True iff event matches the unified schema (spec-112 G-4)."""
    if not isinstance(event, dict):
        return False
    for key in _REQUIRED_KEYS:
        if key not in event:
            return False
        value = event[key]
        if value is None or value == "":
            return False
    engine = event.get("engine")
    if not isinstance(engine, str) or engine not in _ALLOWED_ENGINES:
        return False
    detail = event.get("detail", {})
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
    if not validate_event_schema(event):
        logger.error(
            "hook-common: refusing to emit malformed event (kind=%s engine=%s)",
            event.get("kind") if isinstance(event, dict) else None,
            event.get("engine") if isinstance(event, dict) else None,
        )
        return False
    path = _events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
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


__all__ = [
    "compute_event_hash",
    "emit_event",
    "get_correlation_id",
    "get_session_id",
    "now_monotonic_ms",
    "read_stdin_json",
    "validate_event_schema",
]
