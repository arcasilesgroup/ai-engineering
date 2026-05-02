"""Unit tests for PipelineRunner."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.phases import (
    PHASE_DETECT,
    PHASE_GOVERNANCE,
    PHASE_HOOKS,
    PHASE_IDE_CONFIG,
    PHASE_STATE,
    PHASE_TOOLS,
    InstallContext,
    InstallMode,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
    PlannedAction,
)
from ai_engineering.installer.phases.pipeline import PipelineRunner

# ---------------------------------------------------------------------------
# Fake phase
# ---------------------------------------------------------------------------


class _FakePhase:
    """A test phase that can be configured to pass or fail."""

    def __init__(
        self,
        name: str,
        *,
        fail_verify: bool = False,
        critical: bool = True,
    ) -> None:
        self._name = name
        self._fail_verify = fail_verify
        self._critical = critical

    @property
    def name(self) -> str:
        return self._name

    @property
    def critical(self) -> bool:
        return self._critical

    def plan(self, context: InstallContext) -> PhasePlan:
        return PhasePlan(
            phase_name=self._name,
            actions=[
                PlannedAction("create", "src.txt", f"{self._name}/out.txt", "test"),
            ],
        )

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        return PhaseResult(phase_name=self._name, created=[f"{self._name}/out.txt"])

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        return PhaseVerdict(
            phase_name=self._name,
            passed=not self._fail_verify,
            errors=["forced failure"] if self._fail_verify else [],
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _ctx(tmp_path):
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


# ---------------------------------------------------------------------------
# PipelineRunner
# ---------------------------------------------------------------------------


class TestPipelineRunner:
    def test_dry_run_plans_only(self, tmp_path) -> None:
        """Dry run calls plan() but not execute()."""
        runner = PipelineRunner([_FakePhase("a"), _FakePhase("b")])
        summary = runner.run(_ctx(tmp_path), dry_run=True)
        assert summary.dry_run
        assert len(summary.plans) == 2
        assert len(summary.results) == 0

    def test_full_run_all_phases(self, tmp_path) -> None:
        """Full run executes all phases."""
        runner = PipelineRunner([_FakePhase("a"), _FakePhase("b")])
        summary = runner.run(_ctx(tmp_path))
        assert not summary.dry_run
        assert len(summary.results) == 2
        assert len(summary.verdicts) == 2
        assert summary.completed_phases == ["a", "b"]
        assert summary.failed_phase is None

    def test_stops_on_failure(self, tmp_path) -> None:
        """Pipeline stops when a phase fails verification."""
        runner = PipelineRunner(
            [
                _FakePhase("a"),
                _FakePhase("b", fail_verify=True),
                _FakePhase("c"),
            ]
        )
        summary = runner.run(_ctx(tmp_path))
        assert summary.failed_phase == "b"
        assert "a" in summary.completed_phases
        assert "c" not in summary.completed_phases

    # spec-109 D-109-02 -----------------------------------------------------
    def test_continues_past_non_critical_failure(self, tmp_path) -> None:
        """A non-critical phase failure is recorded but does NOT stop the pipeline."""
        runner = PipelineRunner(
            [
                _FakePhase("a"),
                _FakePhase("b", fail_verify=True, critical=False),
                _FakePhase("c"),
            ]
        )
        summary = runner.run(_ctx(tmp_path))
        # Critical failed_phase stays None because b is non-critical.
        assert summary.failed_phase is None
        assert "b" in summary.non_critical_failures
        # All phases ran -- including c, which previously got skipped.
        assert summary.completed_phases == ["a", "b", "c"]
        assert len(summary.results) == 3
        assert len(summary.verdicts) == 3

    def test_critical_failure_still_breaks(self, tmp_path) -> None:
        """An explicitly-critical failure must still break the pipeline."""
        runner = PipelineRunner(
            [
                _FakePhase("a"),
                _FakePhase("b", fail_verify=True, critical=True),
                _FakePhase("c", critical=False),
            ]
        )
        summary = runner.run(_ctx(tmp_path))
        assert summary.failed_phase == "b"
        assert "c" not in summary.completed_phases
        assert summary.non_critical_failures == []

    def test_phase_without_critical_attribute_defaults_critical(self, tmp_path) -> None:
        """Legacy phases that omit ``critical`` keep the historical fail-stop behaviour."""

        class _LegacyPhase:
            def __init__(self, name: str, fail: bool) -> None:
                self._n = name
                self._fail = fail

            @property
            def name(self) -> str:
                return self._n

            def plan(self, context: InstallContext) -> PhasePlan:
                return PhasePlan(phase_name=self._n, actions=[])

            def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
                return PhaseResult(phase_name=self._n)

            def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
                return PhaseVerdict(phase_name=self._n, passed=not self._fail)

        runner = PipelineRunner(
            [
                _LegacyPhase("legacy_a", fail=False),
                _LegacyPhase("legacy_b", fail=True),
                _LegacyPhase("legacy_c", fail=False),
            ]
        )
        summary = runner.run(_ctx(tmp_path))
        # No `critical` attribute => default True => pipeline breaks at b.
        assert summary.failed_phase == "legacy_b"
        assert "legacy_c" not in summary.completed_phases

    def test_progress_callback_invoked_per_phase(self, tmp_path) -> None:
        """spec-109 D-109-07: pipeline forwards phase-progress events."""
        events: list[str] = []
        runner = PipelineRunner(
            [_FakePhase("a"), _FakePhase("b"), _FakePhase("c")],
            progress_callback=lambda msg: events.append(msg),
        )
        runner.run(_ctx(tmp_path))
        assert events == ["[1/3] a", "[2/3] b", "[3/3] c"]

    def test_progress_callback_failure_does_not_break_pipeline(self, tmp_path) -> None:
        """A raising callback must NEVER bring down the pipeline (fail-open UI)."""

        def _broken_cb(_msg: str) -> None:
            raise RuntimeError("ui broke")

        runner = PipelineRunner(
            [_FakePhase("a"), _FakePhase("b")],
            progress_callback=_broken_cb,
        )
        summary = runner.run(_ctx(tmp_path))
        assert summary.completed_phases == ["a", "b"]

    def test_runner_uses_reconciler_lifecycle(self, tmp_path, monkeypatch) -> None:
        """Install phases are routed through the shared reconcile lifecycle."""
        calls: list[tuple[str, bool]] = []

        from ai_engineering.installer.phases import pipeline as pipeline_module

        real_reconciler = pipeline_module.ResourceReconciler

        class _TrackingReconciler(real_reconciler):
            def run(self, adapter, context, *, preview: bool = False):
                calls.append((adapter.name, preview))
                return super().run(adapter, context, preview=preview)

        monkeypatch.setattr(pipeline_module, "ResourceReconciler", _TrackingReconciler)

        runner = PipelineRunner([_FakePhase("a"), _FakePhase("b")])
        runner.run(_ctx(tmp_path))

        assert calls == [("a", False), ("b", False)]


# ---------------------------------------------------------------------------
# PhasePlan security
# ---------------------------------------------------------------------------


class TestPhasePlanSecurity:
    def test_rejects_absolute_path(self) -> None:
        """Absolute paths in destinations are rejected."""
        with pytest.raises(ValueError, match="Absolute destination path rejected"):
            PhasePlan(
                phase_name="test",
                actions=[
                    PlannedAction("create", "src", "/etc/passwd", "exploit"),
                ],
            )

    def test_rejects_path_traversal(self) -> None:
        """Path traversal in destinations is rejected."""
        with pytest.raises(ValueError, match="Path traversal rejected"):
            PhasePlan(
                phase_name="test",
                actions=[
                    PlannedAction("create", "src", "../../../etc/passwd", "exploit"),
                ],
            )

    def test_serialization_roundtrip(self) -> None:
        """PhasePlan round-trips through dict serialization."""
        plan = PhasePlan(
            phase_name="test",
            actions=[
                PlannedAction("create", "a.txt", "b.txt", "copy"),
                PlannedAction("skip", "", "c.txt", "exists"),
            ],
        )
        restored = PhasePlan.from_dict(plan.to_dict())
        assert restored.phase_name == plan.phase_name
        assert len(restored.actions) == len(plan.actions)
        assert restored.actions[0].destination == "b.txt"

    def test_rejects_source_traversal(self) -> None:
        """Source path traversal is rejected."""
        with pytest.raises(ValueError, match="Source path traversal rejected"):
            PlannedAction("create", "../../../etc/passwd", "out.txt", "exploit")

    def test_rejects_absolute_source(self) -> None:
        """Absolute source paths are rejected."""
        with pytest.raises(ValueError, match="Absolute source path rejected"):
            PlannedAction("create", "/etc/passwd", "out.txt", "exploit")

    def test_allows_empty_source(self) -> None:
        """Empty source is allowed for informational actions."""
        action = PlannedAction("skip", "", "info.txt", "informational")
        assert action.source == ""


# ---------------------------------------------------------------------------
# PhaseResult
# ---------------------------------------------------------------------------


class TestPhaseResult:
    def test_deleted_field_defaults_empty(self) -> None:
        """PhaseResult.deleted defaults to empty list."""
        result = PhaseResult(phase_name="test")
        assert result.deleted == []

    def test_deleted_field_usable(self) -> None:
        """PhaseResult.deleted can be populated."""
        result = PhaseResult(phase_name="test")
        result.deleted.append("removed/file.txt")
        assert result.deleted == ["removed/file.txt"]


# ---------------------------------------------------------------------------
# Phase name constants
# ---------------------------------------------------------------------------


class TestCopyTreeForMode:
    def test_fresh_produces_relative_paths(self, tmp_path: Path) -> None:
        """copy_tree_for_mode in FRESH mode produces relative paths."""
        from ai_engineering.installer.templates import copy_tree_for_mode

        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("a")
        dest = tmp_path / "project" / "out"
        target_root = tmp_path / "project"
        target_root.mkdir(parents=True)

        created: list[str] = []
        skipped: list[str] = []
        copy_tree_for_mode(src, dest, target_root, fresh=True, created=created, skipped=skipped)
        assert len(created) == 1
        assert not Path(created[0]).is_absolute()
        assert Path(created[0]) == Path("out/a.txt")

    def test_non_fresh_produces_relative_paths(self, tmp_path: Path) -> None:
        """copy_tree_for_mode in non-FRESH mode produces relative paths."""
        from ai_engineering.installer.templates import copy_tree_for_mode

        src = tmp_path / "src"
        src.mkdir()
        (src / "b.txt").write_text("b")
        dest = tmp_path / "project" / "out"
        target_root = tmp_path / "project"
        target_root.mkdir(parents=True)

        created: list[str] = []
        skipped: list[str] = []
        copy_tree_for_mode(src, dest, target_root, fresh=False, created=created, skipped=skipped)
        assert len(created) == 1
        assert not Path(created[0]).is_absolute()


class TestPhaseConstants:
    def test_constants_importable(self) -> None:
        """Phase name constants are importable from phases package."""
        assert PHASE_DETECT == "detect"
        assert PHASE_GOVERNANCE == "governance"
        assert PHASE_IDE_CONFIG == "ide_config"
        assert PHASE_HOOKS == "hooks"
        assert PHASE_STATE == "state"
        assert PHASE_TOOLS == "tools"
