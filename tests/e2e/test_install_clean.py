"""E2E test: install on a completely empty repository.

Validates that ``ai-eng install`` on a blank directory creates the
full governance framework structure with all expected directories,
state files, and template content.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ai_engineering.installer.service import install
from ai_engineering.state.io import read_json_model, read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent, InstallState
from ai_engineering.updater.service import update


class TestInstallClean:
    """End-to-end tests for installing on an empty repo."""

    def test_install_creates_ai_engineering_dir(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        ai_dir = tmp_path / ".ai-engineering"
        assert ai_dir.is_dir()

    def test_install_creates_required_dirs(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        ai_dir = tmp_path / ".ai-engineering"

        required_dirs = [
            "contexts",
            "contexts/languages",
            "specs",
            "state",
        ]
        for dirname in required_dirs:
            assert (ai_dir / dirname).is_dir(), f"Missing dir: {dirname}"
        assert (ai_dir / "CONSTITUTION.md").is_file(), "Missing workspace charter: CONSTITUTION.md"

    def test_install_creates_root_constitution(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])

        assert (tmp_path / "CONSTITUTION.md").is_file(), "Missing root CONSTITUTION.md"

    def test_install_creates_state_files(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        state_dir = tmp_path / ".ai-engineering" / "state"

        expected_files = [
            "install-state.json",
            "ownership-map.json",
            "decision-store.json",
            "framework-capabilities.json",
            "instinct-observations.ndjson",
        ]
        for fname in expected_files:
            assert (state_dir / fname).is_file(), f"Missing: {fname}"
        assert not (state_dir / "audit-log.ndjson").exists()
        instincts_dir = tmp_path / ".ai-engineering" / "instincts"
        assert (instincts_dir / "instincts.yml").is_file()
        assert (instincts_dir / "meta.json").is_file()

    def test_install_state_roundtrips(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        state_path = tmp_path / ".ai-engineering" / "state" / "install-state.json"
        state = read_json_model(state_path, InstallState)
        assert state.schema_version == "2.0"

    def test_install_creates_framework_operation(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
        entries = read_ndjson_entries(events_path, FrameworkEvent)
        assert len(entries) >= 1
        assert any(
            e.kind == "framework_operation" and e.detail["operation"] == "install" for e in entries
        )

    def test_install_creates_project_templates(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        assert (tmp_path / "CLAUDE.md").is_file()

    def test_install_creates_governance_content(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        ai_dir = tmp_path / ".ai-engineering"

        # Should have the manifest template
        assert (ai_dir / "manifest.yml").is_file()

        # Should have language contexts
        assert (ai_dir / "contexts" / "languages" / "python.md").is_file()

    def test_install_does_not_seed_team_context_files(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        team_dir = tmp_path / ".ai-engineering" / "contexts" / "team"

        # Team context remains an optional user-owned layer and is no longer seeded.
        assert not team_dir.exists()

        # LESSONS.md lives at .ai-engineering/ root
        lessons_path = tmp_path / ".ai-engineering" / "LESSONS.md"
        assert lessons_path.is_file()
        lessons = lessons_path.read_text(encoding="utf-8")
        assert "## Rules & Patterns" in lessons
        assert "## How to Add Lessons" in lessons
        assert "## Patterns" in lessons
        # Must NOT contain ai-engineering specific lesson entries
        assert "/ai-pr" not in lessons
        assert "/ai-plan" not in lessons

    def test_install_creates_specs_placeholders(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        specs_dir = tmp_path / ".ai-engineering" / "specs"

        assert (specs_dir / "spec.md").is_file()
        assert (specs_dir / "plan.md").is_file()

        spec_content = (specs_dir / "spec.md").read_text(encoding="utf-8")
        assert "No active spec" in spec_content

        plan_content = (specs_dir / "plan.md").read_text(encoding="utf-8")
        assert "No active plan" in plan_content

    def test_install_result_counts(
        self,
        tmp_path: Path,
    ) -> None:
        result = install(tmp_path, stacks=["python"], ides=["vscode"])
        assert result.total_created > 0
        assert result.governance_files.skipped == []
        assert not result.already_installed

    def test_install_leaves_hook_runtime_update_clean(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])

        result = update(tmp_path, dry_run=True)

        hook_updates = [
            change
            for change in result.changes
            if change.action in {"create", "update"}
            and change.path.is_relative_to(tmp_path / ".ai-engineering" / "scripts" / "hooks")
        ]
        assert hook_updates == []

    def test_install_idempotent(self, tmp_path: Path) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        second = install(tmp_path, stacks=["python"], ides=["vscode"])

        assert second.already_installed is True
        # Second install should skip all governance and project files
        assert len(second.governance_files.created) == 0
        assert len(second.project_files.created) == 0

    def test_state_files_are_valid_json(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        state_dir = tmp_path / ".ai-engineering" / "state"

        for f in state_dir.glob("*.json"):
            content = f.read_text(encoding="utf-8")
            data = json.loads(content)
            assert isinstance(data, dict), f"{f.name} is not a JSON object"

    def test_install_auto_installs_hooks_in_git_repo(
        self,
        tmp_path: Path,
    ) -> None:
        subprocess.run(
            ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
        )
        result = install(tmp_path, stacks=["python"], ides=["vscode"])
        hooks_dir = tmp_path / ".git" / "hooks"
        assert (hooks_dir / "pre-commit").is_file()
        assert (hooks_dir / "commit-msg").is_file()
        assert (hooks_dir / "pre-push").is_file()
        assert len(result.hooks.installed) == 3

    def test_install_auto_inits_git_and_installs_hooks(
        self,
        tmp_path: Path,
    ) -> None:
        """Without .git/, install runs git init and installs hooks."""
        result = install(tmp_path, stacks=["python"], ides=["vscode"])
        assert (tmp_path / ".git").is_dir()
        assert len(result.hooks.installed) == 3
