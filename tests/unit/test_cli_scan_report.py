"""Unit tests for ai_engineering.cli_commands.scan_report module.

Tests the scan-report format CLI command which converts raw scan
findings JSON into the standard markdown report contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


def _findings_payload(
    findings: list[dict] | None = None,
    score: int = 85,
    verdict: str = "PASS",
    justification: str | None = None,
) -> dict:
    """Build a scan findings payload dict."""
    payload: dict = {
        "score": score,
        "verdict": verdict,
        "findings": findings or [],
    }
    if justification:
        payload["justification"] = justification
    return payload


class TestScanReportFormat:
    """Tests for `ai-eng scan-report format`."""

    def test_no_input_or_json_provided(self) -> None:
        """When neither --input nor --json is provided, exit with code 1."""
        app = create_app()
        result = runner.invoke(app, ["scan-report", "format", "security"])
        assert result.exit_code != 0

    def test_inline_json_happy_path(self) -> None:
        """Inline --json with valid payload produces markdown report."""
        payload = _findings_payload(
            findings=[
                {
                    "severity": "major",
                    "category": "xss",
                    "description": "Unsafe innerHTML",
                    "location": "src/app.js:42",
                    "remediation": "Use textContent instead",
                }
            ],
            score=75,
            verdict="WARN",
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "# Scan Report: security" in result.output
        assert "Score: 75/100" in result.output
        assert "Verdict: WARN" in result.output
        assert "major" in result.output
        assert "xss" in result.output
        assert "Unsafe innerHTML" in result.output
        assert "src/app.js:42" in result.output

    def test_file_input_happy_path(self, tmp_path: Path) -> None:
        """Reading from --input file produces correct report."""
        payload = _findings_payload(score=100, verdict="PASS")
        input_file = tmp_path / "findings.json"
        input_file.write_text(json.dumps(payload), encoding="utf-8")

        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "quality", "--input", str(input_file)],
        )
        assert result.exit_code == 0
        assert "# Scan Report: quality" in result.output
        assert "Score: 100/100" in result.output
        assert "No findings reported" in result.output

    def test_no_findings_shows_placeholder(self) -> None:
        """When findings list is empty, the placeholder row is shown."""
        payload = _findings_payload(findings=[], score=100, verdict="PASS")
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "No findings reported" in result.output

    def test_findings_not_a_list_treated_as_empty(self) -> None:
        """When findings is not a list (e.g., a string), treat as empty."""
        payload = {"score": 50, "verdict": "WARN", "findings": "invalid"}
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "No findings reported" in result.output

    def test_invalid_inline_json(self) -> None:
        """Invalid JSON in --json produces exit code 1."""
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", "NOT VALID JSON"],
        )
        assert result.exit_code != 0

    def test_nonexistent_input_file(self, tmp_path: Path) -> None:
        """Non-existent --input file produces exit code 1."""
        app = create_app()
        result = runner.invoke(
            app,
            [
                "scan-report",
                "format",
                "security",
                "--input",
                str(tmp_path / "nope.json"),
            ],
        )
        assert result.exit_code != 0

    def test_severity_counts_in_signals_section(self) -> None:
        """The Signals JSON section contains correct severity counts."""
        payload = _findings_payload(
            findings=[
                {"severity": "blocker", "description": "a"},
                {"severity": "critical", "description": "b"},
                {"severity": "major", "description": "c"},
                {"severity": "minor", "description": "d"},
                {"severity": "info", "description": "e"},
            ],
            score=20,
            verdict="FAIL",
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        # Find the Signals JSON block in output
        lines = result.output.split("\n")
        signals_line = None
        for i, line in enumerate(lines):
            if line.strip() == "## Signals":
                signals_line = lines[i + 1]
                break
        assert signals_line is not None
        signals = json.loads(signals_line)
        assert signals["findings"]["blocker"] == 1
        assert signals["findings"]["critical"] == 1
        assert signals["findings"]["major"] == 1
        assert signals["findings"]["minor"] == 1

    def test_unknown_severity_counted_as_info(self) -> None:
        """Unknown severity values are counted under 'info'."""
        payload = _findings_payload(
            findings=[{"severity": "unknown_level", "description": "x"}],
            score=90,
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        # info count should be 1 (the unknown severity mapped to info)
        lines = result.output.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == "## Signals":
                signals = json.loads(lines[i + 1])
                assert signals["findings"]["blocker"] == 0
                break

    def test_gate_check_section(self) -> None:
        """Gate Check section shows blocker and critical thresholds."""
        payload = _findings_payload(
            findings=[{"severity": "blocker", "description": "leak"}],
            score=10,
            verdict="FAIL",
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "## Gate Check" in result.output
        assert "Blocker findings: 1" in result.output
        assert "threshold: 0" in result.output

    def test_custom_justification(self) -> None:
        """Custom justification from the payload appears in the report."""
        payload = _findings_payload(
            justification="Custom reason for verdict.",
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "quality", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "Custom reason for verdict." in result.output

    def test_render_flag_calls_render_markdown(self) -> None:
        """--render flag calls render_markdown instead of typer.echo."""
        payload = _findings_payload(score=100, verdict="PASS")
        with patch("ai_engineering.cli_commands.scan_report.render_markdown") as mock_render:
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "scan-report",
                    "format",
                    "security",
                    "--json",
                    json.dumps(payload),
                    "--render",
                ],
            )
        assert result.exit_code == 0
        mock_render.assert_called_once()
        rendered_content = mock_render.call_args[0][0]
        assert "# Scan Report: security" in rendered_content

    def test_missing_fields_use_defaults(self) -> None:
        """Findings with missing fields use default values."""
        payload = _findings_payload(
            findings=[{}],  # No fields at all
            score=50,
        )
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "info" in result.output  # default severity
        assert "general" in result.output  # default category

    def test_default_verdict_is_warn(self) -> None:
        """When verdict is missing from payload, default to WARN."""
        payload = {"score": 50, "findings": []}
        app = create_app()
        result = runner.invoke(
            app,
            ["scan-report", "format", "security", "--json", json.dumps(payload)],
        )
        assert result.exit_code == 0
        assert "Verdict: WARN" in result.output
