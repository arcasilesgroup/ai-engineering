"""Unit tests for PipelineRunner."""

from __future__ import annotations

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

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fake phase
# ---------------------------------------------------------------------------


class _FakePhase:
    """A test phase that can be configured to pass or fail."""

    def __init__(self, name: str, *, fail_verify: bool = False) -> None:
        self._name = name
        self._fail_verify = fail_verify

    @property
    def name(self) -> str:
        return self._name

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


class TestPhaseConstants:
    def test_constants_importable(self) -> None:
        """Phase name constants are importable from phases package."""
        assert PHASE_DETECT == "detect"
        assert PHASE_GOVERNANCE == "governance"
        assert PHASE_IDE_CONFIG == "ide_config"
        assert PHASE_HOOKS == "hooks"
        assert PHASE_STATE == "state"
        assert PHASE_TOOLS == "tools"
