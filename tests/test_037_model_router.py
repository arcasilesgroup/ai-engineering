"""Tests for spec 037 / B-037-2: the step router.

route(step, config) maps each step of the governed cycle to a configured model tier —
mechanical work to low, hard reasoning to top, the rest to medium — falling back to
default_tier when a tier is missing.
enough to handle inline (model-router MR-01). A pure function over config; never calls a
model.
"""

from __future__ import annotations

from ai_engineering import model_router as mr

# The shape the pin's [models] section parses into: a dict under the "models" key.
CONFIG = {"models": {"top": "deepseek-v4-flash", "medium": "deepseek-v4-flash", "low": "qwen3.6"}}
CONFIG_NO_MEDIUM = {"models": {"top": "a", "default_tier": "z"}}


def test_mechanical_steps_route_to_low():
    assert mr.route("research", CONFIG) == "qwen3.6"
    assert mr.route("spec", CONFIG) == "qwen3.6"


def test_hard_reasoning_routes_to_top():
    assert mr.route("security", CONFIG) == "deepseek-v4-flash"
    assert mr.route("review", CONFIG) == "deepseek-v4-flash"

    assert mr.route("build", CONFIG_NO_MEDIUM) == "z"
