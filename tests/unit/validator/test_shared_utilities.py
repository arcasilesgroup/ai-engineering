"""Tests for shared utility functions from validator._shared.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4.
Covers FileCache, _is_source_repo, _instruction_files, _glob_files,
_is_excluded, _extract_section, _is_table_separator, _parse_skill_names,
_parse_agent_names, _extract_subsection, _parse_*_from_subsection,
and _extract_listings.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    FileCache,
    _extract_listings,
    _extract_section,
    _extract_subsection,
    _glob_files,
    _instruction_files,
    _is_excluded,
    _is_source_repo,
    _is_table_separator,
    _parse_agent_names,
    _parse_agent_names_from_subsection,
    _parse_skill_names,
    _parse_skill_names_from_subsection,
)


class TestIsSourceRepo:
    """Tests for _is_source_repo detection."""

    def test_source_repo_detected(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        assert _is_source_repo(tmp_path) is True

    def test_non_source_repo(self, tmp_path: Path) -> None:
        assert _is_source_repo(tmp_path) is False


class TestInstructionFiles:
    """Tests for _instruction_files returning correct list by repo type."""

    def test_source_repo_includes_templates(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "manifest.yml").write_text(
            "name: test-project\n"
            "version: 1.0.0\n"
            "surfaces:\n"
            "  enabled: [claude-code, github-copilot]\n"
            "  primary: claude-code\n"
            "ownership:\n"
            "  root_entry_points:\n"
            "    CLAUDE.md:\n"
            "      owner: framework\n"
            "      canonical_source: CLAUDE.md\n"
            "      runtime_role: ide-overlay\n"
            "      sync:\n"
            "        mode: copy\n"
            "        template_path: src/ai_engineering/templates/project/CLAUDE.md\n"
            "        mirror_paths: []\n"
            "    AGENTS.md:\n"
            "      owner: framework\n"
            "      canonical_source: scripts/sync_mirrors/core.py:generate_agents_md\n"
            "      runtime_role: shared-runtime-contract\n"
            "      sync:\n"
            "        mode: generate\n"
            "        template_path: src/ai_engineering/templates/project/AGENTS.md\n"
            "        mirror_paths: []\n"
            "    .github/copilot-instructions.md:\n"
            "      owner: framework\n"
            "      canonical_source: src/ai_engineering/templates/project/copilot-instructions.md\n"
            "      runtime_role: ide-overlay\n"
            "      sync:\n"
            "        mode: generate\n"
            "        template_path: src/ai_engineering/templates/project/copilot-instructions.md\n"
            "        mirror_paths: []\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        files = _instruction_files(tmp_path)
        assert any("templates" in f for f in files)
        assert len(files) == 6  # 3 base + 3 template

    def test_non_source_repo_without_manifest_uses_base_instruction_fallback(
        self, tmp_path: Path
    ) -> None:
        assert _instruction_files(tmp_path) == [
            ".github/copilot-instructions.md",
            "AGENTS.md",
            "CLAUDE.md",
        ]


class TestGlobFiles:
    """Tests for _glob_files utility."""

    def test_glob_collects_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        result = _glob_files(tmp_path, ["*.md"])
        names = {p.name for p in result}
        assert names == {"a.md", "b.md"}

    def test_glob_multiple_patterns(self, tmp_path: Path) -> None:
        (tmp_path / "x.md").write_text("x")
        (tmp_path / "y.yml").write_text("y: 1")
        result = _glob_files(tmp_path, ["*.md", "*.yml"])
        names = {p.name for p in result}
        assert names == {"x.md", "y.yml"}

    def test_glob_excludes_directories(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir.md"
        sub.mkdir()
        (tmp_path / "real.md").write_text("real")
        result = _glob_files(tmp_path, ["*.md"])
        assert all(p.is_file() for p in result)
        assert len(result) == 1


class TestIsExcluded:
    """Tests for _is_excluded prefix checking."""

    def test_excluded_prefix_matches(self) -> None:
        assert _is_excluded(Path("team/readme.md"), ["team/"]) is True

    def test_non_excluded_prefix(self) -> None:
        assert _is_excluded(Path("reference/principles.md"), ["team/"]) is False


class TestExtractSection:
    """Tests for _extract_section markdown parser."""

    def test_extracts_section_content(self) -> None:
        content = "## Skills\n\nList of skills.\n\n## Agents\n\nList of agents.\n"
        section = _extract_section(content, "Skills")
        assert "List of skills" in section
        assert "List of agents" not in section

    def test_missing_section_returns_empty(self) -> None:
        content = "## Other\n\nSome content.\n"
        assert _extract_section(content, "Skills") == ""

    def test_last_section_captures_to_end(self) -> None:
        content = "## Skills\n\nOnly section.\n"
        section = _extract_section(content, "Skills")
        assert "Only section." in section


class TestIsTableSeparator:
    """Tests for _is_table_separator."""

    def test_separator_row(self) -> None:
        assert _is_table_separator("|---|---|") is True
        assert _is_table_separator("|:---:|:---:|") is True

    def test_non_separator(self) -> None:
        assert _is_table_separator("| name | value |") is False
        assert _is_table_separator("") is False


class TestParseSkillNames:
    """Tests for _parse_skill_names from bullet and table formats."""

    def test_bullet_format(self) -> None:
        section = "- `.claude/skills/ai-test/SKILL.md`\n- `.claude/skills/ai-debug/SKILL.md`\n"
        names = _parse_skill_names(section)
        assert names == {"ai-test", "ai-debug"}

    def test_table_format(self) -> None:
        section = "| Skills (alphabetical) |\n|---|\n| ai-test, ai-debug |\n"
        names = _parse_skill_names(section)
        assert names == {"ai-test", "ai-debug"}

    def test_empty_section(self) -> None:
        assert _parse_skill_names("") == set()


class TestParseAgentNames:
    """Tests for _parse_agent_names from bullet and table formats."""

    def test_bullet_format(self) -> None:
        section = "- `.claude/agents/ai-build.md`\n- `.claude/agents/ai-plan.md`\n"
        names = _parse_agent_names(section)
        assert names == {"ai-build", "ai-plan"}

    def test_table_format(self) -> None:
        section = (
            "| Agent | Purpose |\n|---|---|\n| ai-build | writes code |\n| ai-plan | planning |\n"
        )
        names = _parse_agent_names(section)
        assert names == {"ai-build", "ai-plan"}

    def test_skips_header_row(self) -> None:
        section = "| Agent | Purpose |\n|---|---|\n"
        names = _parse_agent_names(section)
        assert names == set()

    def test_empty_cells_skipped(self) -> None:
        section = "| | Purpose |\n|---|---|\n"
        names = _parse_agent_names(section)
        assert names == set()


class TestExtractSubsection:
    """Tests for _extract_subsection (level-4 heading parser)."""

    def test_extracts_subsection(self) -> None:
        content = "#### Skills\n\nSkill content.\n\n#### Agents\n\nAgent content.\n"
        section = _extract_subsection(content, "Skills")
        assert "Skill content" in section
        assert "Agent content" not in section

    def test_missing_subsection_returns_empty(self) -> None:
        content = "#### Other\n\nSome content.\n"
        assert _extract_subsection(content, "Skills") == ""

    def test_stops_at_higher_heading(self) -> None:
        content = "#### Skills\n\nContent.\n\n### Higher\n\nOther.\n"
        section = _extract_subsection(content, "Skills")
        assert "Content." in section
        assert "Other." not in section

    def test_stops_at_same_level_heading(self) -> None:
        content = "#### Skills\n\nFirst.\n\n#### Next\n\nSecond.\n"
        section = _extract_subsection(content, "Skills")
        assert "First." in section
        assert "Second." not in section


class TestParseNamesFromSubsection:
    """Tests for _parse_skill_names_from_subsection and _parse_agent_names_from_subsection."""

    def test_skill_names_from_subsection(self) -> None:
        content = "#### Skills\n\n- `.claude/skills/ai-test/SKILL.md`\n\n#### Agents\n\n"
        names = _parse_skill_names_from_subsection(content, "Skills")
        assert names == {"ai-test"}

    def test_agent_names_from_subsection(self) -> None:
        content = "#### Skills\n\n\n#### Agents\n\n- `.codex/agents/ai-build.md`\n"
        names = _parse_agent_names_from_subsection(content, "Agents")
        assert names == {"ai-build"}

    def test_missing_subsection_returns_empty(self) -> None:
        assert _parse_skill_names_from_subsection("#### Other\n", "Skills") == set()
        assert _parse_agent_names_from_subsection("#### Other\n", "Agents") == set()


class TestExtractListings:
    """Tests for _extract_listings with fallback to subsection parsing."""

    def test_top_level_sections(self) -> None:
        content = (
            "## Skills\n\n"
            "- `.claude/skills/ai-test/SKILL.md`\n\n"
            "## Agents\n\n"
            "- `.claude/agents/ai-build.md`\n"
        )
        skills, agents = _extract_listings(content)
        assert skills == {"ai-test"}
        assert agents == {"ai-build"}

    def test_fallback_to_subsections(self) -> None:
        content = (
            "## Overview\n\nSome overview.\n\n"
            "#### Skills\n\n"
            "- `.claude/skills/ai-debug/SKILL.md`\n\n"
            "#### Agents\n\n"
            "- `.codex/agents/ai-plan.md`\n"
        )
        skills, agents = _extract_listings(content)
        assert skills == {"ai-debug"}
        assert agents == {"ai-plan"}

    def test_empty_content(self) -> None:
        skills, agents = _extract_listings("")
        assert skills == set()
        assert agents == set()


class TestFileCache:
    """Tests for FileCache utility."""

    def test_sha256_caching(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        cache = FileCache()
        h1 = cache.sha256(f)
        h2 = cache.sha256(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest length

    def test_rglob_caching(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        cache = FileCache()
        r1 = cache.rglob(tmp_path, "*.md")
        r2 = cache.rglob(tmp_path, "*.md")
        assert r1 == r2
        assert len(r1) == 2

    def test_glob_files_via_cache(self, tmp_path: Path) -> None:
        (tmp_path / "x.md").write_text("x")
        (tmp_path / "y.yml").write_text("y: 1")
        cache = FileCache()
        result = cache.glob_files(tmp_path, ["*.md", "*.yml"])
        assert len(result) == 2
