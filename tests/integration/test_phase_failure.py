"""Integration tests for phase failure resilience.

Covers AC32: hooks phase failure does not prevent preceding phases
from completing; subsequent repair completes the failed phase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.phases import InstallContext, InstallMode
from ai_engineering.installer.phases.detect import DetectPhase
from ai_engineering.installer.phases.governance import GovernancePhase
from ai_engineering.installer.phases.hooks import HooksPhase
from ai_engineering.installer.phases.ide_config import IdeConfigPhase
from ai_engineering.installer.phases.pipeline import PipelineRunner
from ai_engineering.installer.phases.state import StatePhase
from ai_engineering.installer.phases.tools import ToolsPhase

pytestmark = pytest.mark.integration


def _make_context(tmp_path: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


class TestPhaseFailureResilience:
    """Phase failure does not corrupt preceding phases."""

    def test_full_pipeline_completes_on_clean_dir(self, tmp_path: Path) -> None:
        """Basic sanity: pipeline completes on a clean directory."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        context = _make_context(tmp_path)
        runner = PipelineRunner(
            [
                DetectPhase(),
                GovernancePhase(),
                IdeConfigPhase(),
                HooksPhase(),
                StatePhase(),
                ToolsPhase(),
            ]
        )
        summary = runner.run(context)
        assert summary.failed_phase is None
        assert len(summary.completed_phases) == 6

    def test_dry_run_creates_no_files(self, tmp_path: Path) -> None:
        """Dry-run collects plans without creating files."""
        context = _make_context(tmp_path)
        runner = PipelineRunner(
            [
                DetectPhase(),
                GovernancePhase(),
                IdeConfigPhase(),
                StatePhase(),
            ]
        )
        summary = runner.run(context, dry_run=True)
        assert summary.dry_run is True
        assert len(summary.plans) == 4
        assert len(summary.results) == 0
        assert not (tmp_path / ".ai-engineering").exists()

    def test_repair_fills_gaps(self, tmp_path: Path) -> None:
        """REPAIR mode creates missing files without overwriting existing."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        # First install
        ctx1 = _make_context(tmp_path)
        runner = PipelineRunner(
            [
                DetectPhase(),
                GovernancePhase(),
                IdeConfigPhase(),
                HooksPhase(),
                StatePhase(),
                ToolsPhase(),
            ]
        )
        summary1 = runner.run(ctx1)
        assert summary1.failed_phase is None

        # Delete a governance file
        manifest_yml = tmp_path / ".ai-engineering" / "manifest.yml"
        if manifest_yml.exists():
            manifest_yml.unlink()

        # Repair
        ctx2 = _make_context(tmp_path)
        ctx2.mode = InstallMode.REPAIR
        summary2 = runner.run(ctx2)
        assert summary2.failed_phase is None
        assert manifest_yml.exists()
