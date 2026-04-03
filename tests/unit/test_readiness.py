"""Unit tests for detector/readiness.py — tool readiness checks and remediation.

Covers:
- ToolInfo creation and defaults.
- ReadinessReport aggregation, all_ready, missing properties.
- check_tool() with mocked shutil.which and subprocess.
- check_all_tools() and check_tools_for_stacks() composition.
- remediate_missing_tools() with uv/pip fallback.
- check_operational_readiness() with mocked manifest.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_engineering.detector.readiness import (
    _OPTIONAL_TOOLS,
    _STACK_TOOLS,
    ReadinessReport,
    ToolInfo,
    check_all_tools,
    check_operational_readiness,
    check_tool,
    check_tools_for_stacks,
    remediate_missing_tools,
)

# ---------------------------------------------------------------------------
# ToolInfo
# ---------------------------------------------------------------------------


class TestToolInfo:
    """Tests for ToolInfo dataclass."""

    def test_creation_with_defaults(self) -> None:
        info = ToolInfo(name="ruff", available=True)
        assert info.name == "ruff"
        assert info.available is True
        assert info.version is None
        assert info.path is None

    def test_creation_with_all_fields(self) -> None:
        info = ToolInfo(name="ruff", available=True, version="0.5.0", path="/usr/bin/ruff")
        assert info.version == "0.5.0"
        assert info.path == "/usr/bin/ruff"


# ---------------------------------------------------------------------------
# ReadinessReport
# ---------------------------------------------------------------------------


class TestReadinessReport:
    """Tests for ReadinessReport properties."""

    def test_all_ready_with_all_available(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=True),
                ToolInfo(name="ty", available=True),
            ]
        )
        assert report.all_ready is True

    def test_all_ready_with_required_missing(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=True),
                ToolInfo(name="ty", available=False),
            ]
        )
        assert report.all_ready is False

    def test_all_ready_with_optional_missing(self) -> None:
        """Optional tools (gh, az) missing should not affect all_ready."""
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=True),
                ToolInfo(name="gh", available=False),
                ToolInfo(name="az", available=False),
            ]
        )
        assert report.all_ready is True
        # Verify gh and az are indeed optional
        assert "gh" in _OPTIONAL_TOOLS
        assert "az" in _OPTIONAL_TOOLS

    def test_missing_returns_only_required_names(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
                ToolInfo(name="ty", available=True),
                ToolInfo(name="gh", available=False),
            ]
        )
        missing = report.missing
        assert "ruff" in missing
        assert "gh" not in missing  # gh is optional
        assert "ty" not in missing  # ty is available

    def test_empty_report_all_ready(self) -> None:
        report = ReadinessReport()
        assert report.all_ready is True
        assert report.missing == []


# ---------------------------------------------------------------------------
# check_tool()
# ---------------------------------------------------------------------------


class TestCheckTool:
    """Tests for check_tool() with mocked externals."""

    @patch("ai_engineering.detector.readiness._get_version", return_value="0.5.0")
    @patch("ai_engineering.detector.readiness.shutil.which", return_value="/usr/bin/ruff")
    def test_tool_found(self, mock_which: MagicMock, mock_version: MagicMock) -> None:
        info = check_tool("ruff")
        assert info.available is True
        assert info.version == "0.5.0"
        assert info.path == "/usr/bin/ruff"
        mock_which.assert_called_once_with("ruff")

    @patch("ai_engineering.detector.readiness.shutil.which", return_value=None)
    def test_tool_not_found(self, mock_which: MagicMock) -> None:
        info = check_tool("ruff")
        assert info.available is False
        assert info.version is None
        assert info.path is None


# ---------------------------------------------------------------------------
# check_all_tools()
# ---------------------------------------------------------------------------


class TestCheckAllTools:
    """Tests for check_all_tools() composition."""

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_returns_report_with_all_standard_tools(self, mock_check: MagicMock) -> None:
        mock_check.return_value = ToolInfo(name="stub", available=True)
        report = check_all_tools()
        assert isinstance(report, ReadinessReport)
        # check_all_tools checks: uv, ruff, ty, gitleaks, semgrep, pip-audit, gh, az
        assert mock_check.call_count == 8
        called_names = [call.args[0] for call in mock_check.call_args_list]
        assert "uv" in called_names
        assert "ruff" in called_names
        assert "gh" in called_names
        assert "az" in called_names


# ---------------------------------------------------------------------------
# check_tools_for_stacks()
# ---------------------------------------------------------------------------


class TestCheckToolsForStacks:
    """Tests for check_tools_for_stacks() stack-specific checks."""

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_python_stack_includes_python_tools(self, mock_check: MagicMock) -> None:
        mock_check.return_value = ToolInfo(name="stub", available=True)
        check_tools_for_stacks(["python"])
        called_names = [call.args[0] for call in mock_check.call_args_list]
        # Should include common + vcs + python-specific
        for tool in _STACK_TOOLS["python"]:
            assert tool in called_names, f"Expected {tool} in checked tools"

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_dotnet_stack_includes_dotnet_tools(self, mock_check: MagicMock) -> None:
        mock_check.return_value = ToolInfo(name="stub", available=True)
        check_tools_for_stacks(["dotnet"])
        called_names = [call.args[0] for call in mock_check.call_args_list]
        assert "dotnet" in called_names

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_no_duplicate_tools(self, mock_check: MagicMock) -> None:
        """Each tool should only appear once even with overlapping stacks."""
        mock_check.side_effect = lambda name: ToolInfo(name=name, available=True)
        report = check_tools_for_stacks(["python"])
        tool_names = [t.name for t in report.tools]
        assert len(tool_names) == len(set(tool_names)), "Duplicate tools found in report"

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_always_includes_common_tools(self, mock_check: MagicMock) -> None:
        """Common security tools are always checked regardless of stack."""
        mock_check.side_effect = lambda name: ToolInfo(name=name, available=True)
        report = check_tools_for_stacks([])
        tool_names = [t.name for t in report.tools]
        assert "gitleaks" in tool_names
        assert "semgrep" in tool_names

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_scopes_vcs_tools_to_github_when_requested(self, mock_check: MagicMock) -> None:
        mock_check.side_effect = lambda name: ToolInfo(name=name, available=True)
        report = check_tools_for_stacks(["python"], vcs_provider="github")
        tool_names = [t.name for t in report.tools]
        assert "gh" in tool_names
        assert "az" not in tool_names

    @patch("ai_engineering.detector.readiness.check_tool")
    def test_scopes_vcs_tools_to_azure_when_requested(self, mock_check: MagicMock) -> None:
        mock_check.side_effect = lambda name: ToolInfo(name=name, available=True)
        report = check_tools_for_stacks(["python"], vcs_provider="azure_devops")
        tool_names = [t.name for t in report.tools]
        assert "az" in tool_names
        assert "gh" not in tool_names


# ---------------------------------------------------------------------------
# remediate_missing_tools()
# ---------------------------------------------------------------------------


class TestRemediateMissingTools:
    """Tests for remediate_missing_tools() with mocked installers."""

    @patch("ai_engineering.detector.readiness._try_install", return_value=True)
    def test_installs_missing_installable_tools(self, mock_install: MagicMock) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
                ToolInfo(name="ty", available=False),
            ]
        )
        installed = remediate_missing_tools(report)
        assert "ruff" in installed
        assert "ty" in installed

    @patch("ai_engineering.detector.readiness._try_install")
    def test_skips_non_installable_tools(self, mock_install: MagicMock) -> None:
        """System tools like gitleaks are not in _INSTALLABLE_TOOLS."""
        report = ReadinessReport(
            tools=[
                ToolInfo(name="gitleaks", available=False),
            ]
        )
        installed = remediate_missing_tools(report)
        assert installed == []
        mock_install.assert_not_called()

    def test_returns_empty_if_nothing_missing(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=True),
                ToolInfo(name="ty", available=True),
            ]
        )
        installed = remediate_missing_tools(report)
        assert installed == []

    @patch("ai_engineering.detector.readiness._try_install", return_value=False)
    def test_returns_empty_if_install_fails(self, mock_install: MagicMock) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
            ]
        )
        installed = remediate_missing_tools(report)
        assert installed == []


# ---------------------------------------------------------------------------
# check_operational_readiness()
# ---------------------------------------------------------------------------


class TestCheckOperationalReadiness:
    """Tests for check_operational_readiness() with install-state.json."""

    def test_reads_state_and_returns_status(self, tmp_path: Path) -> None:
        """When install-state.json exists and is valid, returns provider/cicd/branch checks."""
        from ai_engineering.state.models import InstallState, ToolEntry

        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        # Create install-state.json with gh authenticated
        state = InstallState(
            tooling={"gh": ToolEntry(installed=True, authenticated=True)},
        )
        from ai_engineering.state.service import save_install_state

        save_install_state(state_dir, state)

        # Create minimal manifest.yml (config reader needs it)
        ai_dir = tmp_path / ".ai-engineering"
        (ai_dir / "manifest.yml").write_text(
            "schema_version: '2.0'\nproviders:\n  vcs: github\n  stacks:\n    - python\n"
        )

        report = check_operational_readiness(tmp_path)
        assert isinstance(report, ReadinessReport)
        tool_names = [t.name for t in report.tools]
        assert "auth:github" in tool_names
        assert "branch-policy:applied" in tool_names

    def test_returns_empty_report_if_no_state(self, tmp_path: Path) -> None:
        """When install-state.json does not exist, returns empty report."""
        report = check_operational_readiness(tmp_path)
        assert report.tools == []
