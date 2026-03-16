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


class TestSyncDriftDetection:
    """Verify sync --check reports zero drift against real repo."""

    def test_check_mode_returns_zero(self) -> None:
        """sync_command_mirrors.py --check should exit 0 (no drift)."""
        from scripts.sync_command_mirrors import sync_all

        exit_code = sync_all(check_only=True)
        assert exit_code == 0, "Mirror drift detected — run: python scripts/sync_command_mirrors.py"

    def test_discover_skills_matches_filesystem(self) -> None:
        """Discovered skills match canonical template skills/ directories."""
        from scripts.sync_command_mirrors import discover_skills

        skills = discover_skills()
        skills_dir = (
            _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "skills"
        )
        expected = {
            d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()
        }
        actual = {name for name, _, _ in skills}
        assert actual == expected, (
            f"Skill discovery mismatch. Missing: {expected - actual}, Extra: {actual - expected}"
        )

    def test_discover_agents_matches_filesystem(self) -> None:
        """Discovered agents match canonical template agents/ files."""
        from scripts.sync_command_mirrors import discover_agents

        agents = discover_agents()
        agents_dir = (
            _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "agents"
        )
        expected = {f.stem for f in agents_dir.glob("*.md")}
        actual = {name for name, _ in agents}
        assert actual == expected


# ── Generation functions (pure — input/output, no I/O) ────────────────────


class TestGenerationFunctions:
    """Test content generation — pure functions, no filesystem access."""

    def test_generate_claude_skill_includes_frontmatter(self) -> None:
        from scripts.sync_command_mirrors import SKILLS_ROOT, generate_claude_skill

        # Arrange
        fm = {"description": "Test skill for testing", "argument-hint": "arg1|arg2"}
        # Use a real skill path so read_canonical_body works
        skill_path = SKILLS_ROOT / "commit" / "SKILL.md"

        # Act
        content = generate_claude_skill("test-skill", fm, skill_path)

        # Assert
        assert "---" in content
        assert "name: ai-test-skill" in content
        assert 'description: "Test skill for testing"' in content
        assert 'argument-hint: "arg1|arg2"' in content
        assert "$ARGUMENTS" in content

    def test_generate_claude_skill_includes_extras_when_present(self) -> None:
        from scripts.sync_command_mirrors import SKILLS_ROOT, generate_claude_skill

        # Arrange — accessibility has context:fork extra
        fm = {"description": "Accessibility audit"}
        skill_path = SKILLS_ROOT / "accessibility" / "SKILL.md"

        # Act
        content = generate_claude_skill("accessibility", fm, skill_path)

        # Assert
        assert "context:fork" in content

    def test_generate_claude_skill_no_extras_for_unknown_skill(self) -> None:
        from scripts.sync_command_mirrors import SKILLS_ROOT, generate_claude_skill

        # Arrange
        fm = {"description": "Unknown skill"}
        # Use a real skill path to avoid file errors
        skill_path = SKILLS_ROOT / "commit" / "SKILL.md"

        # Act
        content = generate_claude_skill("unknown-skill", fm, skill_path)

        # Assert
        assert "context:fork" not in content

    def test_generate_claude_agent_activation_format(self) -> None:
        from scripts.sync_command_mirrors import AgentActivation, generate_claude_agent_activation

        # Arrange
        activation = AgentActivation(
            agent_name="build",
            description="Activate build agent",
            argument_hint="impl|test",
        )

        # Act
        content = generate_claude_agent_activation("code", activation)

        # Assert
        assert "name: ai-code" in content
        assert 'argument-hint: "impl|test"' in content
        # Content is now fully embedded, not a thin wrapper
        assert len(content) > 100

    def test_generate_agents_agent_wrapper_format(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA, generate_agents_agent

        # Arrange
        meta = AGENT_METADATA["build"]

        # Act
        content = generate_agents_agent("build", meta)

        # Assert
        assert "name: build" in content
        # Content is now fully embedded from canonical source
        assert len(content) > 100

    def test_generate_copilot_agent_includes_per_agent_metadata(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA, generate_copilot_agent

        # Arrange
        meta = AGENT_METADATA["explorer"]

        # Act
        content = generate_copilot_agent("explorer", meta)

        # Assert
        assert 'name: "Explorer"' in content
        assert "model: opus" in content
        assert "color: teal" in content
        assert "readFile" in content  # explorer has limited tools
        assert "editFiles" not in content  # explorer is read-only

    def test_generate_skill_copilot_prompt_format(self) -> None:
        from scripts.sync_command_mirrors import SKILLS_ROOT, generate_skill_copilot_prompt

        # Arrange
        skill_path = SKILLS_ROOT / "commit" / "SKILL.md"

        # Act
        content = generate_skill_copilot_prompt("commit", "Execute commit workflow", skill_path)

        # Assert
        assert 'description: "Execute commit workflow"' in content
        assert 'mode: "agent"' in content
        # Content is now fully embedded, not a thin wrapper
        assert len(content) > 100


# ── Validation functions ──────────────────────────────────────────────────


class TestValidationFunctions:
    """Test validation logic — uses tmp_path for filesystem state."""

    def test_validate_runbooks_warns_when_empty(self, tmp_path: Path) -> None:
        # Arrange — empty runbooks dir (monkeypatch RUNBOOKS_ROOT)
        import scripts.sync_command_mirrors as mod
        from scripts.sync_command_mirrors import validate_runbooks

        original = mod.RUNBOOKS_ROOT
        mod.RUNBOOKS_ROOT = tmp_path / "nonexistent"

        # Act
        warnings = validate_runbooks()

        # Assert
        assert any("not found" in w for w in warnings)

        # Cleanup
        mod.RUNBOOKS_ROOT = original

    def test_check_or_write_unchanged_returns_none(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write

        # Arrange — file exists with same content
        test_file = tmp_path / "test.md"
        test_file.write_text("hello", encoding="utf-8")

        import scripts.sync_command_mirrors as mod

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        # Act
        result = _check_or_write(test_file, "hello", check_only=False)

        # Assert
        assert result is None  # unchanged

        mod.ROOT = original_root

    def test_check_or_write_drift_updates_file(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write

        # Arrange — file exists with different content
        test_file = tmp_path / "test.md"
        test_file.write_text("old content", encoding="utf-8")

        import scripts.sync_command_mirrors as mod

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        # Act
        result = _check_or_write(test_file, "new content", check_only=False)

        # Assert
        assert result is not None
        assert "UPDATED" in result
        assert test_file.read_text() == "new content"

        mod.ROOT = original_root

    def test_check_or_write_missing_creates_file(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write

        # Arrange — file doesn't exist
        test_file = tmp_path / "subdir" / "new.md"

        import scripts.sync_command_mirrors as mod

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        # Act
        result = _check_or_write(test_file, "created", check_only=False)

        # Assert
        assert result is not None
        assert "CREATED" in result
        assert test_file.read_text() == "created"

        mod.ROOT = original_root

    def test_check_or_write_check_only_does_not_write(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write

        # Arrange — file exists with different content
        test_file = tmp_path / "test.md"
        test_file.write_text("old", encoding="utf-8")

        import scripts.sync_command_mirrors as mod

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        # Act
        result = _check_or_write(test_file, "new", check_only=True)

        # Assert
        assert "DRIFT" in result
        assert test_file.read_text() == "old"  # NOT modified

        mod.ROOT = original_root
