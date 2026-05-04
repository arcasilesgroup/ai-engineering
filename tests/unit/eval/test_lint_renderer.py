"""spec-119 T-3.4 / T-3.7 — lint-as-prompt markdown renderer."""

from __future__ import annotations

import pytest

from ai_engineering.lint_violation_render import render_table, render_text

pytestmark = pytest.mark.eval


_GOOD = {
    "rule_id": "logger-structured-args",
    "severity": "error",
    "expected": "logger.info({event, ...data})",
    "actual": "console.log(`event=${event}`)",
    "fix_hint": "Replace console.log with logger.info passing a structured object",
    "file": "src/auth/login.ts",
    "line": 42,
}


class TestRenderText:
    def test_includes_all_required_fields(self):
        out = render_text(_GOOD)
        assert "[error]" in out
        assert "logger-structured-args" in out
        assert "src/auth/login.ts:42" in out
        assert "logger.info" in out
        assert "console.log" in out
        assert "fix:" in out

    def test_rejects_missing_required_field(self):
        bad = {**_GOOD}
        del bad["fix_hint"]
        with pytest.raises(ValueError, match="missing required"):
            render_text(bad)

    def test_rejects_unknown_severity(self):
        bad = {**_GOOD, "severity": "blocker"}
        with pytest.raises(ValueError, match="severity"):
            render_text(bad)


class TestRenderTable:
    def test_empty_list(self):
        assert "No lint violations" in render_table([])

    def test_single_row_has_header_and_data(self):
        table = render_table([_GOOD])
        # Header row + separator + 1 data row = 3 lines
        assert table.count("\n") == 2
        assert "Severity" in table
        assert "logger-structured-args" in table

    def test_pipes_in_content_are_escaped(self):
        env = {
            **_GOOD,
            "actual": "a | b | c",
        }
        table = render_table([env])
        # Pipes inside cell are escaped (so the row stays well-formed)
        assert "a \\| b \\| c" in table

    def test_newlines_in_content_are_flattened(self):
        env = {
            **_GOOD,
            "fix_hint": "First step\nSecond step",
        }
        table = render_table([env])
        assert "First step Second step" in table

    def test_missing_optional_location_renders_dash(self):
        env = {**_GOOD}
        del env["file"]
        del env["line"]
        table = render_table([env])
        # Location column carries '-' for missing optional fields
        assert "| - |" in table
