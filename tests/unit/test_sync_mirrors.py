"""Validate sync_command_mirrors.py metadata and drift detection.

Tests the sync script's internal constants match architecture v3
and verifies --check mode reports zero drift against the real repo.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Expected architecture v3 values
_EXPECTED_AGENT_COUNT = 8
_EXPECTED_AGENT_NAMES = frozenset(
    {
        "build",
        "explorer",
        "guard",
        "guide",
        "operate",
        "plan",
        "simplifier",
        "verify",
    }
)
_EXPECTED_ACTIVATION_SKILLS = frozenset(
    {
        "code",
        "explore",
        "guard",
        "guide",
        "ops",
        "plan",
        "simplify",
        "verify",
    }
)
_EXPECTED_AGENT_ONLY = frozenset({"explore", "guide", "verify"})


class TestSyncScriptMetadata:
    """Verify sync script constants match architecture v3."""

    def test_agent_metadata_count(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA

        assert len(AGENT_METADATA) == _EXPECTED_AGENT_COUNT, (
            f"AGENT_METADATA has {len(AGENT_METADATA)} entries, expected {_EXPECTED_AGENT_COUNT}"
        )

    def test_agent_metadata_names(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA

        names = set(AGENT_METADATA.keys())
        assert names == _EXPECTED_AGENT_NAMES, (
            f"Missing: {_EXPECTED_AGENT_NAMES - names}, Extra: {names - _EXPECTED_AGENT_NAMES}"
        )

    def test_agent_activation_skills_count(self) -> None:
        from scripts.sync_command_mirrors import AGENT_ACTIVATION_SKILLS

        assert len(AGENT_ACTIVATION_SKILLS) == len(_EXPECTED_ACTIVATION_SKILLS)

    def test_agent_activation_skills_names(self) -> None:
        from scripts.sync_command_mirrors import AGENT_ACTIVATION_SKILLS

        names = set(AGENT_ACTIVATION_SKILLS.keys())
        assert names == _EXPECTED_ACTIVATION_SKILLS

    def test_agent_only_skills(self) -> None:
        from scripts.sync_command_mirrors import AGENT_ONLY_SKILLS

        assert set(AGENT_ONLY_SKILLS) == _EXPECTED_AGENT_ONLY

    def test_all_agents_have_required_meta_fields(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA

        for name, meta in AGENT_METADATA.items():
            assert meta.display_name, f"{name}: missing display_name"
            assert meta.description, f"{name}: missing description"
            assert meta.model, f"{name}: missing model"
            assert meta.color, f"{name}: missing color"
            assert meta.copilot_tools, f"{name}: empty copilot_tools"
            assert meta.claude_tools, f"{name}: empty claude_tools"
            assert meta.claude_max_turns > 0, f"{name}: invalid max_turns"


class TestSyncDriftDetection:
    """Verify sync --check reports zero drift against real repo."""

    def test_check_mode_returns_zero(self) -> None:
        """sync_command_mirrors.py --check should exit 0 (no drift)."""
        from scripts.sync_command_mirrors import sync_all

        exit_code = sync_all(check_only=True)
        assert exit_code == 0, "Mirror drift detected — run: python scripts/sync_command_mirrors.py"

    def test_discover_skills_matches_filesystem(self) -> None:
        """Discovered skills match actual .ai-engineering/skills/ directories."""
        from scripts.sync_command_mirrors import discover_skills

        skills = discover_skills()
        skills_dir = _PROJECT_ROOT / ".ai-engineering" / "skills"
        expected = {
            d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()
        }
        actual = {name for name, _, _ in skills}
        assert actual == expected, (
            f"Skill discovery mismatch. Missing: {expected - actual}, Extra: {actual - expected}"
        )

    def test_discover_agents_matches_filesystem(self) -> None:
        """Discovered agents match actual .ai-engineering/agents/ files."""
        from scripts.sync_command_mirrors import discover_agents

        agents = discover_agents()
        agents_dir = _PROJECT_ROOT / ".ai-engineering" / "agents"
        expected = {f.stem for f in agents_dir.glob("*.md")}
        actual = {name for name, _ in agents}
        assert actual == expected
