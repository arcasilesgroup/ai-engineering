"""Integration tests for AI provider add/remove/list commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.operations import (
    InstallerError,
    add_provider,
    list_status,
    remove_provider,
)
from ai_engineering.installer.service import install

pytestmark = pytest.mark.integration


class TestProviderAdd:
    """Tests for add_provider operation."""

    def test_add_provider_to_installed_project(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["claude_code"])
        manifest = add_provider(tmp_path, "github_copilot")
        assert "github_copilot" in manifest.providers.ai_providers.enabled
        # Verify copilot files were created
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()

    def test_add_duplicate_provider_raises(self, tmp_path: Path) -> None:
        install(tmp_path)
        with pytest.raises(InstallerError, match="already enabled"):
            add_provider(tmp_path, "claude_code")

    def test_add_unknown_provider_raises(self, tmp_path: Path) -> None:
        install(tmp_path)
        with pytest.raises(InstallerError, match="Unknown provider"):
            add_provider(tmp_path, "unknown_ai")

    def test_add_provider_without_framework_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InstallerError, match="not installed"):
            add_provider(tmp_path, "gemini")

    def test_add_gemini_creates_agents_md(self, tmp_path: Path) -> None:
        install(tmp_path)
        add_provider(tmp_path, "gemini")
        assert (tmp_path / "AGENTS.md").is_file()


class TestProviderRemove:
    """Tests for remove_provider operation."""

    def test_remove_provider(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["claude_code", "github_copilot"])
        manifest = remove_provider(tmp_path, "github_copilot")
        assert "github_copilot" not in manifest.providers.ai_providers.enabled
        assert "claude_code" in manifest.providers.ai_providers.enabled

    def test_remove_last_provider_raises(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["claude_code"])
        with pytest.raises(InstallerError, match="Cannot remove the last"):
            remove_provider(tmp_path, "claude_code")

    def test_remove_nonexistent_provider_raises(self, tmp_path: Path) -> None:
        install(tmp_path)
        with pytest.raises(InstallerError, match="not enabled"):
            remove_provider(tmp_path, "gemini")

    def test_remove_primary_promotes_next(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["claude_code", "github_copilot"])
        manifest = remove_provider(tmp_path, "claude_code")
        assert manifest.providers.ai_providers.primary == "github_copilot"

    def test_remove_does_not_delete_shared_agents_md(
        self,
        tmp_path: Path,
    ) -> None:
        """When removing a provider that uses AGENTS.md but another active
        provider also uses it, AGENTS.md should NOT be deleted."""
        install(tmp_path, ai_providers=["github_copilot", "gemini"])
        # Both copilot and gemini use AGENTS.md
        assert (tmp_path / "AGENTS.md").is_file()
        remove_provider(tmp_path, "gemini")
        # AGENTS.md should still exist (needed by copilot)
        assert (tmp_path / "AGENTS.md").is_file()


class TestProviderList:
    """Tests for listing providers via manifest."""

    def test_list_default_providers(self, tmp_path: Path) -> None:
        install(tmp_path)
        manifest = list_status(tmp_path)
        assert manifest.providers.ai_providers.primary == "claude_code"
        assert "claude_code" in manifest.providers.ai_providers.enabled

    def test_list_custom_providers(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["github_copilot", "gemini"])
        manifest = list_status(tmp_path)
        assert manifest.providers.ai_providers.primary == "github_copilot"
        assert "gemini" in manifest.providers.ai_providers.enabled


class TestProviderAwareInstall:
    """Tests for provider-aware install behavior."""

    def test_install_claude_only(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["claude_code"])
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / ".claude").is_dir()
        # Should NOT create copilot files
        assert not (tmp_path / ".github" / "copilot-instructions.md").exists()
        assert not (tmp_path / "AGENTS.md").exists()

    def test_install_copilot_only(self, tmp_path: Path) -> None:
        install(tmp_path, ai_providers=["github_copilot"])
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()
        # Should NOT create claude files
        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / ".claude").is_dir()

    def test_install_multiple_providers(self, tmp_path: Path) -> None:
        install(
            tmp_path,
            ai_providers=["claude_code", "github_copilot"],
        )
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / ".claude").is_dir()
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / ".github" / "copilot-instructions.md").is_file()

    def test_install_default_providers_copies_all(self, tmp_path: Path) -> None:
        """When no --provider flag, defaults to claude_code."""
        install(tmp_path)
        assert (tmp_path / "CLAUDE.md").is_file()
