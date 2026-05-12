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
        providers=[],
        ides=[],
        vcs=vcs or "github",
    )


def test_wizard_skips_when_surfaces_resolved() -> None:
    result = run_wizard(_detected(), resolved={"surfaces": ["claude-code", "cursor"]})
    assert result.surfaces == ["claude-code", "cursor"]
    assert result.providers == ["claude-code", "cursor"]
    assert result.ides == ["claude-code", "cursor"]


def test_wizard_greenfield_preserves_empty_stacks() -> None:
    """spec-133 D-133-25: greenfield does NOT coerce to ['python']."""
    result = run_wizard(
        DetectionResult(stacks=[], providers=[], ides=[], vcs="github"),
        resolved={"surfaces": ["claude-code"]},
    )
    assert result.stacks == []


def test_wizard_auto_detects_stacks_silently() -> None:
    result = run_wizard(_detected(stacks=["typescript", "rust"]), resolved={"surfaces": ["codex"]})
    assert set(result.stacks) == {"typescript", "rust"}


def test_wizard_vcs_defaults_to_github_when_not_detected() -> None:
    result = run_wizard(
        DetectionResult(stacks=[], providers=[], ides=[], vcs=None),
        resolved={"surfaces": ["claude-code"]},
    )
    assert result.vcs == "github"


def test_wizard_legacy_provider_flag_derives_surfaces() -> None:
    result = run_wizard(_detected(), resolved={"providers": ["codex"], "ides": []})
    assert "codex" in result.surfaces


def test_wizard_filters_unknown_surfaces() -> None:
    """Legacy --provider with unknown ID falls back to default."""
    result = run_wizard(_detected(), resolved={"providers": ["unknown-bot"], "ides": []})
    assert result.surfaces == ["claude-code"]
