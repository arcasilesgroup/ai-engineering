"""Tests for collapsed wizard (spec-133 D-133-17).

Golden-snapshot style: assert the single-question flow short-circuits
when ``surfaces`` is pre-resolved via CLI flag.
"""

from __future__ import annotations

from unittest.mock import patch

from ai_engineering.installer.autodetect import DetectionResult
from ai_engineering.installer.wizard import run_wizard


def _detected(stacks: list[str] | None = None, vcs: str | None = None) -> DetectionResult:
    return DetectionResult(
        stacks=stacks or ["python"],
        surfaces=[],
        vcs=vcs or "github",
    )


def test_wizard_skips_when_surfaces_resolved() -> None:
    result = run_wizard(_detected(), resolved={"surfaces": ["claude-code", "cursor"]})
    assert result.surfaces == ["claude-code", "cursor"]


def test_wizard_greenfield_preserves_empty_stacks() -> None:
    """spec-133 D-133-25: greenfield does NOT coerce to ['python']."""
    result = run_wizard(
        DetectionResult(stacks=[], surfaces=[], vcs="github"),
        resolved={"surfaces": ["claude-code"]},
    )
    assert result.stacks == []


def test_wizard_auto_detects_stacks_silently() -> None:
    result = run_wizard(_detected(stacks=["typescript", "rust"]), resolved={"surfaces": ["codex"]})
    assert set(result.stacks) == {"typescript", "rust"}


def test_wizard_vcs_defaults_to_github_when_prompt_aborted() -> None:
    """D-133-17 amendment: empty ``detected.vcs`` triggers prompt;
    aborting (Ctrl+C → ``_ask_vcs`` returns "github") preserves the safe default.
    """
    with patch("ai_engineering.installer.wizard._ask_vcs", return_value="github"):
        result = run_wizard(
            DetectionResult(stacks=[], surfaces=[], vcs=""),
            resolved={"surfaces": ["claude-code"]},
        )
    assert result.vcs == "github"


def test_surface_choices_no_preselect_when_greenfield() -> None:
    """Greenfield install (no autodetect markers) preselects NOTHING."""
    from ai_engineering.installer.wizard import _build_surface_choices

    choices = _build_surface_choices(detected_surfaces=[])
    assert all(not c.checked for c in choices), "Greenfield wizard must not preselect any Surface"


def test_surface_choices_preselect_only_detected() -> None:
    """Only Surfaces with autodetect-marker matches are preselected."""
    from ai_engineering.installer.wizard import _build_surface_choices

    choices = _build_surface_choices(detected_surfaces=["cursor", "opencode"])
    checked_ids = {c.value for c in choices if c.checked}
    assert checked_ids == {"cursor", "opencode"}


# ---------------------------------------------------------------------------
# Conditional VCS prompt (D-133-17 amendment — option 3)
# Wizard remains 1-question for the common case; falls back to a secondary
# VCS prompt only when autodetect is ambiguous (no git remote configured).
# ---------------------------------------------------------------------------


def test_wizard_prompts_vcs_when_autodetect_ambiguous() -> None:
    """When ``detected.vcs == ""`` (no remote), wizard MUST ask interactively."""
    detected = DetectionResult(stacks=[], surfaces=[], vcs="")
    with patch("ai_engineering.installer.wizard._ask_vcs", return_value="azure_devops") as mock_ask:
        result = run_wizard(detected, resolved={"surfaces": ["claude-code"]})
    mock_ask.assert_called_once()
    assert result.vcs == "azure_devops"


def test_wizard_skips_vcs_prompt_when_autodetect_succeeded() -> None:
    """When ``detected.vcs`` is non-empty, wizard MUST NOT prompt."""
    detected = DetectionResult(stacks=[], surfaces=[], vcs="github")
    with patch("ai_engineering.installer.wizard._ask_vcs") as mock_ask:
        result = run_wizard(detected, resolved={"surfaces": ["claude-code"]})
    mock_ask.assert_not_called()
    assert result.vcs == "github"


def test_wizard_skips_vcs_prompt_when_flag_provided() -> None:
    """``--vcs`` flag in resolved overrides any prompt logic."""
    detected = DetectionResult(stacks=[], surfaces=[], vcs="")
    with patch("ai_engineering.installer.wizard._ask_vcs") as mock_ask:
        result = run_wizard(
            detected,
            resolved={"surfaces": ["claude-code"], "vcs": "azure_devops"},
        )
    mock_ask.assert_not_called()
    assert result.vcs == "azure_devops"


def test_wizard_vcs_prompt_ctrl_c_falls_back_to_github() -> None:
    """Aborting the VCS prompt (Ctrl+C) defaults to ``github`` — safe choice."""
    detected = DetectionResult(stacks=[], surfaces=[], vcs="")
    with patch("ai_engineering.installer.wizard._ask_vcs", return_value="github") as mock_ask:
        result = run_wizard(detected, resolved={"surfaces": ["claude-code"]})
    mock_ask.assert_called_once()
    assert result.vcs == "github"


def test_detect_vcs_returns_empty_when_no_remote(tmp_path) -> None:
    """``detect_vcs`` returns ``""`` for repos with no ``origin`` remote.

    The empty value is the explicit signal for the wizard to prompt.
    """
    from ai_engineering.installer.autodetect import detect_vcs

    # tmp_path has no .git/, so origin lookup must fail gracefully
    assert detect_vcs(tmp_path) == ""
