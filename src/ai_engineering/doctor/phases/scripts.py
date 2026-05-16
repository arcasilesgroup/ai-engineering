"""Doctor phase: framework scripts deployment integrity (spec-133 D-133-21).

Checks:
- scripts-deployed: All 9 root framework scripts exist on disk under
  ``.ai-engineering/scripts/``.
- scripts-executable: The 2 hook-runtime scripts (regenerate-hooks-manifest,
  runtime_rotate) carry the executable bit so hook-installer machinery
  can call them.
- skill-scripts-lib: spec-128 Wave 4 — the ``skill_scripts_lib`` package and
  ``skill_scripts`` subdir under ``.ai-engineering/scripts/skills/`` are
  importable. Without them ``session_bootstrap.py``, ``commit_compose.py``,
  ``pr_body_compose.py``, and ``standup_render.py`` raise ModuleNotFoundError.
"""

from __future__ import annotations

import os
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.phases.scripts import ROOT_SCRIPT_FILES

_SCRIPTS_REL = ".ai-engineering/scripts"
_EXECUTABLE_SCRIPTS = frozenset({"regenerate-hooks-manifest.py", "runtime_rotate.py"})
_IS_WINDOWS = os.name == "nt"
_SKILLS_SUBTREE_REL = "skills"
_SKILL_SCRIPTS_LIB_MODULES: tuple[str, ...] = (
    "skill_scripts_lib/__init__.py",
    "skill_scripts_lib/git_activity.py",
    "skill_scripts_lib/markdown_render.py",
    "skill_scripts_lib/manifest_reader.py",
    "skill_scripts/__init__.py",
)


def _check_scripts_deployed(ctx: DoctorContext) -> CheckResult:
    root = Path(ctx.target) / _SCRIPTS_REL
    missing: list[str] = []
    for name in ROOT_SCRIPT_FILES:
        if not (root / name).exists():
            missing.append(name)
    if missing:
        return CheckResult(
            name="scripts-deployed",
            status=CheckStatus.FAIL,
            message=(
                f"{len(missing)} of {len(ROOT_SCRIPT_FILES)} framework scripts "
                f"missing under {_SCRIPTS_REL}/: {missing[:5]}"
                + (" ..." if len(missing) > 5 else "")
            ),
            fixable=True,
        )
    return CheckResult(
        name="scripts-deployed",
        status=CheckStatus.OK,
        message=f"All {len(ROOT_SCRIPT_FILES)} framework scripts present",
        fixable=False,
    )


def _check_scripts_executable(ctx: DoctorContext) -> CheckResult:
    # Windows does not track POSIX executable bits; scripts run via
    # python.exe + .py extension association, not the exec bit. Skip.
    if _IS_WINDOWS:
        return CheckResult(
            name="scripts-executable",
            status=CheckStatus.OK,
            message="Executable bit check skipped on Windows (not applicable)",
            fixable=False,
        )
    root = Path(ctx.target) / _SCRIPTS_REL
    non_exec: list[str] = []
    for name in _EXECUTABLE_SCRIPTS:
        path = root / name
        if path.exists() and not (path.stat().st_mode & 0o100):
            non_exec.append(name)
    if non_exec:
        return CheckResult(
            name="scripts-executable",
            status=CheckStatus.FAIL,
            message=f"Scripts missing executable bit: {non_exec}",
            fixable=True,
        )
    return CheckResult(
        name="scripts-executable",
        status=CheckStatus.OK,
        message="All hook-runtime scripts are executable",
        fixable=False,
    )


def _check_skill_scripts_lib(ctx: DoctorContext) -> CheckResult:
    """Verify spec-128 Wave 4 skill_scripts_lib subtree is on disk.

    Without these files ``session_bootstrap.py`` and three other scripts
    fail at import time with ``ModuleNotFoundError: skill_scripts_lib``.
    """
    skills_root = Path(ctx.target) / _SCRIPTS_REL / _SKILLS_SUBTREE_REL
    missing: list[str] = []
    for rel in _SKILL_SCRIPTS_LIB_MODULES:
        if not (skills_root / rel).exists():
            missing.append(rel)
    if missing:
        return CheckResult(
            name="skill-scripts-lib",
            status=CheckStatus.FAIL,
            message=(
                f"{len(missing)} skill_scripts_lib module(s) missing under "
                f"{_SCRIPTS_REL}/{_SKILLS_SUBTREE_REL}/: {missing[:5]}"
                + (" ..." if len(missing) > 5 else "")
                + " — run `ai-eng install --repair` to redeliver."
            ),
            fixable=True,
        )
    return CheckResult(
        name="skill-scripts-lib",
        status=CheckStatus.OK,
        message="skill_scripts_lib + skill_scripts subtree present",
        fixable=False,
    )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all script-deployment checks for the doctor pipeline."""
    return [
        _check_scripts_deployed(ctx),
        _check_scripts_executable(ctx),
        _check_skill_scripts_lib(ctx),
    ]


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Repair script deployment by re-running ScriptsPhase logic."""
    from ai_engineering.installer.phases import InstallContext, InstallMode
    from ai_engineering.installer.phases.scripts import ScriptsPhase

    target = Path(ctx.target)
    install_ctx = InstallContext(
        target=target,
        mode=InstallMode.REPAIR,
        surfaces=[],
        vcs_provider="github",
        stacks=[],
    )
    phase = ScriptsPhase()

    if dry_run:
        return [
            CheckResult(
                name="scripts-deployed",
                status=CheckStatus.OK,
                message="dry-run: would re-deploy 9 framework scripts",
                fixable=False,
            )
        ]

    plan = phase.plan(install_ctx)
    result = phase.execute(plan, install_ctx)
    verdict = phase.verify(result, install_ctx)
    status = CheckStatus.OK if verdict.passed else CheckStatus.FAIL
    return [
        CheckResult(
            name="scripts-deployed",
            status=status,
            message=(
                f"redeployed: created={len(result.created)} "
                f"skipped={len(result.skipped)} failed={len(result.failed)}"
            ),
            fixable=False,
        )
    ]
