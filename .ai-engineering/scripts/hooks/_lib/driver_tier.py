"""Stdlib-only driver-capability tier resolution + sidecar (spec-185 T-0.4).

Hook-side mirror of ``ai_engineering.state.driver_tier``. Imports nothing from
``ai_engineering.*`` — only Python stdlib — so it runs before ``pip install``
lands the package. The family map and precedence MUST stay behaviourally
identical to the package copy; ``tests/unit/hooks/test_driver_tier_parity.py``
is the guard (there is no other CI parity check for this dual tree).

Resolves the ACTIVE driving model's capability tier from its model id
(D-185-02/03), keyed on model-id family + active-parameter band rather than
headline benchmark. Auto-detection is the default; ``AIENG_DRIVER_TIER`` is the
escape-hatch override (unset = auto-detect), mirroring ``AIENG_HOOK_ENGINE``.
An unknown model resolves to the most conservative tier.

Detection sources (best-first): the Claude Code ``SessionStart`` hook payload
``model`` field (optional — absent after /clear or resume), else ``None`` ->
conservative default. A transcript-derived fallback for the absent case is
deferred to the Stop-hook self-heal follow-up and is NOT implemented here.
The resolved tier is published to a disk sidecar so every later phase/hook
re-reads it instead of re-detecting, consistent with the framework's
disk-handoff doctrine.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

DRIVER_TIERS: tuple[str, ...] = ("frontier", "standard-floor", "stretch-floor")
STANDARD_FLOOR = "standard-floor"
_DEFAULT_TIER = "stretch-floor"
_OVERRIDE_ENV = "AIENG_DRIVER_TIER"

DRIVER_TIER_REL = Path(".ai-engineering") / "runtime" / "driver-tier.json"
SCHEMA_VERSION = "1.0"

# (model-id substring, tier). Most-specific FIRST. Keep behaviourally identical
# to ai_engineering.state.driver_tier._FAMILY_TIERS.
_FAMILY_TIERS: tuple[tuple[str, str], ...] = (
    ("fable", "frontier"),
    ("mythos", "frontier"),
    ("opus", "frontier"),
    ("sonnet", "standard-floor"),
    ("haiku", "stretch-floor"),
    ("gpt-4o-mini", "stretch-floor"),
    ("gpt-5-nano", "stretch-floor"),
    ("gpt-5-mini", "stretch-floor"),
    ("gpt-4.1-nano", "stretch-floor"),
    ("gpt-4.1-mini", "stretch-floor"),
    ("gpt-5", "frontier"),
    ("gpt-4.1", "frontier"),
    ("gpt-4o", "frontier"),
    ("glm-4-flash", "stretch-floor"),
    ("glm-4-air", "standard-floor"),
    ("glm", "frontier"),
    ("deepseek", "standard-floor"),
    ("mimo", "stretch-floor"),
    ("qwen", "stretch-floor"),
    ("gemma", "stretch-floor"),
)

_TIER_RANK: dict[str, int] = {tier: i for i, tier in enumerate(DRIVER_TIERS)}


def tier_rank(tier: str) -> int:
    return _TIER_RANK.get(tier, len(DRIVER_TIERS))


def resolve_driver_tier(model_id: str | None, *, env: dict | None = None) -> str:
    """Override (valid tier) > model-id family match > conservative default."""
    environ = os.environ if env is None else env
    override = (environ.get(_OVERRIDE_ENV) or "").strip().lower()
    if override in _TIER_RANK:
        return override
    mid = (model_id or "").strip().lower()
    if mid:
        for needle, tier in _FAMILY_TIERS:
            if needle in mid:
                return tier
    return _DEFAULT_TIER


def is_below_standard_floor(tier: str) -> bool:
    return tier_rank(tier) > tier_rank(STANDARD_FLOOR)


def driver_tier_path(project_root: Path) -> Path:
    return project_root / DRIVER_TIER_REL


def write_driver_tier(project_root: Path, model_id: str | None) -> str:
    """Resolve + atomically publish the driver tier sidecar. Returns the tier."""
    tier = resolve_driver_tier(model_id)
    path = driver_tier_path(project_root)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "model_id": (model_id or "").strip() or None,
        "tier": tier,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
    return tier


def _emit_corruption_event(project_root: Path, summary: str) -> None:
    """Best-effort ``framework_error`` NDJSON line for a corrupt sidecar.

    Mirrors ``trace_context._emit_corruption_event`` (gate-policy: plumbing
    fails open and MUST log). Imports stay lazy so this module remains
    stdlib-only at import time; any failure in the logger itself is silent.
    """
    try:
        from datetime import UTC, datetime
        from uuid import uuid4

        from _lib.locked_append import with_lock_retry
        from _lib.trace_context import FRAMEWORK_EVENTS_REL, _compute_prev_event_hash

        events_path = project_root / FRAMEWORK_EVENTS_REL
        events_path.parent.mkdir(parents=True, exist_ok=True)
        entry: dict[str, object] = {
            "schemaVersion": SCHEMA_VERSION,
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": project_root.name,
            "engine": "ai_engineering",
            "kind": "framework_error",
            "outcome": "failure",
            "component": "state.driver_tier",
            "correlationId": uuid4().hex,
            "detail": {
                "error_code": "driver_tier_corrupted",
                "summary": summary[:200],
            },
        }
        with with_lock_retry(project_root, "framework-events") as _locked:
            entry["prev_event_hash"] = _compute_prev_event_hash(events_path)
            line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
            with events_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception:
        return


def read_driver_tier(project_root: Path) -> str:
    """Re-read the persisted tier; conservative default if absent/corrupt.

    A missing or empty sidecar is the benign pre-publish state and stays
    silent. Genuine corruption (unreadable file, bad JSON, non-object
    payload) emits a ``framework_error`` before returning the conservative
    default, mirroring ``trace_context.read_trace_context``.
    """
    path = driver_tier_path(project_root)
    if not path.exists():
        return _DEFAULT_TIER
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        _emit_corruption_event(project_root, f"read failed: {exc!s}")
        return _DEFAULT_TIER
    if not raw.strip():
        return _DEFAULT_TIER
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        _emit_corruption_event(project_root, f"json parse failed: {exc!s}")
        return _DEFAULT_TIER
    if not isinstance(payload, dict):
        _emit_corruption_event(project_root, "payload is not a JSON object")
        return _DEFAULT_TIER
    tier = payload.get("tier")
    return tier if isinstance(tier, str) and tier in _TIER_RANK else _DEFAULT_TIER
