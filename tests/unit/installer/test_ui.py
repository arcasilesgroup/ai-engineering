"""Unit tests for installer UI rendering."""

from __future__ import annotations

import pytest

from ai_engineering.installer.ui import StepStatus, render_step, render_summary

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# StepStatus rendering
# ---------------------------------------------------------------------------


class TestStepStatus:
    def test_render_ok(self, capsys) -> None:
        """OK status renders without error."""
        render_step(StepStatus(1, 6, "Test", "Testing...", "ok", "3 files"))
        # No assertion on exact output -- just verify no crash

    def test_render_warn(self, capsys) -> None:
        """Warning status renders without error."""
        render_step(StepStatus(2, 6, "Test", "Testing...", "warn", "1 issue"))

    def test_render_fail(self, capsys) -> None:
        """Fail status renders without error."""
        render_step(StepStatus(3, 6, "Test", "Testing...", "fail", "error"))


# ---------------------------------------------------------------------------
# render_summary
# ---------------------------------------------------------------------------


class TestRenderSummary:
    def test_summary_renders(self, capsys) -> None:
        """Summary renders without error."""
        render_summary(
            files_created=42,
            hooks_installed=3,
            warnings=["tool missing"],
            pending_setup=[("ai-eng setup github", "Auth not configured")],
            next_steps=[
                ("ai-eng doctor", "Verify health"),
                ("/ai-brainstorm", "First spec"),
            ],
        )
