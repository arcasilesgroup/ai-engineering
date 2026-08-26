"""Tests for spec 038 / B-038-1: the accessibility honesty floor.

A designed surface either names the a11y basics — contrast >= WCAG AA, keyboard
reachability, visible focus, reduced-motion — confirmed by the existing verify steps, or
exits `INCOMPLETE: a11y not-covered <reason>` when it deliberately cannot. A surface that
says neither is refused: a silent pass is never the answer.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering import contract

FLOOR = (
    "verify: contrast >= WCAG 2.2 AA measured over the real background; keyboard "
    "reachability checked; visible focus present; reduced-motion respected."
)
NOT_COVERED = (
    "verify: this surface cannot meet contrast AA; not-covered: editorial low-contrast "
    "intent, logged."
)
SILENT = "verify: the surface looks fine."


def test_floor_holds_clean():
    problems = contract._accessibility_problems(FLOOR)
    assert problems == []


def test_silent_pass_refused():
    problems = contract._accessibility_problems(SILENT)
    assert any("not-covered" in p for p in problems)


def test_honest_exit_accepted():
    problems = contract._accessibility_problems(NOT_COVERED)
    assert problems == []


def test_reference_names_the_rule():
    ref = (
        Path(__file__).parents[1]
        / ".agents"
        / "skills"
        / "ai-design"
        / "references"
        / "accessibility.md"
    )
    text = ref.read_text()
    assert "contrast" in text and "keyboard" in text and "not-covered" in text