"""Progress indicators for the ai-engineering CLI.

Provides Rich-based spinners and multi-step progress for long-running
commands. All output goes to stderr via ``get_console()``.

Design rules:
- ``transient=True`` — spinners disappear when done.
- Suppressed when ``is_json_mode()`` or non-TTY (CI, piped).
- Zero test impact: non-TTY = no output = no assertion changes.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from rich.status import Status

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import get_console


class StepTracker:
    """Multi-step progress tracker using a Rich Status spinner.

    Updates the spinner description on each ``step()`` call.
    """

    def __init__(self, total: int, status: Status | None) -> None:
        self._total = total
        self._current = 0
        self._status = status

    def step(self, description: str) -> None:
        """Advance to the next step and update the spinner message."""
        self._current += 1
        if self._status is not None:
            self._status.update(f"[{self._current}/{self._total}] {description}")


def _should_show_progress() -> bool:
    """Return True if progress indicators should be displayed."""
    if is_json_mode():
        return False
    console = get_console()
    return console.is_terminal


@contextmanager
def spinner(description: str) -> Generator[None, None, None]:
    """Context manager that shows a transient spinner for a single-step wait.

    Args:
        description: Message displayed alongside the spinner.

    Example::

        with spinner("Installing governance framework..."):
            result = install(root, ...)
    """
    if not _should_show_progress():
        yield
        return

    console = get_console()
    with console.status(description, spinner="dots"):
        yield


@contextmanager
def step_progress(total: int, description: str) -> Generator[StepTracker, None, None]:
    """Context manager that shows a multi-step progress spinner.

    Args:
        total: Total number of steps.
        description: Initial message displayed alongside the spinner.

    Example::

        with step_progress(5, "Running maintenance checks") as tracker:
            tracker.step("Generating framework report...")
            report = generate_report(root)
            tracker.step("Checking risk status...")
            risk = check_risk(root)
    """
    if not _should_show_progress():
        yield StepTracker(total, None)
        return

    console = get_console()
    with console.status(f"[0/{total}] {description}", spinner="dots") as status:
        yield StepTracker(total, status)
