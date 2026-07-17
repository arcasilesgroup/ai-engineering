"""spec-185 D-185-02/03: driver-capability tier resolver contract."""

from __future__ import annotations

import pytest

from ai_engineering.state.driver_tier import (
    DRIVER_TIERS,
    is_below_standard_floor,
    resolve_driver_tier,
    tier_rank,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model_id", "expected"),
    [
        # Anthropic
        ("claude-fable-5", "frontier"),
        ("claude-mythos-5", "frontier"),
        ("claude-opus-4-8", "frontier"),
        ("claude-sonnet-5", "standard-floor"),
        ("claude-haiku-4-5-20251001", "stretch-floor"),
        # OpenAI — specific weak variant beats its capable base
        ("gpt-5", "frontier"),
        ("gpt-5-mini", "stretch-floor"),
        ("gpt-4.1-2025", "frontier"),
        ("gpt-4.1-nano", "stretch-floor"),
        ("gpt-4o", "frontier"),
        ("gpt-4o-mini", "stretch-floor"),
        # Open-weight — active-param band, not total params
        ("glm5.2", "frontier"),
        ("glm-4-flash", "stretch-floor"),
        ("glm-4-air", "standard-floor"),
        ("deepseek-v4-flash", "standard-floor"),
        ("mimo-v2.5", "stretch-floor"),
        ("qwen3.6", "stretch-floor"),
        ("gemma4", "stretch-floor"),
    ],
)
def test_resolves_family_to_tier(model_id: str, expected: str) -> None:
    assert resolve_driver_tier(model_id, env={}) == expected


@pytest.mark.unit
def test_unknown_and_empty_default_to_weakest() -> None:
    # Conservative: never over-trust an unrecognised driver.
    assert resolve_driver_tier("some-unheard-of-model", env={}) == "stretch-floor"
    assert resolve_driver_tier(None, env={}) == "stretch-floor"
    assert resolve_driver_tier("", env={}) == "stretch-floor"


@pytest.mark.unit
def test_env_override_wins_over_model_id() -> None:
    # AIENG_DRIVER_TIER is the escape-hatch override (D-185-02).
    assert (
        resolve_driver_tier("claude-opus-4-8", env={"AIENG_DRIVER_TIER": "stretch-floor"})
        == "stretch-floor"
    )


@pytest.mark.unit
def test_invalid_override_falls_back_to_detection() -> None:
    assert resolve_driver_tier("claude-opus-4-8", env={"AIENG_DRIVER_TIER": "bogus"}) == "frontier"


@pytest.mark.unit
def test_below_standard_floor_gate() -> None:
    assert is_below_standard_floor("stretch-floor") is True
    assert is_below_standard_floor("standard-floor") is False
    assert is_below_standard_floor("frontier") is False


@pytest.mark.unit
def test_tier_rank_is_ordered_most_capable_first() -> None:
    assert tier_rank("frontier") < tier_rank("standard-floor") < tier_rank("stretch-floor")
    assert DRIVER_TIERS == ("frontier", "standard-floor", "stretch-floor")
