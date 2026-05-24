"""Spec-146 changelog coverage."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"


def _changelog_entries() -> str:
    """Return the full changelog body.

    Release promotion moves ``[Unreleased]`` content into a versioned
    ``[X.Y.Z]`` section, so spec-coverage guards must search the whole
    changelog, not only the (post-release empty) ``[Unreleased]`` section.
    """
    return CHANGELOG.read_text(encoding="utf-8")


def test_spec_146_changelog_covers_fixed_changed_and_removed() -> None:
    section = _changelog_entries()

    assert "spec-146" in section
    assert "SQLite ownership" in section
    assert "gate-findings.json" in section
    assert "Runtime Layer Tunables" in section
    assert "Removed" in section


def test_spec_146_changelog_lists_removed_modules_and_artifacts() -> None:
    section = _changelog_entries()
    required = (
        "ai_engineering.state.agentsview",
        "ai_engineering.state.outbox",
        "ai_engineering.cli_ui_skill_ref",
        "ai_engineering.governance.policy_engine",
        ".ai-engineering/references/IOCS_ATTRIBUTION.md",
        ".ai-engineering/team/lessons.md",
        ".ai-engineering/state/strategic-compact.json",
        ".ai-engineering/state/instinct-observations.ndjson",
    )

    for token in required:
        assert token in section


def test_spec_146_changelog_documents_no_shim_import_breakage() -> None:
    section = _changelog_entries()

    assert "No compatibility shim" in section
    assert "OPA-backed governance runner" in section
    assert "state.db/tool_capabilities" in section
