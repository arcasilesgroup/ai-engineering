"""Unit tests for installer phases."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
    PhaseResult,
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

    def test_plan_install_creates_team_seed_actions(self, tmp_path: Path) -> None:
        """INSTALL mode produces create actions for team seed files."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path, mode=InstallMode.INSTALL)
        plan = phase.plan(ctx)
        team_actions = [a for a in plan.actions if "contexts/team/" in a.destination]
        assert len(team_actions) == 2
        for a in team_actions:
            assert a.action_type == "create"
            assert a.rationale == "team seed file"

    def test_plan_install_skips_team_if_exists(self, tmp_path: Path) -> None:
        """INSTALL mode with existing team files produces skip actions."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        # Pre-create team files
        team_dir = tmp_path / ".ai-engineering" / "contexts" / "team"
        team_dir.mkdir(parents=True)
        (team_dir / "README.md").write_text("custom")
        (team_dir / "lessons.md").write_text("custom")

        phase = GovernancePhase()
        ctx = _ctx(tmp_path, mode=InstallMode.INSTALL)
        plan = phase.plan(ctx)
        team_actions = [a for a in plan.actions if "contexts/team/" in a.destination]
        assert len(team_actions) == 2
        for a in team_actions:
            assert a.action_type == "skip"
            assert a.rationale == "team seed already exists"

    def test_plan_fresh_overwrites_team_seeds(self, tmp_path: Path) -> None:
        """FRESH mode produces overwrite actions for team files."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path, mode=InstallMode.FRESH)
        plan = phase.plan(ctx)
        team_actions = [a for a in plan.actions if "contexts/team/" in a.destination]
        assert len(team_actions) == 2
        for a in team_actions:
            assert a.action_type == "overwrite"

    def test_plan_repair_skips_team(self, tmp_path: Path) -> None:
        """REPAIR mode skips team files."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path, mode=InstallMode.REPAIR)
        plan = phase.plan(ctx)
        team_actions = [a for a in plan.actions if "contexts/team/" in a.destination]
        assert len(team_actions) == 2
        for a in team_actions:
            assert a.action_type == "skip"
            assert a.rationale == "team-owned file"

    def test_plan_includes_specs_directory_files(self, tmp_path: Path) -> None:
        """Plan includes specs/spec.md and specs/plan.md as create actions."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path, mode=InstallMode.INSTALL)
        plan = phase.plan(ctx)
        specs_actions = [a for a in plan.actions if "specs/" in a.destination]
        specs_dests = sorted(a.destination for a in specs_actions)
        assert ".ai-engineering/specs/plan.md" in specs_dests
        assert ".ai-engineering/specs/spec.md" in specs_dests
        for a in specs_actions:
            assert a.action_type == "create"

    def test_execute_creates_team_and_specs(self, tmp_path: Path) -> None:
        """Execute in INSTALL mode creates team seed files and specs placeholders."""
        from ai_engineering.installer.phases.governance import GovernancePhase

        phase = GovernancePhase()
        ctx = _ctx(tmp_path, mode=InstallMode.INSTALL)
        plan = phase.plan(ctx)
        phase.execute(plan, ctx)

        ai_dir = tmp_path / ".ai-engineering"
        # Team seed files
        assert (ai_dir / "contexts" / "team" / "README.md").is_file()
        assert (ai_dir / "contexts" / "team" / "lessons.md").is_file()
        # Specs placeholders
        assert (ai_dir / "specs" / "spec.md").is_file()
        assert (ai_dir / "specs" / "plan.md").is_file()


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

    @pytest.mark.skipif(
        __import__("os").name == "nt",
        reason="Unix permission semantics not available on Windows",
    )
    def test_execute_applies_executable_permissions(self, tmp_path: Path) -> None:
        """Execute sets +x on .sh and .py hook scripts but not _lib/*.py."""
        import stat
        from unittest.mock import patch

        from ai_engineering.installer.phases.hooks import HooksPhase

        # Build a fake hooks source tree with .sh, .py, and _lib/*.py files
        hooks_src = tmp_path / "template" / "scripts" / "hooks"
        hooks_src.mkdir(parents=True)
        (hooks_src / "run-gates.sh").write_text("#!/bin/bash\nexit 0")
        (hooks_src / "helper.py").write_text("#!/usr/bin/env python3\n")
        lib_dir = hooks_src / "_lib"
        lib_dir.mkdir()
        (lib_dir / "utils.py").write_text("# library module")

        # Strip executable bits from all files to simulate copy2 losing them
        for f in hooks_src.rglob("*"):
            if f.is_file():
                f.chmod(0o644)

        # Target project directory
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git" / "hooks").mkdir(parents=True)

        ctx = _ctx(project)

        # Patch template maps to point at our fake source tree
        fake_maps = type("M", (), {"common_tree_list": [("scripts/hooks", "scripts/hooks")]})()
        with (
            patch(
                "ai_engineering.installer.phases.hooks.get_project_template_root",
                return_value=tmp_path / "template",
            ),
            patch(
                "ai_engineering.installer.phases.hooks.resolve_template_maps",
                return_value=fake_maps,
            ),
            patch("ai_engineering.installer.phases.hooks.install_hooks") as mock_ih,
        ):
            mock_ih.return_value = type("R", (), {"installed": [], "skipped": []})()
            phase = HooksPhase()
            plan = phase.plan(ctx)
            phase._resolved_maps = fake_maps
            phase.execute(plan, ctx)

        # .sh and .py files in the hooks dir (not _lib) must be executable
        dest = project / "scripts" / "hooks"
        sh_file = dest / "run-gates.sh"
        py_file = dest / "helper.py"
        assert sh_file.stat().st_mode & stat.S_IXUSR, "run-gates.sh should be user-executable"
        assert sh_file.stat().st_mode & stat.S_IXGRP, "run-gates.sh should be group-executable"
        assert py_file.stat().st_mode & stat.S_IXUSR, "helper.py should be user-executable"
        assert py_file.stat().st_mode & stat.S_IXGRP, "helper.py should be group-executable"

        # _lib/*.py must NOT have executable bits added
        lib_file = dest / "_lib" / "utils.py"
        assert not (lib_file.stat().st_mode & stat.S_IXUSR), (
            "_lib/utils.py should NOT be user-executable"
        )


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
        assert any("install-state" in d for d in dests)

    def test_fresh_regenerates_state(self, tmp_path: Path) -> None:
        """FRESH mode regenerates install-state."""
        from ai_engineering.installer.phases.state import StatePhase

        phase = StatePhase()
        # Create existing state
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "install-state.json").write_text("{}")

        ctx = _ctx(tmp_path, mode=InstallMode.FRESH)
        plan = phase.plan(ctx)
        overwrite_actions = [a for a in plan.actions if a.action_type == "overwrite"]
        assert any("install-state" in a.destination for a in overwrite_actions)

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


class TestIdeConfigReconfigure:
    def test_reconfigure_with_manifest_generates_deletes(self, tmp_path: Path) -> None:
        """RECONFIGURE with existing state + manifest generates delete actions."""
        import yaml

        from ai_engineering.installer.phases.ide_config import IdeConfigPhase
        from ai_engineering.state.models import InstallState

        # Write a manifest.yml with old providers (claude_code + github_copilot)
        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True)
        manifest_data = {
            "schema_version": "2.0",
            "framework_version": "0.1.0",
            "name": "test",
            "providers": {"vcs": "github", "ides": ["claude_code", "github_copilot"], "stacks": []},
        }
        (ai_dir / "manifest.yml").write_text(yaml.dump(manifest_data))

        ctx = _ctx(tmp_path, mode=InstallMode.RECONFIGURE, providers=["claude_code"])
        ctx.existing_state = InstallState()

        phase = IdeConfigPhase()
        plan = phase.plan(ctx)
        delete_actions = [a for a in plan.actions if a.action_type == "delete"]
        assert len(delete_actions) > 0
        assert any("github_copilot" in a.rationale for a in delete_actions)

    def test_reconfigure_deletions_use_deleted_field(self, tmp_path: Path) -> None:
        """RECONFIGURE deletions go to PhaseResult.deleted, not created."""
        result = PhaseResult(phase_name="ide_config")
        result.deleted.append("removed/file.txt")
        assert "removed/file.txt" not in result.created
        assert "removed/file.txt" in result.deleted


class TestDetectPhaseMutation:
    def test_plan_does_not_mutate_context(self, tmp_path: Path) -> None:
        """DetectPhase.plan() does NOT mutate context.vcs_provider."""
        from unittest.mock import patch

        from ai_engineering.installer.phases.detect import DetectPhase

        ctx = _ctx(tmp_path)
        ctx.vcs_provider = "original"
        phase = DetectPhase()
        with patch(
            "ai_engineering.installer.phases.detect._detect_vcs",
            return_value="azure_devops",
        ):
            phase.plan(ctx)
        assert ctx.vcs_provider == "original"

    def test_execute_sets_vcs_from_plan(self, tmp_path: Path) -> None:
        """DetectPhase.execute() DOES set context.vcs_provider from plan."""
        from unittest.mock import patch

        from ai_engineering.installer.phases.detect import DetectPhase

        ctx = _ctx(tmp_path)
        phase = DetectPhase()
        with patch(
            "ai_engineering.installer.phases.detect._detect_vcs",
            return_value="azure_devops",
        ):
            plan = phase.plan(ctx)
        ctx.vcs_provider = "original"
        phase.execute(plan, ctx)
        assert ctx.vcs_provider == "azure_devops"


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
