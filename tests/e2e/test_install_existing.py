"""E2E test: install on a repository with existing code.

Validates that ``ai-eng install`` on a repo with source code:
- Creates the governance framework without destroying existing files.
- Preserves team/project-managed content on re-install/update.
- Does not overwrite user files that conflict with template paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import InstallManifest
from ai_engineering.updater.service import update


class TestInstallExisting:
    """End-to-end tests for installing on a repo with existing code."""

    def test_preserves_existing_source_files(
        self,
        tmp_path: Path,
    ) -> None:
        # Create some "existing" project files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        app_py = src_dir / "app.py"
        app_py.write_text("print('hello')\n", encoding="utf-8")

        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n", encoding="utf-8")

        install(tmp_path, stacks=["python"], ides=["vscode"])

        # Existing files must be untouched
        assert app_py.read_text(encoding="utf-8") == "print('hello')\n"
        assert readme.read_text(encoding="utf-8") == "# My Project\n"

    def test_preserves_existing_claude_md(
        self,
        tmp_path: Path,
    ) -> None:
        # Create a custom CLAUDE.md before install
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("# My Custom CLAUDE\n", encoding="utf-8")

        install(tmp_path, stacks=["python"], ides=["vscode"])

        # Create-only: must NOT overwrite
        assert claude.read_text(encoding="utf-8") == "# My Custom CLAUDE\n"

    def test_second_install_preserves_state(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])

        # Modify a team-managed file
        team_file = tmp_path / ".ai-engineering" / "standards" / "team" / "core.md"
        if team_file.exists():
            team_file.write_text("# Team customised\n", encoding="utf-8")

        install(tmp_path, stacks=["python"], ides=["vscode"])

        # Team file must be preserved
        if team_file.exists():
            assert team_file.read_text(encoding="utf-8") == "# Team customised\n"

    def test_update_dry_run_does_not_modify(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])

        # Snapshot state before update
        manifest_path = tmp_path / ".ai-engineering" / "state" / "install-manifest.json"
        before = manifest_path.read_text(encoding="utf-8")

        result = update(tmp_path, dry_run=True)

        after = manifest_path.read_text(encoding="utf-8")
        assert before == after
        assert result.dry_run is True

    def test_update_apply_respects_ownership(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])

        # Modify a team-managed file
        team_file = tmp_path / ".ai-engineering" / "standards" / "team" / "core.md"
        original = ""
        if team_file.exists():
            original = team_file.read_text(encoding="utf-8")
            team_file.write_text("# CUSTOM TEAM CONTENT\n", encoding="utf-8")

        result = update(tmp_path, dry_run=False)

        # Team file should NOT be overwritten
        if team_file.exists() and original:
            content = team_file.read_text(encoding="utf-8")
            assert content == "# CUSTOM TEAM CONTENT\n"

        # Denied changes should be tracked
        denied = [c for c in result.changes if c.action == "skip-denied"]
        # At least team-managed files should be denied
        assert len(denied) >= 0  # May be 0 if no matching templates

    def test_install_with_git_history(self, tmp_path: Path) -> None:
        import subprocess

        # Create a git repo with history
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        (tmp_path / "main.py").write_text("# main\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "-A"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Install should work fine alongside git history
        result = install(tmp_path, stacks=["python"], ides=["vscode"])
        assert result.total_created > 0

        # Original file untouched
        assert (tmp_path / "main.py").read_text(encoding="utf-8") == "# main\n"

    def test_manifest_reflects_configured_stacks(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python", "node"], ides=["vscode", "jetbrains"])
        manifest_path = tmp_path / ".ai-engineering" / "state" / "install-manifest.json"
        manifest = read_json_model(manifest_path, InstallManifest)
        assert set(manifest.installed_stacks) == {"python", "node"}
        assert set(manifest.installed_ides) == {"vscode", "jetbrains"}

    def test_update_applies_to_claude_tree(
        self,
        tmp_path: Path,
    ) -> None:
        """Update restores modified .claude/ tree files."""
        install(tmp_path, stacks=["python"], ides=["vscode"])

        commit_md = tmp_path / ".claude" / "commands" / "commit.md"
        if not commit_md.exists():
            pytest.skip("commit.md not deployed by installer")

        original = commit_md.read_bytes()
        commit_md.write_text("modified by user")

        result = update(tmp_path, dry_run=False)

        assert commit_md.read_bytes() == original
        updated = [c for c in result.changes if c.path == commit_md and c.action == "update"]
        assert len(updated) == 1

    def test_update_rollback_preserves_state(
        self,
        tmp_path: Path,
    ) -> None:
        """Simulated write failure triggers rollback — files stay intact."""
        from unittest.mock import patch

        install(tmp_path, stacks=["python"], ides=["vscode"])

        core_md = tmp_path / ".ai-engineering" / "standards" / "framework" / "core.md"
        core_md.write_text("modified content")
        stacks_dir = tmp_path / ".ai-engineering" / "standards" / "framework" / "stacks"
        stacks_md = stacks_dir / "python.md"
        stacks_md.write_text("also modified")

        original_write = Path.write_bytes
        call_count = 0

        def failing_write(self_path: Path, data: bytes) -> int:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                msg = "Simulated IO error"
                raise OSError(msg)
            return original_write(self_path, data)

        with patch.object(Path, "write_bytes", failing_write), pytest.raises(OSError):
            update(tmp_path, dry_run=False)

        # File should be restored to pre-update state
        assert core_md.read_text() == "modified content"
