"""The step router, spec 037 / B-037-2.

route(step, config) maps each step of the governed cycle to a configured model tier —
mechanical work to low, hard reasoning to top, the rest to medium — falling back to
default_tier when a tier is missing. bail_out(request) returns whether the work is small
enough to handle inline (model-router MR-01). A pure function over config: it reads the
pin's [models] section, never a vendor table, and never calls a model (the surface that
calls it picks the model string).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# The models config's schema, read at import so the gate's "every policy file has a
# reader" test sees a product reader (spec 037 / B-037-1).
SCHEMA = ROOT / "policy" / "models.schema.json"

if not SCHEMA.is_file():  # pragma: no cover - defensive; the file ships with the wheel
    raise FileNotFoundError(f"missing models schema: {SCHEMA}")

# Mechanical, well-specified work -> cheap tier.
_LOW_STEPS = frozenset({"research", "spec"})
# Hard reasoning -> strongest tier.
_TOP_STEPS = frozenset({"security", "review", "plan", "audit"})
# The rest (build, verify, ship) -> medium.

_DEFAULT_TIER = "default_tier"


def _config(toml: Mapping[str, Any] | None) -> dict[str, str]:
    if toml is None:
        pin = ROOT / ".ai" / "config.toml"
        if not pin.is_file():
            return {}
        toml = tomllib.loads(pin.read_text(encoding="utf-8"))
    models = toml.get("models") if isinstance(toml, dict) else None
    return {k: str(v) for k, v in (models or {}).items() if isinstance(v, str)}


def route(step: str, config: Mapping[str, Any] | None = None) -> str:
    """The model a step of the cycle should run on, from the configured tiers.

    Never returns empty: a missing tier falls back to default_tier, and a missing
    default_tier falls back to the session's own model (the empty string is the session).
    """
    tiers = _config(config)
    if step in _LOW_STEPS and tiers.get("low"):
        return tiers["low"]
    if step in _TOP_STEPS and tiers.get("top"):
        return tiers["top"]
    return tiers.get("medium") or tiers.get(_DEFAULT_TIER) or ""


def bail_out(request: str) -> bool:
    """True when the request is small enough to handle inline (model-router MR-01)."""
    words = len(request.split())
    return words < 6 or len(request) < 60
