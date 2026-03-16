"""Tests for ai_engineering.updater.service -- legacy migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.updater.service import _migrate_legacy_dirs

pytestmark = pytest.mark.unit


class TestMigrateLegacyDirs:
    """Tests for _migrate_legacy_dirs safety logic."""

    def test_removes_legacy_dirs_when_ide_has_content(self, tmp_path: Path) -> None:
        """When IDE directories have content, legacy dirs are removed."""
        ai = tmp_path / ".ai-engineering"
        (ai / "agents").mkdir(parents=True)
        (ai / "agents" / "plan.md").write_text("old agent", encoding="utf-8")
        (ai / "skills" / "commit").mkdir(parents=True)
        (ai / "skills" / "commit" / "SKILL.md").write_text("old skill", encoding="utf-8")

        # Create IDE dir with content so safety check passes
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / ".claude" / "agents" / "ai-plan.md").write_text("new agent", encoding="utf-8")

        removed = _migrate_legacy_dirs(tmp_path, ai)

        assert not (ai / "agents").exists()
        assert not (ai / "skills").exists()
        assert set(removed) == {"agents", "skills"}

    def test_skips_when_no_ide_dirs_have_content(self, tmp_path: Path) -> None:
        """When no IDE dirs have content, legacy dirs are preserved (safety)."""
        ai = tmp_path / ".ai-engineering"
        (ai / "agents").mkdir(parents=True)
        (ai / "agents" / "plan.md").write_text("old agent", encoding="utf-8")

        removed = _migrate_legacy_dirs(tmp_path, ai)

        assert (ai / "agents").exists()
        assert removed == []

    def test_noop_when_no_legacy_dirs_exist(self, tmp_path: Path) -> None:
        """When no legacy directories exist, returns empty list."""
        ai = tmp_path / ".ai-engineering"
        ai.mkdir(parents=True)

        removed = _migrate_legacy_dirs(tmp_path, ai)

        assert removed == []

    def test_removes_only_existing_legacy_dirs(self, tmp_path: Path) -> None:
        """Only agents/ exists (no skills/) -- removes only agents/."""
        ai = tmp_path / ".ai-engineering"
        (ai / "agents").mkdir(parents=True)
        (ai / "agents" / "build.md").write_text("old", encoding="utf-8")

        # IDE content via .agents/ candidate
        (tmp_path / ".agents" / "skills").mkdir(parents=True)
        (tmp_path / ".agents" / "skills" / "SKILL.md").write_text("content", encoding="utf-8")

        removed = _migrate_legacy_dirs(tmp_path, ai)

        assert not (ai / "agents").exists()
        assert removed == ["agents"]

    def test_github_agents_ide_dir_satisfies_safety_check(self, tmp_path: Path) -> None:
        """The .github/agents/ IDE candidate also satisfies the safety check."""
        ai = tmp_path / ".ai-engineering"
        (ai / "skills" / "code").mkdir(parents=True)
        (ai / "skills" / "code" / "SKILL.md").write_text("old", encoding="utf-8")

        (tmp_path / ".github" / "agents").mkdir(parents=True)
        (tmp_path / ".github" / "agents" / "build.md").write_text("gh agent", encoding="utf-8")

        removed = _migrate_legacy_dirs(tmp_path, ai)

        assert not (ai / "skills").exists()
        assert removed == ["skills"]
