"""Integration tests for surface add/remove/list commands.

spec-133 D-133-16 collapsed the AI-provider axis (`add_provider`) and the
IDE axis (`add_ide`) into a single Surface axis with `add_surface` /
`remove_surface` against `manifest.surfaces.enabled`. This file tests the
surviving CRUD surface; the old per-provider helpers were deleted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.operations import (
    InstallerError,
    add_surface,
    list_status,
    remove_surface,
)
from ai_engineering.installer.service import install


class TestSurfaceAdd:
    """Tests for add_surface operation."""

    def test_add_surface_to_installed_project(self, tmp_path: Path) -> None:
        install(tmp_path, surfaces=["claude-code"])
        manifest = add_surface(tmp_path, "github-copilot")
        assert "github-copilot" in manifest.surfaces.enabled
        # Verify copilot files were created
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()

    def test_add_duplicate_surface_raises(self, tmp_path: Path) -> None:
        install(tmp_path)
        with pytest.raises(InstallerError, match="already"):
            add_surface(tmp_path, "claude-code")

    def test_add_unknown_surface_raises(self, tmp_path: Path) -> None:
        install(tmp_path)
        with pytest.raises(InstallerError, match="Unknown surface"):
            add_surface(tmp_path, "unknown_ai")

    def test_add_surface_without_framework_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError, match="not installed"):
            add_surface(tmp_path, "antigravity")

    def test_add_antigravity_creates_agents_md(self, tmp_path: Path) -> None:
        install(tmp_path)
        add_surface(tmp_path, "antigravity")
        assert (tmp_path / "AGENTS.md").is_file()


class TestSurfaceRemove:
    """Tests for remove_surface operation."""

    def test_remove_surface(self, tmp_path: Path) -> None:
        install(tmp_path, surfaces=["claude-code", "github-copilot"])
        manifest = remove_surface(tmp_path, "github-copilot")
        assert "github-copilot" not in manifest.surfaces.enabled
        assert "claude-code" in manifest.surfaces.enabled

    def test_remove_last_surface_raises(self, tmp_path: Path) -> None:
        install(tmp_path, surfaces=["claude-code"])
        with pytest.raises(InstallerError, match="last"):
            remove_surface(tmp_path, "claude-code")

    def test_remove_nonexistent_surface_raises(self, tmp_path: Path) -> None:
        install(tmp_path)
        with pytest.raises(InstallerError, match="not enabled"):
            remove_surface(tmp_path, "antigravity")

    def test_remove_does_not_delete_shared_agents_md(
        self,
        tmp_path: Path,
    ) -> None:
        """When removing a surface that uses AGENTS.md but another active
        surface also uses it, AGENTS.md should NOT be deleted."""
        install(tmp_path, surfaces=["github-copilot", "antigravity"])
        # Both copilot and antigravity use AGENTS.md
        assert (tmp_path / "AGENTS.md").is_file()
        remove_surface(tmp_path, "antigravity")
        # AGENTS.md should still exist (needed by copilot)
        assert (tmp_path / "AGENTS.md").is_file()


class TestSurfaceList:
    """Tests for listing surfaces via manifest."""

    def test_list_default_surfaces(self, tmp_path: Path) -> None:
        install(tmp_path)
        manifest = list_status(tmp_path)
        assert "claude-code" in manifest.surfaces.enabled

    def test_list_custom_surfaces(self, tmp_path: Path) -> None:
        install(tmp_path, surfaces=["github-copilot", "antigravity"])
        manifest = list_status(tmp_path)
        assert "github-copilot" in manifest.surfaces.enabled
        assert "antigravity" in manifest.surfaces.enabled


class TestSurfaceAwareInstall:
    """Tests for surface-aware install behavior."""

    def test_install_claude_only(self, tmp_path: Path) -> None:
        install(tmp_path, surfaces=["claude-code"])
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / ".claude").is_dir()
        # Should NOT create copilot files
        assert not (tmp_path / ".github" / "copilot-instructions.md").exists()
        assert not (tmp_path / "AGENTS.md").exists()

    def test_install_copilot_only(self, tmp_path: Path) -> None:
        install(tmp_path, surfaces=["github-copilot"])
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()
        # Should NOT create claude files
        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / ".claude").is_dir()

    def test_install_multiple_surfaces(self, tmp_path: Path) -> None:
        install(
            tmp_path,
            surfaces=["claude-code", "github-copilot"],
        )
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / ".claude").is_dir()
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()

    def test_install_default_surfaces(self, tmp_path: Path) -> None:
        """When no --surface flag, defaults to claude-code."""
        install(tmp_path)
        assert (tmp_path / "CLAUDE.md").is_file()
