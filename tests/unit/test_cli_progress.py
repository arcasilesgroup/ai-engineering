"""Tests for the cli_progress module."""

from __future__ import annotations

from unittest.mock import patch

from ai_engineering.cli_progress import StepTracker, spinner, step_progress


class TestSpinner:
    """Tests for the spinner context manager."""

    def test_spinner_noop_in_json_mode(self) -> None:
        """Spinner does nothing in JSON mode."""
        with (
            patch("ai_engineering.cli_progress.is_json_mode", return_value=True),
            spinner("test"),
        ):
            pass  # Should not raise

    def test_spinner_noop_in_non_tty(self) -> None:
        """Spinner does nothing when not a terminal."""
        with (
            patch("ai_engineering.cli_progress.is_json_mode", return_value=False),
            patch("ai_engineering.cli_progress.get_console") as mock_console,
        ):
            mock_console.return_value.is_terminal = False
            with spinner("test"):
                pass  # Should not raise


class TestStepProgress:
    """Tests for the step_progress context manager."""

    def test_step_progress_noop_in_json_mode(self) -> None:
        """Step progress does nothing in JSON mode."""
        with (
            patch("ai_engineering.cli_progress.is_json_mode", return_value=True),
            step_progress(3, "test") as tracker,
        ):
            assert isinstance(tracker, StepTracker)
            tracker.step("step 1")
            tracker.step("step 2")
            tracker.step("step 3")

    def test_step_progress_noop_in_non_tty(self) -> None:
        """Step progress does nothing when not a terminal."""
        with (
            patch("ai_engineering.cli_progress.is_json_mode", return_value=False),
            patch("ai_engineering.cli_progress.get_console") as mock_console,
        ):
            mock_console.return_value.is_terminal = False
            with step_progress(2, "test") as tracker:
                tracker.step("a")
                tracker.step("b")


class TestStepTracker:
    """Tests for StepTracker."""

    def test_tracker_without_status_object(self) -> None:
        """Tracker with None status (suppressed mode) works silently."""
        tracker = StepTracker(3, None)
        tracker.step("one")
        tracker.step("two")
        tracker.step("three")
        # No assertion needed — just verify it doesn't raise
