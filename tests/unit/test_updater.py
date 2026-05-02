"""Tests for ai_engineering.updater.service -- legacy migration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.config.manifest import RootEntryPointConfig, RootEntryPointSyncConfig
from ai_engineering.state.models import OwnershipMap
from ai_engineering.updater.service import (
    _initialize_update_context,
    _merge_missing_ownership_rules,
    _migrate_legacy_dirs,
    update,
)


def _root_entry_point(owner: str) -> RootEntryPointConfig:
    return RootEntryPointConfig(
        owner=owner,
        canonical_source="CONSTITUTION.md",
        runtime_role="ide-overlay",
        sync=RootEntryPointSyncConfig(
            mode="copy",
            template_path="src/ai_engineering/templates/project/CLAUDE.md",
            mirror_paths=[],
        ),
    )


def _write_minimal_manifest(project: Path) -> None:
    ai_eng_dir = project / ".ai-engineering"
    (ai_eng_dir / "state").mkdir(parents=True)
    (ai_eng_dir / "manifest.yml").write_text(
        "ai_providers:\n"
        "  enabled: []\n"
        "providers:\n"
        "  stacks: [python]\n"
        "ownership:\n"
        "  root_entry_points: {}\n",
        encoding="utf-8",
    )


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

        # IDE content via .codex/ candidate
        (tmp_path / ".codex" / "skills").mkdir(parents=True)
        (tmp_path / ".codex" / "skills" / "SKILL.md").write_text("content", encoding="utf-8")

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


class TestMergeMissingOwnershipRules:
    def test_uses_manifest_root_entry_point_contract(self) -> None:
        ownership = OwnershipMap()

        changed = _merge_missing_ownership_rules(
            ownership,
            root_entry_points={
                "CLAUDE.md": _root_entry_point("team"),
            },
        )

        assert changed is True
        assert ownership.is_update_allowed("CLAUDE.md") is False
        assert ownership.has_deny_rule("CLAUDE.md") is True

    def test_missing_root_entry_point_metadata_does_not_invent_root_rules(self) -> None:
        ownership = OwnershipMap()

        changed = _merge_missing_ownership_rules(ownership, root_entry_points=None)

        assert changed is True
        assert ownership.is_update_allowed(".ai-engineering/README.md") is True
        assert ownership.is_update_allowed("CLAUDE.md") is False
        assert ownership.has_deny_rule("CLAUDE.md") is False
        assert ownership.is_update_allowed("AGENTS.md") is False
        assert ownership.has_deny_rule("AGENTS.md") is False


class TestInitializeUpdateContext:
    def test_requires_manifest_contract(self, tmp_path: Path) -> None:
        with pytest.raises(
            FileNotFoundError, match="Manifest contract not found for updater context"
        ):
            _initialize_update_context(tmp_path, dry_run=True)

    def test_dry_run_does_not_migrate_legacy_hooks(self, tmp_path: Path) -> None:
        _write_minimal_manifest(tmp_path)

        legacy_hooks = tmp_path / "scripts" / "hooks"
        legacy_hooks.mkdir(parents=True)
        (legacy_hooks / "pre-commit.py").write_text("print('legacy')\n", encoding="utf-8")

        result = update(tmp_path, dry_run=True)

        assert result.dry_run is True
        assert (legacy_hooks / "pre-commit.py").is_file()
        assert not (tmp_path / ".ai-engineering" / "scripts" / "hooks").exists()

    def test_apply_failure_restores_deleted_orphans(self, tmp_path: Path) -> None:
        _write_minimal_manifest(tmp_path)
        orphan = tmp_path / ".codex" / "config.toml"
        orphan.parent.mkdir(parents=True)
        orphan.write_text("legacy codex config\n", encoding="utf-8")

        with (
            patch("ai_engineering.updater.service._evaluate_governance_files", return_value=[]),
            patch("ai_engineering.updater.service._evaluate_project_files", return_value=[]),
            patch("ai_engineering.updater.service.write_json_model", side_effect=OSError("boom")),
            pytest.raises(OSError, match="boom"),
        ):
            update(tmp_path, dry_run=False)

        assert orphan.read_text(encoding="utf-8") == "legacy codex config\n"
