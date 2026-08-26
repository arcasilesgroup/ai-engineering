"""Tests for spec 037 / B-037-2: the step router.

route(step, config) maps each step of the governed cycle to a configured model tier —
mechanical work to low, hard reasoning to top, the rest to medium — falling back to
default_tier when a tier is missing. bail_out(request) returns whether the work is small
enough to handle inline (model-router MR-01). A pure function over config; never calls a
model.
"""

from __future__ import annotations

from ai_engineering import model_router as mr

CONFIG = {"top": "deepseek-v4-flash", "medium": "deepseek-v4-flash", "low": "qwen3.6"}


def test_mechanical_steps_route_to_low():
    assert mr.route("research", CONFIG) == "qwen3.6"
    assert mr.route("spec", CONFIG) == "qwen3.6"


def test_hard_reasoning_routes_to_top():
    assert mr.route("security", CONFIG) == "deepseek-v4-flash"
    assert mr.route("review", CONFIG) == "deepseek-v4-flash"


def test_default_tier_when_tier_missing():
    assert mr.route("build", {"top": "a", "low": "b"}) == "a"


def test_bail_out_on_small_request():
    assert mr.bail_out("fix the typo in README") is True
    assert mr.bail_out("redesign the auth flow across four services") is False