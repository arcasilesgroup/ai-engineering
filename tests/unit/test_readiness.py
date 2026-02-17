"""Tests for ai_engineering.detector.readiness — tool readiness detection.

Covers:
- ToolInfo and ReadinessReport dataclasses.
- check_tool: available and unavailable tools.
- check_all_tools: full readiness scan.
- remediate_missing_tools: install logic with mocking.
- _get_version: version string parsing.
- _try_install: uv and pip fallback paths.
"""

from __future__ import annotations

from unittest.mock import patch

from ai_engineering.detector.readiness import (
    ReadinessReport,
    ToolInfo,
    _get_version,
    _try_install,
    check_all_tools,
    check_tool,
    remediate_missing_tools,
)

# ── ToolInfo ───────────────────────────────────────────────────────────


class TestToolInfo:
    """Tests for ToolInfo dataclass."""

    def test_available_tool(self) -> None:
        info = ToolInfo(name="ruff", available=True, version="0.4.0", path="/usr/bin/ruff")
        assert info.available is True
        assert info.version == "0.4.0"

    def test_unavailable_tool(self) -> None:
        info = ToolInfo(name="gitleaks", available=False)
        assert info.available is False
        assert info.version is None
        assert info.path is None


# ── ReadinessReport ────────────────────────────────────────────────────


class TestReadinessReport:
    """Tests for ReadinessReport dataclass."""

    def test_all_ready_when_required_available(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=True),
                ToolInfo(name="ty", available=True),
                ToolInfo(name="gh", available=False),  # optional
            ]
        )
        assert report.all_ready is True

    def test_not_ready_when_required_missing(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
                ToolInfo(name="ty", available=True),
            ]
        )
        assert report.all_ready is False

    def test_missing_returns_required_only(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
                ToolInfo(name="gh", available=False),  # optional
                ToolInfo(name="az", available=False),  # optional
            ]
        )
        assert report.missing == ["ruff"]

    def test_empty_report_is_ready(self) -> None:
        report = ReadinessReport()
        assert report.all_ready is True
        assert report.missing == []


# ── check_tool ─────────────────────────────────────────────────────────


class TestCheckTool:
    """Tests for check_tool function."""

    def test_available_tool_returns_info(self) -> None:
        # 'git' should always be available in test environments
        info = check_tool("git")
        assert info.name == "git"
        # git may or may not be in _VERSION_FLAGS, so just check structure
        assert isinstance(info.available, bool)

    def test_unavailable_tool_returns_false(self) -> None:
        info = check_tool("nonexistent-tool-xyz-12345")
        assert info.available is False
        assert info.path is None

    def test_python_available(self) -> None:
        info = check_tool("python3")
        # python3 should be available
        assert info.name == "python3"


# ── check_all_tools ───────────────────────────────────────────────────


class TestCheckAllTools:
    """Tests for check_all_tools function."""

    def test_returns_readiness_report(self) -> None:
        report = check_all_tools()
        assert isinstance(report, ReadinessReport)
        assert len(report.tools) == 8  # uv, ruff, ty, gitleaks, semgrep, pip-audit, gh, az

    def test_tool_names_match_expected(self) -> None:
        report = check_all_tools()
        names = {t.name for t in report.tools}
        expected = {"uv", "ruff", "ty", "gitleaks", "semgrep", "pip-audit", "gh", "az"}
        assert names == expected


# ── _get_version ───────────────────────────────────────────────────────


class TestGetVersion:
    """Tests for _get_version helper."""

    def test_unknown_tool_returns_none(self) -> None:
        version = _get_version("nonexistent-tool-xyz")
        assert version is None

    def test_known_tool_returns_string_or_none(self) -> None:
        # ruff may or may not be installed
        version = _get_version("ruff")
        if version is not None:
            assert isinstance(version, str)
            assert len(version) > 0


# ── remediate_missing_tools ────────────────────────────────────────────


class TestRemediateMissingTools:
    """Tests for remediate_missing_tools function."""

    def test_no_missing_returns_empty(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=True),
                ToolInfo(name="ty", available=True),
            ]
        )
        result = remediate_missing_tools(report)
        assert result == []

    def test_system_tools_not_attempted(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="gitleaks", available=False),
                ToolInfo(name="semgrep", available=False),
            ]
        )
        result = remediate_missing_tools(report)
        assert result == []  # System tools not in _INSTALLABLE_TOOLS

    def test_installable_tool_attempted(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
            ]
        )
        with patch(
            "ai_engineering.detector.readiness._try_install",
            return_value=True,
        ) as mock_install:
            result = remediate_missing_tools(report)
        assert "ruff" in result
        mock_install.assert_called_once_with("ruff")

    def test_failed_install_not_in_result(self) -> None:
        report = ReadinessReport(
            tools=[
                ToolInfo(name="ruff", available=False),
            ]
        )
        with patch(
            "ai_engineering.detector.readiness._try_install",
            return_value=False,
        ):
            result = remediate_missing_tools(report)
        assert result == []


# ── _try_install ───────────────────────────────────────────────────────


class TestTryInstall:
    """Tests for _try_install helper."""

    def test_uses_uv_when_available(self) -> None:
        with (
            patch("ai_engineering.detector.readiness.shutil.which", return_value="/usr/bin/uv"),
            patch("ai_engineering.detector.readiness.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = _try_install("ruff")
        assert result is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "uv"

    def test_falls_back_to_pip_when_uv_unavailable(self) -> None:
        def which_side_effect(name: str) -> str | None:
            return None  # uv not available

        with (
            patch("ai_engineering.detector.readiness.shutil.which", side_effect=which_side_effect),
            patch("ai_engineering.detector.readiness.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = _try_install("ruff")
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pip"

    def test_returns_false_on_all_failures(self) -> None:
        import subprocess as sp

        with (
            patch(
                "ai_engineering.detector.readiness.shutil.which",
                return_value=None,
            ),
            patch(
                "ai_engineering.detector.readiness.subprocess.run",
                side_effect=sp.CalledProcessError(1, "pip"),
            ),
        ):
            result = _try_install("ruff")
        assert result is False
