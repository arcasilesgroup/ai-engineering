"""Validate sync_command_mirrors.py metadata and drift detection.

Tests the sync script's internal constants match the current architecture
and verifies --check mode reports zero drift against the real repo.
"""

from __future__ import annotations

import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Expected architecture values (post spec-091 ai-run orchestration)
_EXPECTED_AGENT_COUNT = 10
_EXPECTED_AGENT_NAMES = frozenset(
    {
        "autopilot",
        "build",
        "explore",
        "guard",
        "guide",
        "plan",
        "review",
        "run-orchestrator",
        "simplify",
        "verify",
    }
)


class TestSyncScriptMetadata:
    """Verify sync script constants match current architecture."""

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
        assert exit_code == 0, (
            "Mirror drift detected -- run: python scripts/sync_command_mirrors.py"
        )

    def test_discover_skills_matches_filesystem(self) -> None:
        """Discovered skills match canonical .claude/skills/ai-* directories."""
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, discover_skills

        skills = discover_skills()
        expected = {
            d.name.removeprefix("ai-")
            for d in CLAUDE_SKILLS.iterdir()
            if d.is_dir() and d.name.startswith("ai-") and (d / "SKILL.md").is_file()
        }
        actual = {name for name, _, _ in skills}
        assert actual == expected, (
            f"Skill discovery mismatch. Missing: {expected - actual}, Extra: {actual - expected}"
        )

    def test_discover_agents_matches_filesystem(self) -> None:
        """Discovered agents match canonical .claude/agents/ai-*.md files."""
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, discover_agents

        agents = discover_agents()
        expected = {f.stem.removeprefix("ai-") for f in CLAUDE_AGENTS.glob("ai-*.md")}
        actual = {name for name, _, _ in agents}
        assert actual == expected


# -- Generation functions (pure -- input/output, no I/O) ----


class TestGenerationFunctions:
    """Test content generation -- pure functions, no filesystem access."""

    def test_generate_codex_skill_includes_frontmatter(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, generate_codex_skill

        # Arrange -- use real canonical skill
        skill_path = CLAUDE_SKILLS / "ai-commit" / "SKILL.md"

        # Act
        content = generate_codex_skill("commit", skill_path)

        # Assert -- frontmatter comes from canonical
        assert "---" in content
        assert "name: ai-commit" in content
        assert "tags:" in content
        assert len(content) > 100

    def test_generate_copilot_skill_includes_frontmatter(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, generate_copilot_skill

        # Arrange
        skill_path = CLAUDE_SKILLS / "ai-commit" / "SKILL.md"

        # Act
        content = generate_copilot_skill("commit", skill_path)

        # Assert -- standalone SKILL.md with adapted frontmatter
        assert "name: ai-commit" in content
        assert "mode: agent" in content
        assert "tags:" in content
        assert len(content) > 100

    def test_generate_copilot_instructions_preserves_slash_command_boundary(self) -> None:
        from scripts.sync_command_mirrors import (
            discover_agents,
            discover_skills,
            generate_copilot_instructions,
        )

        content = generate_copilot_instructions(discover_skills(), discover_agents())

        assert "`/ai-start` and other `/ai-*` entries are IDE slash commands" in content
        assert "Never translate `/ai-<name>` into `ai-eng <name>`" in content

    def test_generate_codex_agent_wrapper_format(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, generate_codex_agent

        # Arrange
        agent_path = CLAUDE_AGENTS / "ai-build.md"

        # Act
        content = generate_codex_agent("build", agent_path)

        # Assert -- content is fully embedded from canonical source
        assert len(content) > 100

    def test_generate_copilot_agent_includes_per_agent_metadata(self) -> None:
        from scripts.sync_command_mirrors import (
            AGENT_METADATA,
            CLAUDE_AGENTS,
            generate_copilot_agent,
        )

        # Arrange
        meta = AGENT_METADATA["explore"]
        agent_path = CLAUDE_AGENTS / "ai-explore.md"

        # Act
        content = generate_copilot_agent("explore", meta, agent_path)

        # Assert
        assert 'name: "Explorer"' in content
        assert "model: opus" in content
        assert "color: cyan" in content
        assert "readFile" in content  # explore has limited tools
        assert "editFiles" not in content  # explore is read-only

    def test_generate_install_claude_skill_copies_content(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, generate_install_claude_skill

        skill_path = CLAUDE_SKILLS / "ai-commit" / "SKILL.md"
        content = generate_install_claude_skill(skill_path)
        # Should be an exact copy
        assert content == skill_path.read_text(encoding="utf-8")

    def test_generate_install_codex_surface_copies_content(self) -> None:
        from scripts.sync_command_mirrors import ROOT, generate_install_codex_surface

        surface_path = ROOT / ".codex" / "hooks.json"
        content = generate_install_codex_surface(surface_path)
        assert content == surface_path.read_text(encoding="utf-8")

    def test_generate_agents_md_preserves_provider_rows_and_counts(self) -> None:
        from scripts.sync_command_mirrors import (
            discover_agents,
            discover_skills,
            generate_agents_md,
        )

        skills = discover_skills()
        agents = discover_agents()

        content = generate_agents_md(skill_count=len(skills), agent_count=len(agents))

        # Platform Mirrors table removed (spec-087) -- only check Skills header
        assert f"## Skills ({len(skills)})" in content
        # Source-of-Truth uses .codex/ paths (AGENTS.md is Codex-only)
        assert f"| Skills ({len(skills)}) | `.codex/skills/ai-<name>/SKILL.md` |" in content
        assert f"| Agents ({len(agents)}) | `.codex/agents/ai-<name>.md` |" in content

    def test_codex_provider_surfaces_match_install_templates(self) -> None:
        root_hooks = (_PROJECT_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        tpl_hooks = (
            _PROJECT_ROOT
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".codex"
            / "hooks.json"
        ).read_text(encoding="utf-8")
        root_config = (_PROJECT_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        tpl_config = (
            _PROJECT_ROOT
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".codex"
            / "config.toml"
        ).read_text(encoding="utf-8")

        assert root_hooks == tpl_hooks
        assert root_config == tpl_config

    def test_codex_hooks_are_bash_only_for_tool_events(self) -> None:
        hooks = json.loads((_PROJECT_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        pre = hooks["hooks"]["PreToolUse"]
        post = hooks["hooks"]["PostToolUse"]

        assert all(entry["matcher"] == "Bash" for entry in pre)
        assert all(entry["matcher"] == "Bash" for entry in post)


# -- Validation functions --


class TestValidationFunctions:
    """Test validation logic -- uses tmp_path for filesystem state."""

    def test_validate_runbooks_warns_when_empty(self, tmp_path: Path) -> None:
        # Arrange -- empty runbooks dir (monkeypatch RUNBOOKS_ROOT)
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

        # Arrange -- file exists with same content
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

        # Arrange -- file exists with different content
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

        # Arrange -- file doesn't exist
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

        # Arrange -- file exists with different content
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


# -- Canonical content helpers --


class TestCanonicalHelpers:
    """Test read/serialize/format helpers for canonical frontmatter."""

    def test_read_frontmatter_returns_dict(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, read_frontmatter

        fm = read_frontmatter(CLAUDE_SKILLS / "ai-commit" / "SKILL.md")
        assert "name" in fm
        assert "tags" in fm

    def test_read_frontmatter_missing_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "no-fm.md"
        f.write_text("# No frontmatter here\n")

        from scripts.sync_command_mirrors import read_frontmatter

        fm = read_frontmatter(f)
        assert fm == {}

    def test_read_frontmatter_unclosed_fence(self, tmp_path: Path) -> None:
        f = tmp_path / "bad-fm.md"
        f.write_text("---\nname: broken\n# No closing fence\n")

        from scripts.sync_command_mirrors import read_frontmatter

        fm = read_frontmatter(f)
        assert fm == {}

    def test_serialize_frontmatter_round_trip(self) -> None:
        from scripts.sync_command_mirrors import _serialize_frontmatter

        data = {
            "name": "test",
            "version": "1.0.0",
            "description": "A test skill",
            "tags": ["a", "b"],
        }
        result = _serialize_frontmatter(data)
        assert result.startswith("---")
        assert result.endswith("---")
        assert "name: test" in result
        assert "tags: [a, b]" in result

    def test_serialize_frontmatter_preserves_key_order(self) -> None:
        from scripts.sync_command_mirrors import _serialize_frontmatter

        data = {"tags": ["x"], "name": "first", "version": "2.0.0"}
        result = _serialize_frontmatter(data)
        lines = result.splitlines()
        name_idx = next(i for i, ln in enumerate(lines) if ln.startswith("name:"))
        tags_idx = next(i for i, ln in enumerate(lines) if ln.startswith("tags:"))
        assert name_idx < tags_idx

    def test_format_yaml_field_string(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        assert _format_yaml_field("name", "test") == "name: test"

    def test_format_yaml_field_string_with_special_chars(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        result = _format_yaml_field("description", "Run tests: unit + integration")
        assert result == 'description: "Run tests: unit + integration"'

    def test_format_yaml_field_list(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        result = _format_yaml_field("tags", ["a", "b", "c"])
        assert result == "tags: [a, b, c]"

    def test_format_yaml_field_dict(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        result = _format_yaml_field("requires", {"bins": ["ruff"]})
        assert "requires:" in result
        assert "bins:" in result

    def test_format_yaml_field_integer(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        assert _format_yaml_field("count", 42) == "count: 42"


# -- Cross-reference translation --


class TestCrossReferenceTranslation:
    """Test translate_refs path translation for each IDE target."""

    def test_translate_skill_path_claude(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Read `.claude/skills/ai-plan/SKILL.md` for details."
        result = translate_refs(content, "claude")
        # Claude is the canonical form -- unchanged
        assert "`.claude/skills/ai-plan/SKILL.md`" in result

    def test_translate_skill_path_copilot(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Read `.claude/skills/ai-plan/SKILL.md` for details."
        result = translate_refs(content, "copilot")
        assert "`.github/skills/ai-plan/SKILL.md`" in result

    def test_translate_skill_path_codex(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Read `.claude/skills/ai-plan/SKILL.md` for details."
        result = translate_refs(content, "codex")
        assert "`.codex/skills/ai-plan/SKILL.md`" in result

    def test_translate_agent_path_claude(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Delegates to `.claude/agents/ai-build.md`."
        result = translate_refs(content, "claude")
        assert "`.claude/agents/ai-build.md`" in result

    def test_translate_agent_path_copilot(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Delegates to `.claude/agents/ai-build.md`."
        result = translate_refs(content, "copilot")
        assert "`.github/agents/build.agent.md`" in result

    def test_translate_agent_path_codex(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Delegates to `.claude/agents/ai-build.md`."
        result = translate_refs(content, "codex")
        assert "`.codex/agents/ai-build.md`" in result

    def test_specs_not_translated(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Check `.ai-engineering/specs/_active.md`."
        result = translate_refs(content, "claude")
        assert ".ai-engineering/specs/_active.md" in result

    def test_multiple_references_in_one_line(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "See `.claude/skills/ai-plan/SKILL.md` and `.claude/agents/ai-build.md`."
        result = translate_refs(content, "copilot")
        assert ".github/skills/ai-plan/SKILL.md" in result
        assert ".github/agents/build.agent.md" in result

    def test_no_translation_for_bare_text(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "No references here, just plain text."
        result = translate_refs(content, "claude")
        assert result == content


# -- Platform-neutral content --


class TestPlatformNeutralContent:
    """Verify canonical skills avoid Claude Code-specific tool references."""

    _FORBIDDEN_PATTERNS = ("Agent(", "Write tool", "Read tool", "Bash tool", "run_in_background")
    _ALLOWED_EXCEPTIONS = frozenset({"ai-analyze-permissions"})

    def test_platform_neutral_content(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS

        violations: list[str] = []
        for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            bare_name = skill_dir.name.removeprefix("ai-")
            if bare_name in self._ALLOWED_EXCEPTIONS:
                continue
            content = skill_file.read_text(encoding="utf-8")
            for pattern in self._FORBIDDEN_PATTERNS:
                if pattern in content:
                    violations.append(f"{skill_dir.name}: found '{pattern}'")
        assert not violations, (
            f"Platform-specific patterns found in {len(violations)} skill(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# -- Handler parity --


class TestHandlerParity:
    """Verify handler mirrors exist for every canonical handler."""

    def test_handler_parity(self) -> None:
        from scripts.sync_command_mirrors import (
            CLAUDE_SKILLS,
            discover_handlers,
            is_copilot_compatible,
        )

        missing: list[str] = []
        github_skills = _PROJECT_ROOT / ".github" / "skills"
        codex_skills = _PROJECT_ROOT / ".codex" / "skills"

        for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
                continue
            bare_name = skill_dir.name.removeprefix("ai-")
            skill_file = skill_dir / "SKILL.md"
            copilot_ok = skill_file.is_file() and is_copilot_compatible(skill_file)
            handlers = discover_handlers(skill_dir)
            for handler_name, _ in handlers:
                # Check .github/skills mirror (only for copilot-compatible skills)
                if copilot_ok:
                    gh_handler = (
                        github_skills / f"ai-{bare_name}" / "handlers" / f"{handler_name}.md"
                    )
                    if not gh_handler.is_file():
                        missing.append(f".github/skills/ai-{bare_name}/handlers/{handler_name}.md")
                # Check .codex/skills mirror (always generated)
                cx_handler = codex_skills / f"ai-{bare_name}" / "handlers" / f"{handler_name}.md"
                if not cx_handler.is_file():
                    missing.append(f".codex/skills/ai-{bare_name}/handlers/{handler_name}.md")
        assert not missing, f"{len(missing)} handler mirror(s) missing:\n" + "\n".join(
            f"  - {m}" for m in missing
        )


class TestReferenceParity:
    """Verify reference mirrors exist for every canonical reference file."""

    def test_reference_parity(self) -> None:
        from scripts.sync_command_mirrors import (
            CLAUDE_SKILLS,
            discover_reference_files,
            is_copilot_compatible,
        )

        missing: list[str] = []
        github_skills = _PROJECT_ROOT / ".github" / "skills"
        codex_skills = _PROJECT_ROOT / ".codex" / "skills"
        gemini_skills = _PROJECT_ROOT / ".gemini" / "skills"

        for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
                continue
            bare_name = skill_dir.name.removeprefix("ai-")
            skill_file = skill_dir / "SKILL.md"
            copilot_ok = skill_file.is_file() and is_copilot_compatible(skill_file)
            references = discover_reference_files(skill_dir)
            for ref_name, _ in references:
                cx_ref = codex_skills / f"ai-{bare_name}" / "references" / ref_name
                gm_ref = gemini_skills / f"ai-{bare_name}" / "references" / ref_name
                if not cx_ref.is_file():
                    missing.append(f".codex/skills/ai-{bare_name}/references/{ref_name}")
                if not gm_ref.is_file():
                    missing.append(f".gemini/skills/ai-{bare_name}/references/{ref_name}")
                if copilot_ok:
                    gh_ref = github_skills / f"ai-{bare_name}" / "references" / ref_name
                    if not gh_ref.is_file():
                        missing.append(f".github/skills/ai-{bare_name}/references/{ref_name}")

        assert not missing, f"{len(missing)} reference mirror(s) missing:\n" + "\n".join(
            f"  - {m}" for m in missing
        )


# -- Copilot compatibility --


class TestCopilotCompatibility:
    """Test is_copilot_compatible frontmatter check."""

    def test_compatible_when_field_absent(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import is_copilot_compatible

        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: test\n---\n\n# Test\n")
        assert is_copilot_compatible(f) is True

    def test_compatible_when_explicitly_true(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import is_copilot_compatible

        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: test\ncopilot_compatible: true\n---\n\n# Test\n")
        assert is_copilot_compatible(f) is True

    def test_incompatible_when_false(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import is_copilot_compatible

        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: test\ncopilot_compatible: false\n---\n\n# Test\n")
        assert is_copilot_compatible(f) is False

    def test_incompatible_when_false_uppercase(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import is_copilot_compatible

        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: test\ncopilot_compatible: False\n---\n\n# Test\n")
        assert is_copilot_compatible(f) is False


# -- Handler generation --


class TestCopilotHandlerGeneration:
    """Test generate_copilot_handler cross-reference translation."""

    def test_generate_copilot_handler_translates_refs(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import generate_copilot_handler

        handler = tmp_path / "handler.md"
        handler.write_text(
            "Read `.claude/skills/ai-plan/SKILL.md` for the plan.\n"
            "Delegate to `.claude/agents/ai-build.md`.\n",
            encoding="utf-8",
        )

        content = generate_copilot_handler(handler)

        assert ".github/skills/ai-plan/SKILL.md" in content
        assert ".github/agents/build.agent.md" in content
        assert ".claude/" not in content
