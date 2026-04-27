"""Tests for first-run BREAKING banner emission (spec-101 T-5.1/T-5.2).

The pipeline runner emits a one-shot BREAKING banner on its first execution
in a project. The banner highlights the spec-101 BREAKING contract:

- ``EXIT 80`` / ``EXIT 81`` are now reserved for missing required tools.
- ``python_env.mode`` defaults to ``uv-tool``.
- ``required_tools`` covers all 14 supported stacks.

Persistence semantics:

- The banner emits to **stderr** (so stdout pipelines stay clean).
- The runner sets ``InstallState.breaking_banner_seen = True`` once it has
  fired so subsequent invocations stay quiet (idempotency).
- A missing ``install-state.json`` (fresh install) is treated identically
  to ``breaking_banner_seen=False`` -- the banner fires.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.cli_output import set_json_mode
from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
)
from ai_engineering.installer.phases.pipeline import PipelineRunner
from ai_engineering.state.models import InstallState
from ai_engineering.state.service import load_install_state, save_install_state


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
    """Ensure module-global JSON mode is OFF before each test.

    Without this, parallel test runs (-n auto) can leave the global flag
    set to True from a sibling test that exercised JSON output, causing
    the banner-emission tests to silently skip and assert-fail.
    """
    set_json_mode(False)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


class _NoopPhase:
    """A no-op phase used to drive the pipeline without filesystem effects."""

    def __init__(self, name: str = "noop") -> None:
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


def _make_context(target: Path, *, existing_state: InstallState | None = None) -> InstallContext:
    """Build an InstallContext rooted at *target* with optional pre-loaded state."""
    return InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
        existing_state=existing_state,
    )


def _make_target(tmp_path: Path) -> Path:
    """Create a project skeleton with the state directory ready."""
    target = tmp_path / "project"
    state_dir = target / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return target


# ---------------------------------------------------------------------------
# T-5.1: BREAKING banner test cases
# ---------------------------------------------------------------------------


class TestBreakingBannerFirstRun:
    """Banner emits once on first run, then never again."""

    def test_emits_on_fresh_install_no_state_file(self, tmp_path, capsys) -> None:
        """When install-state.json does not exist, banner emits to stderr."""
        target = _make_target(tmp_path)
        # No state file written -- truly fresh install.
        runner = PipelineRunner([_NoopPhase("phase-a")])

        runner.run(_make_context(target), dry_run=False)

        captured = capsys.readouterr()
        assert "BREAKING" in captured.err, (
            "First-run banner must emit to stderr; "
            f"got stderr={captured.err!r} stdout={captured.out!r}"
        )
        # Key change keywords must appear so users notice the contract change.
        assert "EXIT 80" in captured.err
        assert "EXIT 81" in captured.err
        assert "python_env.mode" in captured.err
        assert "14 stacks" in captured.err

    def test_emits_when_flag_false(self, tmp_path, capsys) -> None:
        """State file exists with breaking_banner_seen=False -> banner fires."""
        target = _make_target(tmp_path)
        state_dir = target / ".ai-engineering" / "state"
        save_install_state(state_dir, InstallState(breaking_banner_seen=False))

        runner = PipelineRunner([_NoopPhase()])
        runner.run(_make_context(target), dry_run=False)

        captured = capsys.readouterr()
        assert "BREAKING" in captured.err

    def test_sets_flag_after_emit(self, tmp_path, capsys) -> None:
        """After the banner fires, breaking_banner_seen must be True on disk."""
        target = _make_target(tmp_path)
        state_dir = target / ".ai-engineering" / "state"
        save_install_state(state_dir, InstallState(breaking_banner_seen=False))

        runner = PipelineRunner([_NoopPhase()])
        runner.run(_make_context(target), dry_run=False)

        capsys.readouterr()  # drain captured output

        loaded = load_install_state(state_dir)
        assert loaded.breaking_banner_seen is True, (
            "After the banner fires, the flag must persist to install-state.json"
        )

    def test_does_not_emit_when_flag_true(self, tmp_path, capsys) -> None:
        """Idempotency: with breaking_banner_seen=True, banner never fires."""
        target = _make_target(tmp_path)
        state_dir = target / ".ai-engineering" / "state"
        save_install_state(state_dir, InstallState(breaking_banner_seen=True))

        runner = PipelineRunner([_NoopPhase()])
        runner.run(_make_context(target), dry_run=False)

        captured = capsys.readouterr()
        assert "BREAKING" not in captured.err
        assert "BREAKING" not in captured.out

    def test_banner_emits_exactly_once_across_two_runs(self, tmp_path, capsys) -> None:
        """Run twice in a row; banner must only appear during the first run."""
        target = _make_target(tmp_path)
        state_dir = target / ".ai-engineering" / "state"
        save_install_state(state_dir, InstallState(breaking_banner_seen=False))

        runner = PipelineRunner([_NoopPhase()])

        runner.run(_make_context(target), dry_run=False)
        first = capsys.readouterr()
        runner.run(_make_context(target), dry_run=False)
        second = capsys.readouterr()

        assert first.err.count("BREAKING") == 1, "Banner must emit exactly once on the first run."
        assert "BREAKING" not in second.err
        assert "BREAKING" not in second.out

    def test_dry_run_does_not_emit_or_persist(self, tmp_path, capsys) -> None:
        """Dry-run preview must neither show the banner nor persist the flag."""
        target = _make_target(tmp_path)
        state_dir = target / ".ai-engineering" / "state"
        save_install_state(state_dir, InstallState(breaking_banner_seen=False))

        runner = PipelineRunner([_NoopPhase()])
        runner.run(_make_context(target), dry_run=True)

        captured = capsys.readouterr()
        assert "BREAKING" not in captured.err
        assert "BREAKING" not in captured.out

        loaded = load_install_state(state_dir)
        assert loaded.breaking_banner_seen is False, "Dry-run must not flip the persistence flag."


class TestBreakingBannerStateFlag:
    """The InstallState model carries the persistence flag."""

    def test_install_state_has_breaking_banner_seen_field(self) -> None:
        """``breaking_banner_seen`` defaults to False on a fresh InstallState."""
        state = InstallState()
        assert hasattr(state, "breaking_banner_seen"), (
            "InstallState must expose breaking_banner_seen for spec-101 idempotency"
        )
        assert state.breaking_banner_seen is False

    def test_breaking_banner_seen_roundtrips_through_json(self) -> None:
        """Field survives JSON serialize -> deserialize."""
        state = InstallState(breaking_banner_seen=True)
        raw = state.model_dump_json()
        restored = InstallState.model_validate_json(raw)
        assert restored.breaking_banner_seen is True

    def test_legacy_install_state_dict_without_field_loads(self, tmp_path) -> None:
        """A pre-spec-101 install-state.json without the field still loads."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        # Modern shape minus breaking_banner_seen.
        legacy = {
            "schema_version": "2.0",
            "installed_at": "2026-04-01T00:00:00Z",
            "vcs_provider": None,
            "ai_providers": None,
            "tooling": {},
            "platforms": {},
            "branch_policy": {"applied": False, "mode": "api"},
            "operational_readiness": {"status": "pending", "pending_steps": []},
            "release": {"last_version": ""},
            "required_tools_state": {},
        }
        (state_dir / "install-state.json").write_text(json.dumps(legacy), encoding="utf-8")

        loaded = load_install_state(state_dir)
        assert loaded.breaking_banner_seen is False
