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

    def test_tool_install_via_brew_on_linux(self) -> None:
        """Brew works on Linux (Linuxbrew) — not just macOS."""
        call_count = 0

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "gitleaks":
                call_count += 1
                return "/home/linuxbrew/.linuxbrew/bin/gitleaks" if call_count > 1 else None
            if name == "brew":
                return "/home/linuxbrew/.linuxbrew/bin/brew"
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Linux"),
            patch("ai_engineering.installer.tools.subprocess.run"),
        ):
            result = ensure_tool("gitleaks", allow_install=True)

        assert result.available is True
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


class TestEnsureToolPipFallback:
    """Tests for pip/uv fallback when OS package manager has no mapping."""

    def test_pip_fallback_when_no_os_mapping(self) -> None:
        """ensure_tool falls back to pip for installable tools without OS mapping."""
        call_count = 0

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "ruff":
                call_count += 1
                return "/usr/local/bin/ruff" if call_count > 1 else None
            if name == "uv":
                return "/usr/local/bin/uv"
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
            patch("ai_engineering.installer.tools.subprocess.run"),
        ):
            result = ensure_tool("ruff", allow_install=True)

        assert result.available is True
        assert result.attempted is True
        assert result.method == "pip"

    def test_pip_fallback_uv_preferred_over_pip(self) -> None:
        """When uv is available, pip fallback uses 'uv pip install'."""
        import subprocess as sp

        call_count = 0
        commands_run: list[list[str]] = []

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "ruff":
                call_count += 1
                return "/usr/local/bin/ruff" if call_count > 1 else None
            if name == "uv":
                return "/usr/local/bin/uv"
            return None

        def run_side_effect(cmd: list[str], **kwargs: object) -> sp.CompletedProcess[str]:
            commands_run.append(list(cmd))
            return sp.CompletedProcess(cmd, 0)

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
            patch("ai_engineering.installer.tools.subprocess.run", side_effect=run_side_effect),
        ):
            result = ensure_tool("ruff", allow_install=True)

        assert result.available is True
        assert any("uv" in cmd for cmd in commands_run)

    def test_pip_fallback_uses_plain_pip_when_no_uv(self) -> None:
        """When uv is not available, falls back to plain pip."""
        call_count = 0

        def which_side_effect(name: str) -> str | None:
            nonlocal call_count
            if name == "ruff":
                call_count += 1
                return "/usr/local/bin/ruff" if call_count > 1 else None
            if name == "uv":
                return None
            if name == "pip":
                return "/usr/bin/pip"
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
            patch("ai_engineering.installer.tools.subprocess.run"),
        ):
            result = ensure_tool("ruff", allow_install=True)

        assert result.available is True
        assert result.method == "pip"

    def test_no_pip_fallback_for_system_tools(self) -> None:
        """System tools (gh, az) should not use pip fallback."""

        def which_side_effect(name: str) -> str | None:
            if name == "winget":
                return "C:\\winget.exe"
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
        ):
            # gh has a winget mapping but unknown-system-tool does not
            result = ensure_tool("unknown-system-tool", allow_install=True)

        assert result.available is False

    def test_pip_fallback_failure(self) -> None:
        """When pip fallback also fails, result is not available."""
        import subprocess as sp

        def which_side_effect(name: str) -> str | None:
            if name in ("uv", "pip"):
                return f"/usr/bin/{name}"
            return None

        with (
            patch("ai_engineering.installer.tools.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.installer.tools.platform.system", return_value="Windows"),
            patch(
                "ai_engineering.installer.tools.subprocess.run",
                side_effect=sp.CalledProcessError(1, "uv"),
            ),
        ):
            result = ensure_tool("ruff", allow_install=True)

        assert result.available is False
        assert result.attempted is True


class TestPhaseOrder:
    """Tests for PHASE_ORDER constraint: tools must run before hooks."""

    def test_tools_before_hooks(self) -> None:
        from ai_engineering.installer.phases import PHASE_HOOKS, PHASE_ORDER, PHASE_TOOLS

        tools_idx = PHASE_ORDER.index(PHASE_TOOLS)
        hooks_idx = PHASE_ORDER.index(PHASE_HOOKS)
        assert tools_idx < hooks_idx, (
            f"PHASE_TOOLS (index {tools_idx}) must come before "
            f"PHASE_HOOKS (index {hooks_idx}) to ensure gate tools "
            f"are installed before hooks activate gates"
        )

    def test_state_before_hooks(self) -> None:
        """Existing constraint: state must run before hooks for hash recording."""
        from ai_engineering.installer.phases import PHASE_HOOKS, PHASE_ORDER, PHASE_STATE

        state_idx = PHASE_ORDER.index(PHASE_STATE)
        hooks_idx = PHASE_ORDER.index(PHASE_HOOKS)
        assert state_idx < hooks_idx

    def test_state_before_tools(self) -> None:
        """State must also run before tools (tools may update install-state)."""
        from ai_engineering.installer.phases import PHASE_ORDER, PHASE_STATE, PHASE_TOOLS

        state_idx = PHASE_ORDER.index(PHASE_STATE)
        tools_idx = PHASE_ORDER.index(PHASE_TOOLS)
        assert state_idx < tools_idx


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

    def test_azure_devops_returns_az(self) -> None:
        assert provider_required_tools("azure_devops") == ["az"]

    def test_hyphenated_azure_alias_returns_az(self) -> None:
        assert provider_required_tools("azure-devops") == ["az"]

    def test_unknown_provider_returns_empty(self) -> None:
        assert provider_required_tools("bitbucket") == []
