"""Unit tests for installer/tools module."""

from __future__ import annotations

from unittest.mock import patch

from ai_engineering.installer.tools import ToolInstallResult, ensure_tool, provider_required_tools


class TestEnsureTool:
    """Tests for the ensure_tool function."""

    def test_tool_already_available(self) -> None:
        # Act
        with patch("ai_engineering.installer.tools.shutil.which", return_value="/usr/bin/gh"):
            result = ensure_tool("gh")

        # Assert
        assert result.available is True
        assert result.attempted is False
        assert result.installed is False

    def test_tool_missing_auto_install_disabled(self) -> None:
        # Arrange
        import os

        env = {k: v for k, v in os.environ.items() if k != "AI_ENG_AUTO_INSTALL_TOOLS"}

        # Act
        with (
            patch("ai_engineering.installer.tools.shutil.which", return_value=None),
            patch.dict("os.environ", {}, clear=False),
            patch.dict("os.environ", env, clear=True),
        ):
            result = ensure_tool("gh", allow_install=False)

        # Assert
        assert result.available is False
        assert result.attempted is False
        assert "disabled" in result.detail.lower() or result.detail == ""

    def test_tool_missing_explicit_no_install(self) -> None:
        with patch("ai_engineering.installer.tools.shutil.which", return_value=None):
            result = ensure_tool("gh", allow_install=False)
        assert result.available is False
        assert result.attempted is False

    def test_tool_missing_no_package_manager(self) -> None:
        # Arrange
        def which_side_effect(name: str) -> str | None:
            return None

        # Act
        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Unknown"),
        ):
            result = ensure_tool("gh", allow_install=True)

        # Assert
        assert result.available is False
        assert result.attempted is False
        assert "No supported package manager" in result.detail

    def test_tool_install_via_brew_success(self) -> None:
        # Arrange
        call_count = 0

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "gh":
                call_count += 1
                return "/usr/local/bin/gh" if call_count > 1 else None
            if name == "brew":
                return "/usr/local/bin/brew"
            return None

        # Act
        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Darwin"),
            patch("ai_engineering.installer.tools.subprocess.run"),
        ):
            result = ensure_tool("gh", allow_install=True)

        # Assert
        assert result.available is True
        assert result.attempted is True
        assert result.installed is True
        assert result.method == "brew"

    def test_tool_install_failure(self) -> None:
        # Arrange
        import subprocess

        def which_side_effect(name: str) -> str | None:
            if name == "brew":
                return "/usr/local/bin/brew"
            return None

        # Act
        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Darwin"),
            patch(
                "ai_engineering.installer.tools.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "brew"),
            ),
        ):
            result = ensure_tool("gh", allow_install=True)

        # Assert
        assert result.available is False
        assert result.attempted is True
        assert result.installed is False
        assert result.method == "brew"

    def test_auto_install_env_var(self) -> None:
        def which_side_effect(name: str) -> str | None:
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Unknown"),
            patch.dict("os.environ", {"AI_ENG_AUTO_INSTALL_TOOLS": "1"}),
        ):
            result = ensure_tool("gh")
        # Should attempt install (auto_install read from env), but no package manager
        assert result.available is False
        assert "No supported package manager" in result.detail

    def test_tool_install_via_apt_success(self) -> None:
        # Arrange
        call_count = 0

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "gh":
                call_count += 1
                return "/usr/bin/gh" if call_count > 1 else None
            if name == "apt-get":
                return "/usr/bin/apt-get"
            if name == "brew":
                return None
            return None

        # Act
        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Linux"),
            patch("ai_engineering.installer.tools.subprocess.run"),
        ):
            result = ensure_tool("gh", allow_install=True)

        # Assert
        assert result.available is True
        assert result.method == "apt"

    def test_tool_install_via_winget_success(self) -> None:
        # Arrange
        call_count = 0

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "gh":
                call_count += 1
                return "C:\\gh.exe" if call_count > 1 else None
            if name == "winget":
                return "C:\\winget.exe"
            if name in ("brew", "apt-get"):
                return None
            return None

        # Act
        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
            patch("ai_engineering.installer.tools.subprocess.run"),
        ):
            result = ensure_tool("gh", allow_install=True)

        # Assert
        assert result.available is True
        assert result.method == "winget"

    def test_winget_unknown_tool_no_package_manager(self) -> None:
        def which_side_effect(name: str) -> str | None:
            if name == "winget":
                return "C:\\winget.exe"
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
        ):
            result = ensure_tool("unknown-tool-xyz", allow_install=True)
        # winget_id not found for unknown tool, so no cmd
        assert result.available is False
        assert "No supported package manager" in result.detail


class TestToolInstallResult:
    """Tests for the ToolInstallResult dataclass."""

    def test_defaults(self) -> None:
        result = ToolInstallResult(tool="gh", available=True, attempted=False, installed=False)
        assert result.method == "none"
        assert result.detail == ""


class TestProviderRequiredTools:
    """Tests for provider_required_tools."""

    def test_github_returns_gh(self) -> None:
        assert provider_required_tools("github") == ["gh"]

    def test_azure_returns_az(self) -> None:
        assert provider_required_tools("azure-devops") == ["az"]
