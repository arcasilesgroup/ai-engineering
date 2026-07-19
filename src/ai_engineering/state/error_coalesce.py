"""Error / integrity storm coalescer (spec-190 D-190-02, pip twin).

Functional twin of the hook-side coalescer in
``.ai-engineering/scripts/hooks/_lib/runtime_state.py``. The hook ``_lib``
cannot import ``ai_engineering.*`` (sealed stdlib-only contract) and pip code
cannot import the hook ``_lib``, so the logic is intentionally duplicated. Both
writers target the SAME atomic JSON sidecar
(``.ai-engineering/runtime/error-coalesce.json``) with an identical schema so
repeated error/integrity emits collapse into one full event per window plus
periodic rollups, regardless of which writer records the occurrence.

The whole surface is fail-open: any read/write/parse failure degrades to a
first-occurrence verdict (``emit_full=True``) so no incident is silently lost.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

_ERROR_LEDGER_REL = Path(".ai-engineering") / "runtime" / "error-coalesce.json"

# Default rollup + storm threshold, reused as the rollup cadence so a storm and
# its first rollup coincide on the threshold-crossing occurrence.
_DEFAULT_ERROR_STORM_THRESHOLD = 20
# Default coalescing window (seconds); reuses the shared hot-path cache TTL.
_DEFAULT_ERROR_WINDOW_SEC = 300


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _error_storm_threshold() -> int:
    return _env_int("AIENG_ERROR_STORM_THRESHOLD", _DEFAULT_ERROR_STORM_THRESHOLD)


def _error_window_sec() -> int:
    return _env_int("AIENG_HOOK_CACHE_TTL_SEC", _DEFAULT_ERROR_WINDOW_SEC)


def error_ledger_path(project_root: Path) -> Path:
    return project_root / _ERROR_LEDGER_REL


def error_fingerprint(
    component: str | None,
    error_code: str | None,
    session_id: str | None,
    summary: str | None,
) -> str:
    """Stable 16-hex fingerprint over the coalescing key.

    Mirrors ``_lib.runtime_state.error_fingerprint`` byte-for-byte so the two
    writers agree on grouping for the shared sidecar.
    """
    bounded = (summary or "")[:200]
    raw = "\x1f".join(
        (
            component or "",
            error_code or "",
            session_id or "",
            bounded,
        )
    )
    return hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, sort_keys=True, default=str), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()


def _prune_error_entries(entries: dict, now: float, window: int) -> None:
    stale = [
        fp
        for fp, rec in list(entries.items())
        if not isinstance(rec, dict)
        or not isinstance(rec.get("first_seen"), (int, float))
        or (now - float(rec["first_seen"])) > window
    ]
    for fp in stale:
        entries.pop(fp, None)


def record_error(
    project_root: Path,
    fingerprint: str,
    *,
    component: str | None = None,
    error_code: str | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    """Record one error/integrity occurrence; decide whether to emit.

    See ``_lib.runtime_state.record_error`` for the full contract. Returns
    ``{emit_full, occurrences, storm_triggered, is_rollup}``. Fail-open.
    """
    fallback = {"emit_full": True, "occurrences": 1, "storm_triggered": False, "is_rollup": False}
    try:
        threshold = _error_storm_threshold()
        window = _error_window_sec()
        now = time.time()
        path = error_ledger_path(project_root)
        ledger = _read_json(path) or {}
        entries = ledger.get("fingerprints")
        if not isinstance(entries, dict):
            entries = {}

        rec = entries.get(fingerprint)
        if isinstance(rec, dict):
            first_seen = rec.get("first_seen")
            if not isinstance(first_seen, (int, float)) or (now - float(first_seen)) > window:
                rec = None
        else:
            rec = None

        if rec is None:
            entries[fingerprint] = {
                "first_seen": now,
                "last_seen": now,
                "count": 1,
                "storm_notified": False,
                "component": component,
                "error_code": error_code,
                "summary": (summary or "")[:200] or None,
            }
            _prune_error_entries(entries, now, window)
            ledger["fingerprints"] = entries
            _atomic_write_json(path, ledger)
            return {
                "emit_full": True,
                "occurrences": 1,
                "storm_triggered": False,
                "is_rollup": False,
            }

        count = int(rec.get("count", 0)) + 1
        rec["count"] = count
        rec["last_seen"] = now
        if component is not None:
            rec["component"] = component
        if error_code is not None:
            rec["error_code"] = error_code

        storm_triggered = False
        if count >= threshold and not rec.get("storm_notified"):
            storm_triggered = True
            rec["storm_notified"] = True

        is_rollup = count % threshold == 0
        emit_full = is_rollup or storm_triggered

        entries[fingerprint] = rec
        _prune_error_entries(entries, now, window)
        ledger["fingerprints"] = entries
        _atomic_write_json(path, ledger)
        return {
            "emit_full": emit_full,
            "occurrences": count,
            "storm_triggered": storm_triggered,
            "is_rollup": is_rollup,
        }
    except Exception:
        return dict(fallback)


def active_error_storms(project_root: Path) -> list[dict[str, Any]]:
    """Return fingerprints with an active storm in the current window. Fail-open."""
    try:
        window = _error_window_sec()
        now = time.time()
        ledger = _read_json(error_ledger_path(project_root)) or {}
        entries = ledger.get("fingerprints")
        if not isinstance(entries, dict):
            return []
        out: list[dict[str, Any]] = []
        for fingerprint, rec in entries.items():
            if not isinstance(rec, dict) or not rec.get("storm_notified"):
                continue
            first_seen = rec.get("first_seen")
            if not isinstance(first_seen, (int, float)) or (now - float(first_seen)) > window:
                continue
            out.append(
                {
                    "fingerprint": fingerprint,
                    "count": int(rec.get("count", 0)),
                    "component": rec.get("component"),
                    "error_code": rec.get("error_code"),
                }
            )
        return out
    except Exception:
        return []
