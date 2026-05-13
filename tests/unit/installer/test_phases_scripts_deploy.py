"""Tests for ScriptsPhase (spec-133 D-133-21).

Asserts the 9 root framework scripts are deployed into the consumer's
``.ai-engineering/scripts/`` tree on every install.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.phases import InstallContext, InstallMode
from ai_engineering.installer.phases.scripts import ROOT_SCRIPT_FILES, ScriptsPhase


@pytest.fixture
def ctx(tmp_path: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        surfaces=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
    )


def test_root_script_files_inventory_matches_spec_133() -> None:
    """spec-133 D-133-21: 9 root scripts must be deployed."""
    expected = {
        "branch_slug.py",
        "commit_compose.py",
        "doc_gate.py",
        "plan_tasks.py",
        "pr_body_compose.py",
        "regenerate-hooks-manifest.py",
        "runtime_rotate.py",
        "session_bootstrap.py",
        "spec_lifecycle.py",
    }
    assert set(ROOT_SCRIPT_FILES) == expected
    assert len(ROOT_SCRIPT_FILES) == 9


def test_scripts_phase_plan_emits_one_action_per_script(ctx: InstallContext) -> None:
    plan = ScriptsPhase().plan(ctx)
    destinations = {a.destination for a in plan.actions}
    assert destinations == {f".ai-engineering/scripts/{s}" for s in ROOT_SCRIPT_FILES}


def test_scripts_phase_execute_copies_all_scripts(ctx: InstallContext) -> None:
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    result = phase.execute(plan, ctx)
    target_root = ctx.target / ".ai-engineering" / "scripts"
    for script in ROOT_SCRIPT_FILES:
        assert (target_root / script).exists(), f"{script} not deployed"
    assert result.failed == []


def test_scripts_phase_idempotent_second_run_is_noop(ctx: InstallContext) -> None:
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    phase.execute(plan, ctx)
    # second run
    plan2 = phase.plan(ctx)
    result2 = phase.execute(plan2, ctx)
    # everything should have been skipped (idempotent)
    assert result2.failed == []
    assert len(result2.skipped) == len(ROOT_SCRIPT_FILES)


def test_scripts_phase_verify_passes_when_all_present(ctx: InstallContext) -> None:
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    result = phase.execute(plan, ctx)
    verdict = phase.verify(result, ctx)
    assert verdict.passed
    assert verdict.errors == []


def test_scripts_phase_verify_fails_when_missing(ctx: InstallContext) -> None:
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    result = phase.execute(plan, ctx)
    # remove a deployed script
    (ctx.target / ".ai-engineering" / "scripts" / "session_bootstrap.py").unlink()
    verdict = phase.verify(result, ctx)
    assert not verdict.passed


def test_scripts_phase_deployed_files_executable(ctx: InstallContext) -> None:
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    phase.execute(plan, ctx)
    target_root = ctx.target / ".ai-engineering" / "scripts"
    for script in ROOT_SCRIPT_FILES:
        path = target_root / script
        st_mode = path.stat().st_mode
        # owner-execute bit must be set
        assert st_mode & 0o100, f"{script} not executable"


def test_scripts_phase_runs_in_phase_order() -> None:
    """ScriptsPhase must be after StatePhase and before ToolsPhase/HooksPhase."""
    from ai_engineering.installer.phases import (
        PHASE_HOOKS,
        PHASE_ORDER,
        PHASE_SCRIPTS,
        PHASE_STATE,
        PHASE_TOOLS,
    )

    order = list(PHASE_ORDER)
    assert order.index(PHASE_STATE) < order.index(PHASE_SCRIPTS)
    assert order.index(PHASE_SCRIPTS) < order.index(PHASE_TOOLS)
    assert order.index(PHASE_SCRIPTS) < order.index(PHASE_HOOKS)
