"""Unit tests for installer phases."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _ctx(
    tmp_path: Path,
    mode: InstallMode = InstallMode.INSTALL,
    providers: list[str] | None = None,
) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=mode,
        providers=providers or ["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


# ---------------------------------------------------------------------------
# GovernancePhase
# ---------------------------------------------------------------------------


class TestGovernancePhase:
    def test_plan_install_creates_actions(self, tmp_path: Path) -> None:
        """Plan in INSTALL mode produces create actions."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path)
        plan = phase.plan(ctx)
        assert plan.phase_name == "governance"
        create_actions = [a for a in plan.actions if a.action_type == "create"]
        assert len(create_actions) > 0

    def test_execute_creates_files(self, tmp_path: Path) -> None:
        """Execute in INSTALL mode creates governance files."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path)
        plan = phase.plan(ctx)
        result = phase.execute(plan, ctx)
        assert len(result.created) > 0
        # Verify files exist
        for f in result.created:
            assert (tmp_path / f).exists()

    def test_verify_passes(self, tmp_path: Path) -> None:
        """Verify after execute passes."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path)
        plan = phase.plan(ctx)
        result = phase.execute(plan, ctx)
        verdict = phase.verify(result, ctx)
        assert verdict.passed


# ---------------------------------------------------------------------------
# IdeConfigPhase
# ---------------------------------------------------------------------------


class TestIdeConfigPhase:
    def test_plan_claude_code(self, tmp_path: Path) -> None:
        """Plan with claude_code produces .claude tree."""
        from ai_engineering.installer.phases.ide_config import IdeConfigPhase

        phase = IdeConfigPhase()
        ctx = _ctx(tmp_path, providers=["claude_code"])
        plan = phase.plan(ctx)
        dests = [a.destination for a in plan.actions if a.action_type != "skip"]
        assert any("claude" in d.lower() or "CLAUDE" in d for d in dests)

    def test_plan_multi_provider(self, tmp_path: Path) -> None:
        """Plan with multiple providers includes all."""
        from ai_engineering.installer.phases.ide_config import IdeConfigPhase

        phase = IdeConfigPhase()
        ctx = _ctx(tmp_path, providers=["claude_code", "github_copilot"])
        plan = phase.plan(ctx)
        dests = " ".join(a.destination for a in plan.actions)
        assert "claude" in dests.lower() or "CLAUDE" in dests
        assert "github" in dests.lower() or "prompts" in dests.lower()

    def test_execute_creates_files(self, tmp_path: Path) -> None:
        """Execute creates IDE-specific files."""
        from ai_engineering.installer.phases.ide_config import IdeConfigPhase

        phase = IdeConfigPhase()
        ctx = _ctx(tmp_path, providers=["claude_code"])
        plan = phase.plan(ctx)
        result = phase.execute(plan, ctx)
        assert len(result.created) > 0


# ---------------------------------------------------------------------------
# HooksPhase
# ---------------------------------------------------------------------------


class TestHooksPhase:
    def test_plan_includes_hooks(self, tmp_path: Path) -> None:
        """Plan includes hook script copying."""
        from ai_engineering.installer.phases.hooks import HooksPhase

        phase = HooksPhase()
        ctx = _ctx(tmp_path)
        plan = phase.plan(ctx)
        assert any("hooks" in a.destination for a in plan.actions)


# ---------------------------------------------------------------------------
# StatePhase
# ---------------------------------------------------------------------------


class TestStatePhase:
    def test_plan_creates_state_files(self, tmp_path: Path) -> None:
        """Plan creates state files."""
        from ai_engineering.installer.phases.state import StatePhase

        phase = StatePhase()
        ctx = _ctx(tmp_path)
        plan = phase.plan(ctx)
        dests = [a.destination for a in plan.actions if a.action_type == "create"]
        assert any("install-manifest" in d for d in dests)

    def test_fresh_regenerates_manifest(self, tmp_path: Path) -> None:
        """FRESH mode regenerates install-manifest."""
        from ai_engineering.installer.phases.state import StatePhase

        phase = StatePhase()
        # Create existing manifest
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "install-manifest.json").write_text("{}")

        ctx = _ctx(tmp_path, mode=InstallMode.FRESH)
        plan = phase.plan(ctx)
        overwrite_actions = [a for a in plan.actions if a.action_type == "overwrite"]
        assert any("install-manifest" in a.destination for a in overwrite_actions)

    def test_never_overwrites_decision_store(self, tmp_path: Path) -> None:
        """Decision store is never overwritten."""
        from ai_engineering.installer.phases.state import StatePhase

        phase = StatePhase()
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "decision-store.json").write_text("{}")

        ctx = _ctx(tmp_path, mode=InstallMode.FRESH)
        plan = phase.plan(ctx)
        decision_actions = [a for a in plan.actions if "decision-store" in a.destination]
        for a in decision_actions:
            assert a.action_type == "skip"


# ---------------------------------------------------------------------------
# ToolsPhase
# ---------------------------------------------------------------------------


class TestToolsPhase:
    def test_always_passes_verify(self, tmp_path: Path) -> None:
        """Tools phase verify always passes (warnings only)."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        phase = ToolsPhase()
        ctx = _ctx(tmp_path)
        plan = phase.plan(ctx)
        result = phase.execute(plan, ctx)
        verdict = phase.verify(result, ctx)
        assert verdict.passed  # tools are warnings, not failures
