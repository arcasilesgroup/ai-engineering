"""Tests for installer: templates, service, operations, and canonical events."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.installer.operations import (
    InstallerError,
    add_ide,
    add_stack,
    list_status,
    remove_ide,
    remove_stack,
)
from ai_engineering.installer.service import InstallResult, install
from ai_engineering.installer.templates import (
    _VCS_TEMPLATE_TREES,
    copy_file_if_missing,
    copy_project_templates,
    copy_template_tree,
    get_ai_engineering_template_root,
    get_project_template_root,
    resolve_template_maps,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TestTemplateDiscovery:
    """Tests for template root resolution."""

    def test_ai_engineering_template_root_exists(self) -> None:
        root = get_ai_engineering_template_root()
        assert root.is_dir()
        assert (root / "manifest.yml").is_file()

    def test_project_template_root_exists(self) -> None:
        root = get_project_template_root()
        assert root.is_dir()
        assert (root / "CLAUDE.md").is_file()

    def test_ai_engineering_template_root_missing_raises(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import ai_engineering.installer.templates as tpl_mod

        monkeypatch.setattr(tpl_mod, "TEMPLATES_ROOT", tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError, match="Template directory"):
            get_ai_engineering_template_root()

    def test_project_template_root_missing_raises(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import ai_engineering.installer.templates as tpl_mod

        monkeypatch.setattr(tpl_mod, "TEMPLATES_ROOT", tmp_path / "nonexistent")
        with pytest.raises(FileNotFoundError, match="Template directory"):
            get_project_template_root()


class TestCopyFileIfMissing:
    """Tests for single-file create-only copy."""

    def test_copies_when_missing(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "file.txt"
        src.parent.mkdir()
        src.write_text("content")
        dest = tmp_path / "dest" / "file.txt"

        assert copy_file_if_missing(src, dest) is True
        assert dest.read_text() == "content"

    def test_skips_when_existing(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "file.txt"
        src.parent.mkdir()
        src.write_text("new")
        dest = tmp_path / "dest" / "file.txt"
        dest.parent.mkdir()
        dest.write_text("old")

        assert copy_file_if_missing(src, dest) is False
        assert dest.read_text() == "old"


class TestCopyTemplateTree:
    """Tests for recursive tree copy with create-only semantics."""

    def test_copies_entire_tree(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        (src / "a").mkdir(parents=True)
        (src / "a" / "1.txt").write_text("a1")
        (src / "b.txt").write_text("b")

        dest = tmp_path / "dest"
        result = copy_template_tree(src, dest)

        assert len(result.created) == 2
        assert len(result.skipped) == 0
        assert (dest / "a" / "1.txt").read_text() == "a1"
        assert (dest / "b.txt").read_text() == "b"

    def test_skips_existing_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "keep.txt").write_text("new")

        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "keep.txt").write_text("old")

        result = copy_template_tree(src, dest)

        assert len(result.created) == 0
        assert len(result.skipped) == 1
        assert (dest / "keep.txt").read_text() == "old"

    def test_mixed_new_and_existing(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "new.txt").write_text("new")
        (src / "old.txt").write_text("updated")

        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "old.txt").write_text("original")

        result = copy_template_tree(src, dest)

        assert len(result.created) == 1
        assert len(result.skipped) == 1
        assert (dest / "new.txt").read_text() == "new"
        assert (dest / "old.txt").read_text() == "original"


class TestCopyProjectTemplates:
    """Tests for project template mapping."""

    def test_copies_project_templates_to_correct_locations(
        self,
        tmp_path: Path,
    ) -> None:
        result = copy_project_templates(tmp_path)

        # CLAUDE.md → project root
        assert (tmp_path / "CLAUDE.md").is_file()
        # copilot-instructions.md → .github/
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()
        assert len(result.created) >= 3  # at least CLAUDE, AGENTS, copilot-instructions

    def test_skips_existing_project_files(self, tmp_path: Path) -> None:
        # Pre-create CLAUDE.md
        (tmp_path / "CLAUDE.md").write_text("custom")
        result = copy_project_templates(tmp_path)

        assert (tmp_path / "CLAUDE.md").read_text() == "custom"
        assert any(p.name == "CLAUDE.md" for p in result.skipped)

    def test_project_template_trees_include_skills_and_agents(self) -> None:
        maps = resolve_template_maps()
        tree_map = dict(maps.tree_list)
        assert ".github/skills" in tree_map
        assert tree_map[".github/skills"] == ".github/skills"
        assert "agents" in tree_map
        assert tree_map["agents"] == ".github/agents"

    def test_install_creates_github_skills_dir(self, tmp_path: Path) -> None:
        copy_project_templates(tmp_path)
        skills_dir = tmp_path / ".github" / "skills"
        assert skills_dir.is_dir()
        skill_files = list(skills_dir.rglob("SKILL.md"))
        assert len(skill_files) >= 1

    def test_install_creates_github_agents_dir(self, tmp_path: Path) -> None:
        copy_project_templates(tmp_path)
        agents_dir = tmp_path / ".github" / "agents"
        assert agents_dir.is_dir()
        agent_files = list(agents_dir.glob("*.agent.md"))
        assert len(agent_files) >= 1

    def test_vcs_template_trees_has_github_entry(self) -> None:
        assert "github" in _VCS_TEMPLATE_TREES
        trees = dict(_VCS_TEMPLATE_TREES["github"])
        assert "github_templates" in trees
        assert trees["github_templates"] == ".github"

    def test_vcs_provider_github_copies_issue_templates(self, tmp_path: Path) -> None:
        result = copy_project_templates(tmp_path, vcs_provider="github")
        issue_dir = tmp_path / ".github" / "ISSUE_TEMPLATE"
        assert issue_dir.is_dir()
        assert (issue_dir / "bug.yml").is_file()
        assert (issue_dir / "feature.yml").is_file()
        assert (issue_dir / "task.yml").is_file()
        assert (issue_dir / "config.yml").is_file()
        assert (tmp_path / ".github" / "pull_request_template.md").is_file()
        # At least the 5 GitHub template files should appear in created
        github_created = [
            p for p in result.created if "ISSUE_TEMPLATE" in str(p) or "pull_request" in str(p)
        ]
        assert len(github_created) >= 5

    def test_vcs_provider_none_skips_github_templates(self, tmp_path: Path) -> None:
        copy_project_templates(tmp_path)
        issue_dir = tmp_path / ".github" / "ISSUE_TEMPLATE"
        # ISSUE_TEMPLATE should not exist when vcs_provider is not set
        assert not issue_dir.exists()

    def test_codex_provider_copies_agents_tree(self, tmp_path: Path) -> None:
        copy_project_templates(tmp_path, providers=["codex"])
        agents_dir = tmp_path / ".agents" / "skills"
        assert agents_dir.is_dir()
        skill_files = list(agents_dir.glob("*/SKILL.md"))
        assert len(skill_files) >= 28  # skills in .agents/skills/


# ---------------------------------------------------------------------------
# Service — install()
# ---------------------------------------------------------------------------


class TestInstallOnEmptyRepo:
    """Tests for install() on a clean target directory."""

    def test_creates_complete_structure(self, tmp_path: Path) -> None:
        result = install(tmp_path)

        assert isinstance(result, InstallResult)
        assert result.total_created > 0
        assert result.already_installed is False

        # Governance structure created
        assert (tmp_path / ".ai-engineering" / "manifest.yml").is_file()
        assert (tmp_path / ".ai-engineering" / "contexts" / "languages" / "python.md").is_file()

        # State files generated
        assert (tmp_path / ".ai-engineering" / "state" / "install-state.json").is_file()
        assert (tmp_path / ".ai-engineering" / "state" / "ownership-map.json").is_file()
        assert (tmp_path / ".ai-engineering" / "state" / "decision-store.json").is_file()

        # Project files created
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()

        # Canonical state artifacts written
        assert (tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson").is_file()
        assert (tmp_path / ".ai-engineering" / "state" / "framework-capabilities.json").is_file()

    def test_state_files_contain_valid_json(self, tmp_path: Path) -> None:
        install(tmp_path)

        manifest_path = tmp_path / ".ai-engineering" / "state" / "install-state.json"
        data = json.loads(manifest_path.read_text())
        assert data["schema_version"] == "2.0"
        assert "operational_readiness" in data

    def test_custom_stacks_and_ides(self, tmp_path: Path) -> None:
        install(tmp_path, stacks=["python", "node"], ides=["vscode", "terminal"])

        import yaml

        manifest_path2 = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest_data = yaml.safe_load(manifest_path2.read_text())
        assert manifest_data["providers"]["stacks"] == ["python", "node"]
        assert manifest_data["providers"]["ides"] == ["vscode", "terminal"]

    def test_framework_events_record_install_event(self, tmp_path: Path) -> None:
        result = install(tmp_path)
        events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
        lines = events_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["kind"] == "framework_operation"
        assert entry["detail"]["operation"] == "install"
        assert entry["detail"]["created"] == result.total_created


class TestInstallOnExistingRepo:
    """Tests for install() on a repo that already has some files."""

    def test_preserves_existing_files(self, tmp_path: Path) -> None:
        # Pre-create a team-managed file
        team_dir = tmp_path / ".ai-engineering" / "standards" / "team"
        team_dir.mkdir(parents=True)
        (team_dir / "core.md").write_text("custom team standard")

        install(tmp_path)

        # Team file preserved
        assert (team_dir / "core.md").read_text() == "custom team standard"

    def test_idempotent_install(self, tmp_path: Path) -> None:
        result1 = install(tmp_path)
        result2 = install(tmp_path)

        assert result1.total_created > 0
        # Second install creates nothing new (only audit log grows)
        assert result2.total_created == 0
        assert result2.total_skipped > 0

        # State files not duplicated
        assert len(result2.state_files) == 0

    def test_preserves_custom_claude_md(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("my custom CLAUDE")
        install(tmp_path)
        assert (tmp_path / "CLAUDE.md").read_text() == "my custom CLAUDE"


# ---------------------------------------------------------------------------
# Operations — add/remove stack/IDE
# ---------------------------------------------------------------------------


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Return a tmp_path with a completed installation."""
    install(tmp_path)
    return tmp_path


class TestAddStack:
    """Tests for add_stack operation."""

    def test_adds_new_stack(self, installed_project: Path) -> None:
        remove_stack(installed_project, "python")
        manifest = add_stack(installed_project, "python")
        assert "python" in manifest.providers.stacks

    def test_raises_on_duplicate_stack(self, installed_project: Path) -> None:
        with pytest.raises(InstallerError, match="already installed"):
            add_stack(installed_project, "python")

    def test_raises_on_unknown_stack(self, installed_project: Path) -> None:
        with pytest.raises(InstallerError, match="Unknown stack"):
            add_stack(installed_project, "bogus")

    def test_logs_framework_operation(self, installed_project: Path) -> None:
        remove_stack(installed_project, "python")
        add_stack(installed_project, "python")
        events = _read_framework_events(installed_project)
        stack_events = [
            e
            for e in events
            if e["kind"] == "framework_operation" and e["detail"]["operation"] == "stack-add"
        ]
        assert len(stack_events) == 1
        detail = stack_events[0]["detail"]
        assert "python" in (detail.get("message", "") if isinstance(detail, dict) else detail)


class TestRemoveStack:
    """Tests for remove_stack operation."""

    def test_removes_existing_stack(self, installed_project: Path) -> None:
        manifest = remove_stack(installed_project, "python")
        assert "python" not in manifest.providers.stacks

    def test_raises_on_missing_stack(self, installed_project: Path) -> None:
        with pytest.raises(InstallerError, match="not installed"):
            remove_stack(installed_project, "nonexistent")


class TestAddIde:
    """Tests for add_ide operation."""

    def test_adds_new_ide(self, installed_project: Path) -> None:
        manifest = add_ide(installed_project, "vscode")
        assert "vscode" in manifest.providers.ides
        assert "terminal" in manifest.providers.ides

    def test_raises_on_duplicate_ide(self, installed_project: Path) -> None:
        with pytest.raises(InstallerError, match="already installed"):
            add_ide(installed_project, "terminal")


class TestRemoveIde:
    """Tests for remove_ide operation."""

    def test_removes_existing_ide(self, installed_project: Path) -> None:
        manifest = remove_ide(installed_project, "terminal")
        assert "terminal" not in manifest.providers.ides

    def test_raises_on_missing_ide(self, installed_project: Path) -> None:
        with pytest.raises(InstallerError, match="not installed"):
            remove_ide(installed_project, "nonexistent")


class TestListStatus:
    """Tests for list_status operation."""

    def test_returns_current_manifest(self, installed_project: Path) -> None:
        manifest = list_status(installed_project)
        assert isinstance(manifest, ManifestConfig)
        assert "python" in manifest.providers.stacks

    def test_reflects_mutations(self, installed_project: Path) -> None:
        remove_stack(installed_project, "python")
        add_stack(installed_project, "python")
        manifest = list_status(installed_project)
        assert "python" in manifest.providers.stacks

    def test_raises_without_install(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError, match="not installed"):
            list_status(tmp_path)


class TestOperationsWithoutInstall:
    """Operations on uninstalled projects raise InstallerError."""

    def test_add_stack_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError):
            add_stack(tmp_path, "python")

    def test_remove_stack_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError):
            remove_stack(tmp_path, "python")

    def test_add_ide_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError):
            add_ide(tmp_path, "vscode")

    def test_remove_ide_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError):
            remove_ide(tmp_path, "vscode")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_framework_events(project: Path) -> list[dict[str, object]]:
    """Read all framework events as dicts."""
    events_path = project / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not events_path.exists():
        return []
    return [
        json.loads(line) for line in events_path.read_text().strip().splitlines() if line.strip()
    ]
