"""Doctor phase: framework scripts deployment integrity (spec-133 D-133-21).

Checks:
- scripts-deployed: All 9 root framework scripts exist on disk under
  ``.ai-engineering/scripts/``.
- scripts-executable: The 2 hook-runtime scripts (regenerate-hooks-manifest,
  runtime_rotate) carry the executable bit so hook-installer machinery
  can call them.
"""

from __future__ import annotations

import os
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.installer.phases.scripts import ROOT_SCRIPT_FILES

_SCRIPTS_REL = ".ai-engineering/scripts"
_EXECUTABLE_SCRIPTS = frozenset({"regenerate-hooks-manifest.py", "runtime_rotate.py"})
_IS_WINDOWS = os.name == "nt"


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


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all script-deployment checks for the doctor pipeline."""
    return [
        _check_scripts_deployed(ctx),
        _check_scripts_executable(ctx),
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
