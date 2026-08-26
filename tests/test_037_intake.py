"""Tests for spec 037 / B-037-3: the intake validator.

validate_intake(text) returns PASS when the opening request names the goal, the
constraints and an acceptance signal, and INCOMPLETE with the missing fields when it does
not. The template is a fallback for malformed requests; a well-formed free request passes
without it.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering import intake

GOOD = (
    "Goal: add rate limiting to the public API. Constraints: must not break existing "
    "clients, no new dependency. Acceptance: tests pass and the quota header is set."
)


def test_template_example_passes():


def test_template_example_passes():
    # The template's own example is the contract, end to end.
    template = Path("specs/new-goal-template.md").read_text()
    assert intake.validate_intake(template) == "PASS"


def test_well_formed_free_request_passes():
    assert intake.validate_intake(GOOD) == "PASS"


def test_missing_acceptance_is_incomplete():
    bad = "Goal: add rate limiting. Constraints: none."
    result = intake.validate_intake(bad)
    assert result.startswith("INCOMPLETE")
    assert "acceptance" in result


def test_empty_request_is_incomplete():
    assert intake.validate_intake("").startswith("INCOMPLETE")
