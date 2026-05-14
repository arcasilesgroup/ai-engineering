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
    expected = {f".ai-engineering/scripts/{s}" for s in ROOT_SCRIPT_FILES}
    # spec-128 Wave 4: skills/ subtree is one additional action.
    expected.add(".ai-engineering/scripts/skills/")
    assert destinations == expected


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
    # everything should have been skipped (idempotent) — 9 root scripts +
    # 8 skills/ subtree files (skill_scripts_lib has 4, skill_scripts has 4).
    assert result2.failed == []
    assert len(result2.skipped) >= len(ROOT_SCRIPT_FILES)


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


# ---------------------------------------------------------------------------
# spec-128 Wave 4: skill_scripts_lib + skill_scripts subtree deployment
# ---------------------------------------------------------------------------

_LIB_FILES = (
    "skill_scripts_lib/__init__.py",
    "skill_scripts_lib/git_activity.py",
    "skill_scripts_lib/markdown_render.py",
    "skill_scripts_lib/manifest_reader.py",
)
_SKILL_FILES = (
    "skill_scripts/__init__.py",
    "skill_scripts/cleanup_run.py",
    "skill_scripts/resolve_classify.py",
    "skill_scripts/standup_render.py",
)


def test_scripts_phase_deploys_skill_scripts_lib_directory(ctx: InstallContext) -> None:
    """spec-128 Wave 4: skill_scripts_lib must land under skills/ so session_bootstrap imports resolve."""
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    phase.execute(plan, ctx)
    skills_root = ctx.target / ".ai-engineering" / "scripts" / "skills"
    for rel in _LIB_FILES:
        assert (skills_root / rel).exists(), f"{rel} not deployed"


def test_scripts_phase_deploys_skill_scripts_directory(ctx: InstallContext) -> None:
    """spec-128 Wave 4: skill_scripts subdir (cleanup_run, resolve_classify, standup_render) must land."""
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    phase.execute(plan, ctx)
    skills_root = ctx.target / ".ai-engineering" / "scripts" / "skills"
    for rel in _SKILL_FILES:
        assert (skills_root / rel).exists(), f"{rel} not deployed"


def test_scripts_phase_skips_pycache_in_skills_tree(ctx: InstallContext) -> None:
    """copy_template_tree must filter __pycache__; no .pyc files should land in target."""
    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    phase.execute(plan, ctx)
    skills_root = ctx.target / ".ai-engineering" / "scripts" / "skills"
    pyc_files = list(skills_root.rglob("*.pyc"))
    pycache_dirs = [p for p in skills_root.rglob("__pycache__") if p.is_dir()]
    assert pyc_files == [], f"Unexpected .pyc files leaked into target: {pyc_files}"
    assert pycache_dirs == [], f"Unexpected __pycache__ dirs leaked into target: {pycache_dirs}"


def test_session_bootstrap_imports_succeed_post_install(ctx: InstallContext) -> None:
    """session_bootstrap.py's skill_scripts_lib imports must resolve after install.

    Reproduces the user-reported ModuleNotFoundError from broken installs:
    ``ModuleNotFoundError: No module named 'skill_scripts_lib'``.
    """
    import subprocess
    import sys

    phase = ScriptsPhase()
    plan = phase.plan(ctx)
    phase.execute(plan, ctx)
    scripts_dir = ctx.target / ".ai-engineering" / "scripts"
    # Mirror session_bootstrap.py's sys.path injection (line 73-75).
    code = (
        "import sys, pathlib; "
        f"sys.path.insert(0, str(pathlib.Path({str(scripts_dir)!r}) / 'skills')); "
        "from skill_scripts_lib.markdown_render import parse_frontmatter; "
        "from skill_scripts_lib.git_activity import last_commit; "
        "print('IMPORT_OK')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"import failed: stderr={proc.stderr} stdout={proc.stdout}"
    assert "IMPORT_OK" in proc.stdout


def test_scripts_phase_repair_mode_redelivers_missing_skills_dir(
    tmp_path: Path,
) -> None:
    """REPAIR mode must redeliver skills/ subtree after a user deletes it."""
    install_ctx = InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        surfaces=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
    )
    phase = ScriptsPhase()
    phase.execute(phase.plan(install_ctx), install_ctx)
    skills_root = tmp_path / ".ai-engineering" / "scripts" / "skills"
    init_path = skills_root / "skill_scripts_lib" / "__init__.py"
    assert init_path.exists()

    # User accidentally deletes the subtree.
    init_path.unlink()
    (skills_root / "skill_scripts_lib" / "git_activity.py").unlink()

    # REPAIR mode redelivers.
    repair_ctx = InstallContext(
        target=tmp_path,
        mode=InstallMode.REPAIR,
        surfaces=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
    )
    repair_result = phase.execute(phase.plan(repair_ctx), repair_ctx)
    assert init_path.exists(), "REPAIR mode failed to redeliver skill_scripts_lib"
    assert repair_result.failed == []
