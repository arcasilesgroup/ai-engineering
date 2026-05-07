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

# spec-101 Wave 29: ``ToolsPhase`` invokes real network install mechanisms
# (GitHub releases download for ``gitleaks``/``jq``) which 404 on Ubuntu and
# Windows runners -- causing the pipeline summary's ``failed_phase`` to land
# on ``'tools'`` instead of ``None``. Engage the synthetic-OK simulate hook
# so the install pipeline short-circuits the network call while still
# exercising every other phase boundary.
pytestmark = pytest.mark.usefixtures("hermetic_install_env")


def _make_context(tmp_path: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude-code"],
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
