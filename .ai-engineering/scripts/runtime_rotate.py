#!/usr/bin/env python3
"""Rotate `.ai-engineering/runtime/` per retention policy.

Hot-path budget: <100ms wall-clock for steady-state repos. Stdlib only.

Retention policy (per spec-127 cleanup):

| Subtree                      | Retention | Action on stale       |
|------------------------------|-----------|-----------------------|
| `runtime/tool-outputs/*.txt` | 7 days    | unlink                |
| `runtime/autopilot/sub-*`    | 30 days   | rmtree if mtime stale |
| `runtime/tool-history.ndjson`| 10000 lines / 5 MB | tail-truncate  |
| `runtime/checkpoint.json`    | session   | keep (transient)      |
| `runtime/risk-score.json`    | session   | keep (transient)      |
| `runtime/skills-index.json`  | session   | keep (regenerable)    |
| `runtime/ralph-resume.json`  | session   | keep (transient)      |

Idempotent. Fail-open: missing dirs no-op silently. Emits a
`framework_event` summary so cleanup is auditable.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME_DIR = ROOT / ".ai-engineering" / "runtime"

TOOL_OUTPUTS_DIR = RUNTIME_DIR / "tool-outputs"
AUTOPILOT_DIR = RUNTIME_DIR / "autopilot"
TOOL_HISTORY = RUNTIME_DIR / "tool-history.ndjson"

TOOL_OUTPUTS_TTL_SECONDS = 7 * 24 * 3600
AUTOPILOT_TTL_SECONDS = 30 * 24 * 3600
TOOL_HISTORY_MAX_LINES = 10_000
TOOL_HISTORY_MAX_BYTES = 5 * 1024 * 1024


def _now() -> float:
    return time.time()


def _rotate_tool_outputs(now: float) -> dict[str, int]:
    if not TOOL_OUTPUTS_DIR.is_dir():
        return {"deleted": 0, "kept": 0, "bytes_freed": 0}
    deleted = kept = bytes_freed = 0
    cutoff = now - TOOL_OUTPUTS_TTL_SECONDS
    for entry in TOOL_OUTPUTS_DIR.iterdir():
        if not entry.is_file():
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        if stat.st_mtime < cutoff:
            try:
                entry.unlink()
                deleted += 1
                bytes_freed += stat.st_size
            except OSError:
                kept += 1
        else:
            kept += 1
    return {"deleted": deleted, "kept": kept, "bytes_freed": bytes_freed}


def _rotate_autopilot(now: float) -> dict[str, int]:
    if not AUTOPILOT_DIR.is_dir():
        return {"deleted": 0, "kept": 0, "bytes_freed": 0}
    deleted = kept = bytes_freed = 0
    cutoff = now - AUTOPILOT_TTL_SECONDS
    for entry in AUTOPILOT_DIR.iterdir():
        if not entry.is_dir() or not entry.name.startswith("sub-"):
            continue
        try:
            mtime = max(
                (p.stat().st_mtime for p in entry.rglob("*") if p.is_file()),
                default=entry.stat().st_mtime,
            )
            size = sum(p.stat().st_size for p in entry.rglob("*") if p.is_file())
        except OSError:
            kept += 1
            continue
        if mtime < cutoff:
            try:
                shutil.rmtree(entry)
                deleted += 1
                bytes_freed += size
            except OSError:
                kept += 1
        else:
            kept += 1
    return {"deleted": deleted, "kept": kept, "bytes_freed": bytes_freed}


def _truncate_tool_history() -> dict[str, int]:
    if not TOOL_HISTORY.is_file():
        return {"truncated": 0, "lines_kept": 0, "bytes_freed": 0}
    try:
        size_before = TOOL_HISTORY.stat().st_size
    except OSError:
        return {"truncated": 0, "lines_kept": 0, "bytes_freed": 0}
    if size_before <= TOOL_HISTORY_MAX_BYTES:
        # Quick line-count check for byte-bound files.
        try:
            with TOOL_HISTORY.open("rb") as fh:
                lines = sum(1 for _ in fh)
        except OSError:
            return {"truncated": 0, "lines_kept": 0, "bytes_freed": 0}
        if lines <= TOOL_HISTORY_MAX_LINES:
            return {"truncated": 0, "lines_kept": lines, "bytes_freed": 0}
    # Tail-truncate to last TOOL_HISTORY_MAX_LINES lines.
    try:
        with TOOL_HISTORY.open("rb") as fh:
            data = fh.readlines()
        kept = data[-TOOL_HISTORY_MAX_LINES:]
        tmp = TOOL_HISTORY.with_suffix(".ndjson.tmp")
        with tmp.open("wb") as fh:
            fh.writelines(kept)
        tmp.replace(TOOL_HISTORY)
    except OSError:
        return {"truncated": 0, "lines_kept": 0, "bytes_freed": 0}
    try:
        size_after = TOOL_HISTORY.stat().st_size
    except OSError:
        size_after = size_before
    return {
        "truncated": 1,
        "lines_kept": len(kept),
        "bytes_freed": max(0, size_before - size_after),
    }


def _emit_event(payload: dict[str, object]) -> None:
    events_path = ROOT / ".ai-engineering" / "state" / "framework-events.ndjson"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "framework_event/1",
        "timestamp": datetime.now(UTC).isoformat(),
        "category": "runtime-rotate",
        "control": "retention",
        "outcome": "ok",
        "detail": payload,
    }
    try:
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    started = _now()
    payload = {
        "tool_outputs": _rotate_tool_outputs(started),
        "autopilot": _rotate_autopilot(started),
        "tool_history": _truncate_tool_history(),
        "elapsed_ms": int((_now() - started) * 1000),
    }
    _emit_event(payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
