"""Tests for cli_ui.skill_ref helper (spec-133 D-133-22).

Skill-reference rendering must be consistent everywhere we print
``/ai-<name>`` to a shell user: that string is NOT a shell command,
it is a slash command for the AI surface chat. The helper unambiguously
labels it.
"""

from __future__ import annotations

import pytest

from ai_engineering.cli_ui_skill_ref import skill_ref, skill_ref_tight


def test_skill_ref_returns_canonical_long_form() -> None:
    assert skill_ref("start") == "the /ai-start skill (run in your AI surface chat, not shell)"


def test_skill_ref_strips_leading_slash_if_present() -> None:
    assert skill_ref("/ai-start") == "the /ai-start skill (run in your AI surface chat, not shell)"


def test_skill_ref_strips_ai_prefix_if_present() -> None:
    assert skill_ref("ai-start") == "the /ai-start skill (run in your AI surface chat, not shell)"


def test_skill_ref_tight_form() -> None:
    assert skill_ref_tight("commit") == "/ai-commit (in your AI surface)"


def test_skill_ref_tight_strips_leading_slash() -> None:
    assert skill_ref_tight("/ai-commit") == "/ai-commit (in your AI surface)"


def test_skill_ref_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        skill_ref("")


def test_skill_ref_rejects_only_prefix() -> None:
    with pytest.raises(ValueError):
        skill_ref("/ai-")


def test_skill_ref_rejects_whitespace_only() -> None:
    with pytest.raises(ValueError):
        skill_ref("   ")
