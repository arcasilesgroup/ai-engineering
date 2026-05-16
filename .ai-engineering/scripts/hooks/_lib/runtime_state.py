"""Runtime state primitives for harness hooks (spec-116 G-1).

Shared helpers for the Runtime Layer hooks introduced to close the gaps
identified in the harness audit:

* tool-call offloading (large stdout/stderr → filesystem)
* loop-detection middleware (sliding window of recent tool calls)
* checkpoint / resume markers (Ralph Loop, mid-task crash recovery)
* compaction snapshots (critical state preserved before context drop)
* progressive disclosure (per-prompt top-K skill ranking)

Sealed contract: stdlib-only. Same constraint as the rest of ``_lib``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _lib.hook_context import RUNTIME_DIR

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
#
# Spec-125 Wave 2b corrective: every active path resolution flows through
# the ``RUNTIME_DIR(project_root)`` factory in ``_lib/hook_context.py``
# (canonical ``.ai-engineering/runtime/...``). The ``*_REL`` constants
# below are retained as backwards-compatible re-exports in ``__all__`` so
# any out-of-tree consumer that imports them keeps loading, but they are
# *not* used by the helper functions. Updating a path now means editing
# ``hook_context.RUNTIME_DIR`` plus the per-file leaf names below.
#
# Choice: factory-functions-take-project-root. Selected because every
# existing call site already passes ``project_root`` to the helpers
# (``runtime_dir(project_root)``, ``tool_outputs_dir(project_root)``,
# ...). Module-level constants would have required threading
# ``project_root`` through additional code paths.

# Filename leaves -- single source of truth for the basenames.
_TOOL_OUTPUTS_NAME = "tool-outputs"
_TOOL_HISTORY_NAME = "tool-history.ndjson"
_CHECKPOINT_NAME = "checkpoint.json"
_RALPH_RESUME_NAME = "ralph-resume.json"
_PRECOMPACT_SNAPSHOT_NAME = "precompact-snapshot.json"
_EVENT_SIDECARS_NAME = "event-sidecars"

# Legacy ``*_REL`` constants retained for backwards-compatible re-export
# only -- do NOT use these for new code. They reference the pre-Wave-2b
# ``state/runtime`` location and are kept solely so any external import
# path keeps resolving. Active path resolution flows through the
# helper functions below (which use ``RUNTIME_DIR``).
RUNTIME_DIR_REL = Path(".ai-engineering") / "state" / "runtime"
TOOL_OUTPUTS_DIR_REL = RUNTIME_DIR_REL / _TOOL_OUTPUTS_NAME
TOOL_HISTORY_REL = RUNTIME_DIR_REL / _TOOL_HISTORY_NAME
CHECKPOINT_REL = RUNTIME_DIR_REL / _CHECKPOINT_NAME
RALPH_RESUME_REL = RUNTIME_DIR_REL / _RALPH_RESUME_NAME
PRECOMPACT_SNAPSHOT_REL = RUNTIME_DIR_REL / _PRECOMPACT_SNAPSHOT_NAME
# spec-123 D-123-23: oversized framework events offload to a content-addressed
# sidecar dir under runtime/ so the inline NDJSON line stays under the
# POSIX_BUF (4 KB) atomic-append guarantee.
EVENT_SIDECARS_DIR_REL = RUNTIME_DIR_REL / _EVENT_SIDECARS_NAME

# ---------------------------------------------------------------------------
# Tunables (override via env if site needs different thresholds)
# ---------------------------------------------------------------------------


def _env_int(name: str, default: int, *, ceiling: int | None = None) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    if ceiling is not None and value > ceiling:
        return ceiling
    return value


# Tool-call offload threshold (bytes). Outputs above this go to disk.
# 16 KiB default: smaller outputs cost more in context-hint bytes than they save.
TOOL_OFFLOAD_BYTES = _env_int("AIENG_TOOL_OFFLOAD_BYTES", 16384, ceiling=8 * 1024 * 1024)
# Head/tail kept inline when offloading.
TOOL_OFFLOAD_HEAD = _env_int("AIENG_TOOL_OFFLOAD_HEAD", 1024, ceiling=64 * 1024)
TOOL_OFFLOAD_TAIL = _env_int("AIENG_TOOL_OFFLOAD_TAIL", 512, ceiling=64 * 1024)

# Cap for tool_response flatten before signature/offload eats memory.
# Couples to TOOL_OFFLOAD_BYTES upper bound: never truncate below the offload threshold.
TOOL_RESPONSE_FLATTEN_CAP = max(TOOL_OFFLOAD_BYTES * 4, 1 << 16)

# Tools that already surface their full payload to the model (Read, Glob, Grep, etc.)
# Offloading these wastes I/O and inflates context with a "fetch from path" hint.
TOOL_OFFLOAD_SKIP = frozenset({"Read", "Glob", "Grep", "TodoWrite"})

# Cap on number of files retained in tool-outputs/. Older files GC'd opportunistically.
TOOL_OUTPUTS_FILE_CAP = _env_int("AIENG_TOOL_OUTPUTS_FILE_CAP", 200, ceiling=10_000)

# Loop-detection: window size + repetition threshold.
LOOP_WINDOW = _env_int("AIENG_LOOP_WINDOW", 6, ceiling=200)
LOOP_REPEAT_THRESHOLD = _env_int("AIENG_LOOP_REPEAT_THRESHOLD", 3, ceiling=200)

# Tool history retention (max records kept on disk).
TOOL_HISTORY_MAX = _env_int("AIENG_TOOL_HISTORY_MAX", 500, ceiling=10_000)

# spec-123 D-123-23: oversized event-sidecar offload threshold (bytes).
# Events whose serialised JSON exceeds this ceiling are written to a
# content-addressed sidecar file under runtime/event-sidecars/ and the
# inline event carries only the sha256 + summary. Default 3 KB sits
# below the 4 KB POSIX PIPE_BUF guarantee for atomic appends.
EVENT_SIDECAR_BYTES = _env_int("AIENG_EVENT_SIDECAR_BYTES", 3072, ceiling=64 * 1024)
# Trim threshold: amortise rewrites by only trimming when file grows beyond
# steady-state (~180 B/line x TOOL_HISTORY_MAX x 1.5 buffer).
_TOOL_HISTORY_TRIM_BYTES = max(256 * 1024, TOOL_HISTORY_MAX * 280)
# NDJSON tail-byte read window: covers ~LOOP_WINDOW * 4 records of typical 180 B size.
_NDJSON_TAIL_BYTES = 32 * 1024


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def runtime_dir(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root)


def tool_outputs_dir(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _TOOL_OUTPUTS_NAME


def tool_history_path(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _TOOL_HISTORY_NAME


def checkpoint_path(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _CHECKPOINT_NAME


def ralph_resume_path(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _RALPH_RESUME_NAME


def precompact_snapshot_path(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _PRECOMPACT_SNAPSHOT_NAME


def event_sidecars_dir(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _EVENT_SIDECARS_NAME


def ensure_runtime_dirs(project_root: Path) -> None:
    """Create runtime/ + tool-outputs/ if missing. Idempotent.

    tool-outputs/ holds offloaded tool payloads that may include redacted-but-
    sensitive content (file paths, env vars, diff bodies). Tightened to 0o700
    so peers on a multi-user host can't enumerate or read.
    """
    runtime_dir(project_root).mkdir(parents=True, exist_ok=True)
    out_dir = tool_outputs_dir(project_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        out_dir.chmod(0o700)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# JSON I/O (resilient to malformed lines)
# ---------------------------------------------------------------------------


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def append_ndjson(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, sort_keys=True, default=str)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_ndjson_tail(path: Path, limit: int) -> list[dict]:
    """Return up to `limit` most recent dict-typed records (skip bad lines).

    Tail-byte read: seek to end-window so cost is O(window) not O(file size).
    Drops the first (possibly partial) line in the window to avoid mid-line splits.
    """
    if not path.exists() or limit <= 0:
        return []
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            window = max(_NDJSON_TAIL_BYTES, limit * 512)
            fh.seek(max(0, size - window))
            buf = fh.read()
    except OSError:
        return []
    text = buf.decode("utf-8", errors="replace")
    lines = text.splitlines()
    # If window started mid-file, the first line is likely a partial — drop it.
    if size > window and lines:
        lines = lines[1:]
    out: list[dict] = []
    for line in reversed(lines):
        if len(out) >= limit:
            break
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    out.reverse()
    return out


# ---------------------------------------------------------------------------
# Tool-call signature (loop detection)
# ---------------------------------------------------------------------------


_SECRET_RE = re.compile(
    r"(?i)(api_key|token|secret|password|authorization|credentials|auth)"
    r"([\"'\s:=]+)[^\s\"',;]{4,}",
)


def redact(text: str) -> str:
    return _SECRET_RE.sub(r"\1\2[REDACTED]", text)


def tool_signature(tool_name: str, tool_input: dict) -> str:
    """Stable sha1-prefix signature for repetition detection.

    Reduces the tool input to a canonical JSON form (sort keys, redact
    secrets) and hashes the first 12 hex chars. Same call ⇒ same sig.
    """
    safe_input = {k: v for k, v in tool_input.items() if k not in {"session_id"}}
    payload = json.dumps(safe_input, sort_keys=True, default=str)[:4096]
    payload = redact(payload)
    raw = f"{tool_name}|{payload}".encode()
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Tool history (sliding window persistence)
# ---------------------------------------------------------------------------


@dataclass
class ToolHistoryEntry:
    timestamp: str
    session_id: str | None
    tool: str
    signature: str
    outcome: str
    error_summary: str | None
    # File touched by Edit/Write/MultiEdit (None for non-file tools). Lets the
    # checkpoint→episode bridge (runtime-stop) recover edited paths from a single
    # source of truth instead of scanning framework-events for an event that
    # auto-format never emits.
    file_path: str | None = None

    def to_dict(self) -> dict:
        payload: dict = {
            "timestamp": self.timestamp,
            "sessionId": self.session_id,
            "tool": self.tool,
            "signature": self.signature,
            "outcome": self.outcome,
            "errorSummary": self.error_summary,
        }
        if self.file_path:
            payload["filePath"] = self.file_path
        return payload


def append_tool_history(project_root: Path, entry: ToolHistoryEntry) -> None:
    """Append + truncate to TOOL_HISTORY_MAX so the file stays bounded.

    Trim threshold is set above steady-state file size so the trim path doesn't
    run on every PostToolUse — only when the file actually grew unbounded.
    """
    path = tool_history_path(project_root)
    append_ndjson(path, entry.to_dict())
    try:
        if path.stat().st_size < _TOOL_HISTORY_TRIM_BYTES:
            return
    except OSError:
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) <= TOOL_HISTORY_MAX:
        return
    keep = lines[-TOOL_HISTORY_MAX:]
    path.write_text("\n".join(keep) + "\n", encoding="utf-8")


def _gc_tool_outputs(directory: Path, *, cap: int = TOOL_OUTPUTS_FILE_CAP) -> None:
    """Drop oldest files when directory exceeds cap. Best-effort, swallows IO errors."""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return
    if len(entries) <= cap:
        return
    try:
        entries.sort(key=lambda p: p.stat().st_mtime)
    except OSError:
        return
    for old in entries[: len(entries) - cap]:
        try:
            old.unlink()
        except OSError:
            continue


def recent_tool_history(
    project_root: Path,
    *,
    session_id: str | None = None,
    limit: int = LOOP_WINDOW,
) -> list[dict]:
    """Last `limit` records, optionally filtered to a session."""
    raw = read_ndjson_tail(tool_history_path(project_root), limit * 4)
    if session_id is None:
        return raw[-limit:]
    filtered = [r for r in raw if r.get("sessionId") == session_id]
    return filtered[-limit:]


# ---------------------------------------------------------------------------
# Loop detection
# ---------------------------------------------------------------------------


def detect_repetition(
    history: list[dict],
    *,
    threshold: int = LOOP_REPEAT_THRESHOLD,
) -> tuple[bool, str | None]:
    """Return ``(loop_detected, reason)`` based on signature repetition.

    A loop is flagged when the same signature appears ``threshold`` or
    more times in the supplied window. Repeated *failures* are also
    considered loops because models routinely retry the same broken
    approach without changing inputs.
    """
    if not history:
        return False, None
    signatures = [r.get("signature") for r in history if r.get("signature")]
    if not signatures:
        return False, None
    counts: dict[str, int] = {}
    for sig in signatures:
        counts[sig] = counts.get(sig, 0) + 1
    most_sig, most_n = max(counts.items(), key=lambda kv: kv[1])
    if most_n >= threshold:
        last_record = next(
            (r for r in reversed(history) if r.get("signature") == most_sig),
            None,
        )
        tool = (last_record or {}).get("tool", "<unknown>")
        return True, (
            f"signature {most_sig} repeated {most_n}x in last {len(history)} calls (tool={tool})"
        )
    # Repeated failures even with different signatures still smell like a loop.
    failures = [r for r in history if r.get("outcome") == "failure"]
    if len(failures) >= threshold:
        return True, (f"{len(failures)} failures in last {len(history)} calls — agent is thrashing")
    return False, None


# ---------------------------------------------------------------------------
# Tool output offload helpers
# ---------------------------------------------------------------------------


def offload_large_text(
    project_root: Path,
    *,
    correlation_id: str,
    tool_name: str,
    text: str,
) -> dict[str, Any]:
    """Persist `text` if it exceeds the offload threshold.

    Returns a dict with the head/tail snippet, full path (when offloaded),
    and the byte counts. Caller decides how to surface this to the model.

    Security posture:
    * Payload is redacted via `redact()` before write (tool outputs routinely
      contain `cat .env`, env dumps, HTTP bodies on a multi-user host).
    * File written with mode 0o600 + O_NOFOLLOW so it's not world-readable
      and a pre-existing symlink in tool-outputs/ cannot redirect the write.
    * Directory mode tightened to 0o700 in `ensure_runtime_dirs`.
    * Opportunistic GC keeps the directory bounded at TOOL_OUTPUTS_FILE_CAP.
    """
    encoded = text.encode("utf-8", errors="replace")
    total = len(encoded)
    summary: dict[str, Any] = {
        "tool": tool_name,
        "totalBytes": total,
        "offloaded": False,
    }
    if total <= TOOL_OFFLOAD_BYTES:
        summary["preview"] = text
        return summary
    ensure_runtime_dirs(project_root)
    out_dir = tool_outputs_dir(project_root)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", correlation_id)[:48] or "anon"
    redacted_text = redact(text)
    redacted_encoded = redacted_text.encode("utf-8", errors="replace")
    base_name = f"{iso_now().replace(':', '')}-{safe_id}"
    out_path = out_dir / f"{base_name}.txt"
    # Cross-OS: `O_NOFOLLOW` is POSIX-only -- Windows has no symlink semantics
    # at the filesystem layer that this flag protects against. Falling back to
    # 0 on Windows preserves the security posture on POSIX (where the flag
    # genuinely matters) without breaking import on win32.
    _O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
    attempt = 0
    while True:
        try:
            fd = os.open(
                str(out_path),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            attempt += 1
            if attempt > 5:
                # Give up rather than overwrite; head+tail still surfaces in summary.
                break
            out_path = out_dir / f"{base_name}-{attempt}.txt"
            continue
        except OSError:
            break
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(redacted_encoded)
        except OSError:
            with contextlib.suppress(OSError):
                out_path.unlink()
            break
        head = redacted_encoded[:TOOL_OFFLOAD_HEAD].decode("utf-8", errors="replace")
        tail = redacted_encoded[-TOOL_OFFLOAD_TAIL:].decode("utf-8", errors="replace")
        summary.update(
            {
                "offloaded": True,
                "head": head,
                "tail": tail,
                "headBytes": min(TOOL_OFFLOAD_HEAD, total),
                "tailBytes": min(TOOL_OFFLOAD_TAIL, total),
                "path": str(out_path.relative_to(project_root)),
            }
        )
        _gc_tool_outputs(out_dir)
        return summary
    # Fall-through: write failed or filename collisions exhausted. Surface a
    # head+tail-only summary so the caller still gets context, but flag offload as
    # incomplete so the hook does not pretend a path exists.
    head = encoded[:TOOL_OFFLOAD_HEAD].decode("utf-8", errors="replace")
    tail = encoded[-TOOL_OFFLOAD_TAIL:].decode("utf-8", errors="replace")
    summary.update(
        {
            "offloaded": False,
            "head": head,
            "tail": tail,
            "headBytes": min(TOOL_OFFLOAD_HEAD, total),
            "tailBytes": min(TOOL_OFFLOAD_TAIL, total),
            "writeFailed": True,
        }
    )
    return summary


# ---------------------------------------------------------------------------
# Event sidecar offload (spec-123 D-123-23)
# ---------------------------------------------------------------------------


def _serialise_event(event: dict) -> bytes:
    """Canonical JSON encoding of an event (sorted keys, compact separators).

    Matches :func:`ai_engineering.state.sidecar._serialize` so the bytes
    counted here are the same bytes that would land in the NDJSON line.
    """
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _event_summary(event: dict, max_chars: int = 160) -> str:
    """Build a stable one-line summary for an oversized event."""
    kind = event.get("kind") or "unknown"
    component = event.get("component") or ""
    detail = event.get("detail")
    detail_summary: str
    if isinstance(detail, dict):
        fragments: list[str] = []
        for key in ("operation", "tool", "skill", "agent", "error_code"):
            value = detail.get(key)
            if isinstance(value, str) and value:
                fragments.append(f"{key}={value}")
        detail_summary = " ".join(fragments) if fragments else f"keys={','.join(sorted(detail))}"
    elif isinstance(detail, list):
        detail_summary = f"list[{len(detail)}]"
    else:
        detail_summary = ""
    base = f"[{kind}@{component}] {detail_summary}".strip()
    return base[:max_chars]


def maybe_offload_event(
    project_root: Path,
    event: dict,
    *,
    ceiling: int | None = None,
) -> dict:
    """Offload oversized events to a content-addressed sidecar.

    Returns the original event unchanged when its serialised form is at or
    below ``ceiling`` bytes. Otherwise writes the full event to
    ``runtime/event-sidecars/<sha256>.json`` and returns a small inline
    replacement carrying the sha256 + summary + correlation pointers so
    audit-chain reasoning still works on the projection.

    Mirrors :func:`ai_engineering.state.sidecar.maybe_offload` but lives in
    ``_lib`` so the hook layer (which intentionally avoids importing
    ``ai_engineering`` to stay stdlib-only and fast) can call it directly.
    """
    threshold = ceiling if ceiling is not None else EVENT_SIDECAR_BYTES
    payload = _serialise_event(event)
    if len(payload) <= threshold:
        return event

    digest = hashlib.sha256(payload).hexdigest()
    sidecar_dir = event_sidecars_dir(project_root)
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = sidecar_dir / f"{digest}.json"
    if not sidecar_path.exists():
        # Atomic write via tmp + rename to avoid partial-write windows.
        tmp_path = sidecar_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_bytes(payload)
            os.replace(tmp_path, sidecar_path)
        except OSError:
            # Fail-open: surface the original event rather than dropping it.
            with contextlib.suppress(OSError):
                tmp_path.unlink()
            return event

    inline: dict[str, Any] = {
        "kind": event.get("kind") or "unknown",
        "engine": event.get("engine") or "unknown",
        "component": event.get("component") or "unknown",
        "outcome": event.get("outcome") or "success",
        "timestamp": event.get("timestamp") or "",
        "sidecar_sha256": digest,
        "sidecar_size_bytes": len(payload),
        "summary": _event_summary(event),
    }
    for key in (
        "correlationId",
        "correlation_id",
        "session_id",
        "trace_id",
        "span_id",
        "parent_span_id",
        "prev_event_hash",
    ):
        if key in event and event[key] is not None:
            inline[key] = event[key]
    return inline


# ---------------------------------------------------------------------------
# Misc helpers consumed by hooks
# ---------------------------------------------------------------------------


def derive_outcome(data: dict) -> str:
    """Extract a coarse outcome ('success'|'failure') from a tool payload."""
    response = data.get("tool_response") or {}
    if isinstance(response, dict) and (response.get("error") or response.get("is_error")):
        return "failure"
    if data.get("error") or data.get("is_error"):
        return "failure"
    return "success"


def extract_error_summary(data: dict) -> str | None:
    response = data.get("tool_response") or {}
    candidates: list[str] = []
    if isinstance(response, dict):
        for key in ("error", "stderr", "message"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value)
    for key in ("error", "stderr"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value)
    if not candidates:
        return None
    return redact(candidates[0].strip())[:200]


__all__ = [
    "CHECKPOINT_REL",
    "EVENT_SIDECARS_DIR_REL",
    "EVENT_SIDECAR_BYTES",
    "LOOP_REPEAT_THRESHOLD",
    "LOOP_WINDOW",
    "PRECOMPACT_SNAPSHOT_REL",
    "RALPH_RESUME_REL",
    "RUNTIME_DIR_REL",
    "TOOL_HISTORY_MAX",
    "TOOL_HISTORY_REL",
    "TOOL_OFFLOAD_BYTES",
    "TOOL_OFFLOAD_HEAD",
    "TOOL_OFFLOAD_SKIP",
    "TOOL_OFFLOAD_TAIL",
    "TOOL_OUTPUTS_DIR_REL",
    "TOOL_OUTPUTS_FILE_CAP",
    "TOOL_RESPONSE_FLATTEN_CAP",
    "ToolHistoryEntry",
    "append_ndjson",
    "append_tool_history",
    "checkpoint_path",
    "derive_outcome",
    "detect_repetition",
    "ensure_runtime_dirs",
    "event_sidecars_dir",
    "extract_error_summary",
    "iso_now",
    "maybe_offload_event",
    "offload_large_text",
    "precompact_snapshot_path",
    "ralph_resume_path",
    "read_json",
    "read_ndjson_tail",
    "recent_tool_history",
    "redact",
    "runtime_dir",
    "tool_history_path",
    "tool_outputs_dir",
    "tool_signature",
    "write_json",
]
