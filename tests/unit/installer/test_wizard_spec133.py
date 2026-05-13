"""Tests for collapsed wizard (spec-133 D-133-17).

Golden-snapshot style: assert the single-question flow short-circuits
when ``surfaces`` is pre-resolved via CLI flag.
"""

from __future__ import annotations

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


def test_wizard_vcs_defaults_to_github_when_not_detected() -> None:
    result = run_wizard(
        DetectionResult(stacks=[], surfaces=[], vcs=None),
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
