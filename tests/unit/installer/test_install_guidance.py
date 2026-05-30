"""Per-surface wire-up guidance aggregation + rendering (spec-156 D-156-15).

Surfaces with no machine-wide home file (cursor / github-copilot) under
``--global`` contribute a :class:`GuidanceSentinel` instead of a written file.
These tests pin the full chain: the pipeline aggregates (and dedupes) guidance
from any phase exposing ``.guidance``; ``_summary_to_install_result`` carries it
onto ``InstallResult``; and the CLI surfaces it in both the JSON envelope and
the human render so choosing those surfaces in global scope does something
visible.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.cli_commands import core
from ai_engineering.cli_output import set_json_mode
from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
)
from ai_engineering.installer.phases.pipeline import PipelineRunner, PipelineSummary
from ai_engineering.installer.scope import GuidanceSentinel
from ai_engineering.installer.service import InstallResult, _summary_to_install_result


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
    set_json_mode(False)
    yield
    set_json_mode(False)


class _GuidancePhase:
    """A phase that records guidance sentinels, like IdeConfigPhase under --global."""

    def __init__(self, sentinels: list[GuidanceSentinel]) -> None:
        self.guidance = list(sentinels)

    @property
    def name(self) -> str:
        return "ide_config"

    def plan(self, context: InstallContext) -> PhasePlan:
        return PhasePlan(phase_name=self.name, actions=[])

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        return PhaseResult(phase_name=self.name)

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        return PhaseVerdict(phase_name=self.name, passed=True)


def _context(tmp_path: Path) -> InstallContext:
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        surfaces=["cursor"],
        vcs_provider="github",
        stacks=["python"],
    )


def test_pipeline_aggregates_and_dedupes_guidance(tmp_path: Path) -> None:
    keep = GuidanceSentinel(surface="cursor", message="copy rules", steps=("a", "b"))
    dup = GuidanceSentinel(surface="cursor", message="DROPPED", steps=())
    runner = PipelineRunner([_GuidancePhase([keep, dup])])
    summary = runner.run(_context(tmp_path), dry_run=False)
    assert [s.surface for s in summary.guidance] == ["cursor"]
    assert summary.guidance[0].message == "copy rules"


def test_summary_to_install_result_transfers_guidance() -> None:
    sentinel = GuidanceSentinel(surface="github-copilot", message="wire it", steps=("x",))
    summary = PipelineSummary()
    summary.guidance = [sentinel]
    result = _summary_to_install_result(summary, InstallMode.INSTALL)
    assert result.guidance == [sentinel]


def test_install_json_envelope_includes_guidance(capsys: pytest.CaptureFixture[str]) -> None:
    from types import SimpleNamespace

    set_json_mode(True)
    result = InstallResult()
    result.guidance = [GuidanceSentinel(surface="cursor", message="m", steps=("s1", "s2"))]
    core._emit_install_success_json(
        Path("/tmp/proj"),
        result,
        resolved_vcs="github",
        active_surfaces=["cursor"],
        auto_remediation_report=SimpleNamespace(to_dict=lambda: {}),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["guidance"] == [
        {"surface": "cursor", "message": "m", "steps": ["s1", "s2"]}
    ]


def test_render_install_guidance_human(capsys: pytest.CaptureFixture[str]) -> None:
    core._render_install_guidance(
        [GuidanceSentinel(surface="cursor", message="Copy rules", steps=("step one", "step two"))]
    )
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "cursor: Copy rules" in combined
    assert "1. step one" in combined
    assert "2. step two" in combined


def test_render_install_guidance_empty_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    core._render_install_guidance([])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
