"""spec-185 D-185-02/03: vendor-agnostic driver-capability tier resolution.

Resolves the ACTIVE driving model's capability tier from its model id, across
Anthropic, OpenAI, and open-weight families. This is the *driver-capability*
axis (how capable is the model currently driving the framework), distinct from
the *dispatch-effort* axis (which model to dispatch a sub-task TO — the
``effort``/``model_tier`` pair documented in
``.ai-engineering/reference/model-dispatch-policy.md``). The two axes must not
be conflated: this module answers the former.

Detection keys on model-id family + active-parameter band, NOT headline
benchmark, because reasoning capability tracks active FLOPs (spec-185 brief
[14][15][S19]). Auto-detection is the default; ``AIENG_DRIVER_TIER`` is an
escape-hatch override (unset = auto-detect), mirroring the ``AIENG_HOOK_ENGINE``
convention. An unknown model resolves to the most conservative tier so the
framework never *over*-trusts an unrecognised driver.

Stdlib-only so a hook ``_lib`` mirror can import the same logic.
"""

from __future__ import annotations

import os

# Ordered most-capable -> least. Index doubles as capability rank.
DRIVER_TIERS: tuple[str, ...] = ("frontier", "standard-floor", "stretch-floor")

STANDARD_FLOOR = "standard-floor"
_DEFAULT_TIER = "stretch-floor"  # fail-safe: unknown driver -> weakest tier
_OVERRIDE_ENV = "AIENG_DRIVER_TIER"

# (model-id substring, tier). Checked in order — most-specific FIRST so a
# narrower variant (e.g. ``gpt-4o-mini``) wins over its base (``gpt``).
_FAMILY_TIERS: tuple[tuple[str, str], ...] = (
    # Anthropic (dispatch reference names are also the driver names here)
    ("fable", "frontier"),  # Claude 5 Mythos-class (claude-fable-5)
    ("mythos", "frontier"),  # Claude 5 Mythos-class (claude-mythos-5)
    ("opus", "frontier"),
    ("sonnet", "standard-floor"),
    ("haiku", "stretch-floor"),
    # OpenAI — specific weak variants before the capable base
    ("gpt-4o-mini", "stretch-floor"),
    ("gpt-5-nano", "stretch-floor"),
    ("gpt-5-mini", "stretch-floor"),
    ("gpt-4.1-nano", "stretch-floor"),
    ("gpt-4.1-mini", "stretch-floor"),
    ("gpt-5", "frontier"),
    ("gpt-4.1", "frontier"),
    ("gpt-4o", "frontier"),
    # Open-weight (active-param band drives the tier, not total params);
    # weak GLM variants before the flagship base needle
    ("glm-4-flash", "stretch-floor"),
    ("glm-4-air", "standard-floor"),
    ("glm", "frontier"),  # glm5.2 ~753B MoE "coding agentico" — local ceiling
    ("deepseek", "standard-floor"),  # deepseek-v4-flash ~21B active
    ("mimo", "stretch-floor"),  # mimo-v2.5 ~15B active — unproven, conservative
    ("qwen", "stretch-floor"),  # qwen3.x A3B ~3B active
    ("gemma", "stretch-floor"),  # gemma A4B ~4B, no native tool schema
)

_TIER_RANK: dict[str, int] = {tier: i for i, tier in enumerate(DRIVER_TIERS)}


def tier_rank(tier: str) -> int:
    """Capability rank (0 = most capable). Unknown tiers rank as weakest."""
    return _TIER_RANK.get(tier, len(DRIVER_TIERS))


def resolve_driver_tier(model_id: str | None, *, env: dict | None = None) -> str:
    """Resolve the driver-capability tier for the active model.

    Precedence: ``AIENG_DRIVER_TIER`` override (when it names a valid tier) >
    model-id family match > conservative default (``stretch-floor``).
    """
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
    """True when ``tier`` is weaker than the standard-floor (D-185-04).

    Below-floor drivers hard-block multi-concern flows (``/ai-autopilot``) and
    flip advisory governance to deterministic enforcement.
    """
    return tier_rank(tier) > tier_rank(STANDARD_FLOOR)
