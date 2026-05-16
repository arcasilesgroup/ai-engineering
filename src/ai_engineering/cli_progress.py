"""Progress indicators for the ai-engineering CLI.

Provides Rich-based spinners and multi-step progress for long-running
commands. All output goes to stderr via ``get_console()``.

Design rules:
- ``transient=True`` — spinners disappear when done.
- Suppressed when ``is_json_mode()`` or non-TTY (CI, piped).
- Zero test impact: non-TTY = no output = no assertion changes.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from rich.status import Status

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import get_console

# spec-124 D-124-03: substep updates are throttled so high-frequency
# events (e.g. fast-installing tools that finish in <10ms) do not
# saturate the terminal. 100ms = ~10 updates / second, matches Rich's
# native spinner refresh budget.
_SUBSTEP_THROTTLE_SECONDS = 0.1


class StepTracker:
    """Multi-step progress tracker using a Rich Status spinner.

    Updates the spinner description on each ``step()`` call. Sub-step
    updates via :meth:`substep` refine the description WITHOUT
    incrementing the ``[N/M]`` counter, so phases with internal granularity
    (per-tool / per-hook) can surface fine-grained progress under the
    same parent step.
    """

    def __init__(self, total: int, status: Status | None) -> None:
        self._total = total
        self._current = 0
        self._status = status
        # Last description emitted (so substep can fall back to the parent
        # step's label after the sub-task completes if desired).
        self._last_step_description = ""
        # Last wall-clock time (monotonic) at which the spinner was
        # updated by a substep. Used to throttle high-frequency updates
        # so the terminal isn't saturated.
        self._last_substep_emit: float = 0.0

    def step(self, description: str) -> None:
        """Advance to the next step and update the spinner message."""
        self._current += 1
        self._last_step_description = description
        # Reset the throttle timer so a fresh step can immediately surface
        # its first substep update without waiting for the throttle window.
        self._last_substep_emit = 0.0
        if self._status is not None:
            self._status.update(f"[{self._current}/{self._total}] {description}")

    def substep(self, description: str) -> None:
        """Refine the spinner message without advancing the ``[N/M]`` counter.

        Throttled to one update per :data:`_SUBSTEP_THROTTLE_SECONDS` so
        rapid-fire events (e.g. eight tools installing in a tight loop)
        do not saturate the terminal. The throttle is best-effort: the
        first call after :meth:`step` always emits, and intermediate calls
        within the throttle window are silently dropped.
        """
        if self._status is None:
            return
        now = time.monotonic()
        if (now - self._last_substep_emit) < _SUBSTEP_THROTTLE_SECONDS:
            return
        self._last_substep_emit = now
        prefix = f"[{self._current}/{self._total}]" if self._current else f"[0/{self._total}]"
        # Compose: "[N/M] <parent> -> <substep>" so the user can see both
        # the parent context and the active sub-task. When no parent step
        # has been emitted yet (substep before step), fall back to just
        # the [N/M] prefix + substep description.
        if self._last_step_description:
            self._status.update(f"{prefix} {self._last_step_description} -> {description}")
        else:
            self._status.update(f"{prefix} {description}")


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
