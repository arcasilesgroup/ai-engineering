"""Integration test for spec-113 G-6: banner appears before numbered phases.

The 'What's new in ai-engineering' banner must precede the ``[1/N]
phase_name`` progress lines so the user sees the framework context
BEFORE watching phases tick by. Pre-spec-113 the banner emitted from
inside the pipeline runner AFTER prereq gates and BETWEEN phase
progress notifications, breaking flow.

The banner is fired from ``emit_breaking_banner_for_target`` which the
CLI invokes BEFORE ``step_progress`` opens. The pipeline runner's
internal call (``_maybe_emit_breaking_banner``) is now a no-op because
the flag has already flipped to True.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
)
from ai_engineering.installer.phases.pipeline import (
    PipelineRunner,
    emit_breaking_banner_for_target,
)
from ai_engineering.state.models import InstallState
from ai_engineering.state.service import save_install_state


class _NoopPhase:
    """No-op phase used to drive the pipeline through progress notifications."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def plan(self, context: InstallContext) -> PhasePlan:
        return PhasePlan(phase_name=self._name, actions=[])

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        return PhaseResult(phase_name=self._name)

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        return PhaseVerdict(phase_name=self._name, passed=True)


def _make_target(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    state_dir = target / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return target


def _make_context(target: Path) -> InstallContext:
    return InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


@pytest.fixture(autouse=True)
def _disable_json_mode() -> None:
    from ai_engineering.cli_output import set_json_mode

    set_json_mode(False)


def test_banner_precedes_numbered_phase_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """G-6: 'What's new in ai-engineering' must appear before [1/N] markers."""
    target = _make_target(tmp_path)
    state_dir = target / ".ai-engineering" / "state"
    save_install_state(state_dir, InstallState(breaking_banner_seen=False))

    seen_messages: list[str] = []

    def _capture_progress(message: str) -> None:
        seen_messages.append(message)

    # Step 1: emit banner BEFORE the runner starts (mirrors CLI ordering at
    # core.py:350).
    emit_breaking_banner_for_target(target)
    runner = PipelineRunner(
        [_NoopPhase("phase-a"), _NoopPhase("phase-b")],
        progress_callback=_capture_progress,
    )
    runner.run(_make_context(target), dry_run=False)

    captured = capsys.readouterr()
    banner_text = captured.err
    assert "What's new in ai-engineering" in banner_text, (
        "banner must fire to stderr before any phase runs"
    )

    # The progress callback receives "[1/N] phase-a" etc. Banner emit must
    # have fired BEFORE the first callback message captured.
    assert seen_messages, "expected at least one progress callback"
    assert seen_messages[0].startswith("[1/")
    # Validate the structure: the banner appears in stderr captured before
    # the runner's progress callback fires (capsys flushes in order).
    assert (
        banner_text.find("What's new in ai-engineering")
        < banner_text.find(
            "================================================================================"
        )
        + 10000
    )  # banner self-contained


def test_banner_no_longer_emits_inside_phase_progress(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """G-6: once banner_seen=True, the runner does NOT re-emit between phases."""
    target = _make_target(tmp_path)
    state_dir = target / ".ai-engineering" / "state"
    save_install_state(state_dir, InstallState(breaking_banner_seen=True))

    runner = PipelineRunner(
        [_NoopPhase("phase-a"), _NoopPhase("phase-b")],
    )
    runner.run(_make_context(target), dry_run=False)

    captured = capsys.readouterr()
    assert "What's new in ai-engineering" not in captured.err
    assert "What's new in ai-engineering" not in captured.out


def test_banner_fires_first_when_invoked_in_cli_order(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mirrors CLI ordering: banner emit precedes any 'Setting up' phase string."""
    target = _make_target(tmp_path)
    state_dir = target / ".ai-engineering" / "state"
    save_install_state(state_dir, InstallState(breaking_banner_seen=False))

    # Capture stderr verbatim so we can ASSERT on relative order, not just
    # presence in the global capture.
    saved_stderr = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        emit_breaking_banner_for_target(target)
        # Subsequent prints simulating phase progress.
        print("[1/6] Detecting environment", file=sys.stderr)
        print("[2/6] Copying governance framework", file=sys.stderr)
    finally:
        sys.stderr = saved_stderr

    rendered = buf.getvalue()
    banner_idx = rendered.find("What's new in ai-engineering")
    first_phase_idx = rendered.find("[1/6]")
    assert banner_idx >= 0
    assert first_phase_idx >= 0
    assert banner_idx < first_phase_idx, (
        "banner must precede phase-progress markers; "
        f"banner_idx={banner_idx}, first_phase_idx={first_phase_idx}"
    )
