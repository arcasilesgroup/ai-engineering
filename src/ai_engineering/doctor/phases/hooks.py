"""Doctor phase: git hook integrity validation.

Checks:
- hooks-integrity: All required hooks pass verify_hooks().
- hooks-scripts: scripts/hooks/ directory exists under .ai-engineering/.
"""

from __future__ import annotations

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.hooks.manager import install_hooks, verify_hooks


def _check_hooks_integrity(ctx: DoctorContext) -> CheckResult:
    """Verify that all required hooks are installed and have valid hashes."""
    try:
        status = verify_hooks(ctx.target)
    except FileNotFoundError:
        return CheckResult(
            name="hooks-integrity",
            status=CheckStatus.FAIL,
            message="git hooks directory not found; is this a git repository?",
            fixable=True,
        )

    failed_hooks = [name for name, ok in status.items() if not ok]

    if failed_hooks:
        return CheckResult(
            name="hooks-integrity",
            status=CheckStatus.FAIL,
            message=f"hook verification failed: {', '.join(sorted(failed_hooks))}",
            fixable=True,
        )

    return CheckResult(
        name="hooks-integrity",
        status=CheckStatus.OK,
        message="all hooks verified",
    )


def _check_hooks_scripts(ctx: DoctorContext) -> CheckResult:
    """Check that scripts/hooks/ directory exists under .ai-engineering/."""
    scripts_dir = ctx.target / ".ai-engineering" / "scripts" / "hooks"
    if not scripts_dir.is_dir():
        return CheckResult(
            name="hooks-scripts",
            status=CheckStatus.WARN,
            message="scripts/hooks/ directory missing under .ai-engineering/",
        )

    return CheckResult(
        name="hooks-scripts",
        status=CheckStatus.OK,
        message="scripts/hooks/ directory present",
    )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all hooks phase checks."""
    return [
        _check_hooks_integrity(ctx),
        _check_hooks_scripts(ctx),
    ]


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Attempt to fix failed hooks checks.

    Only ``hooks-integrity`` is fixable via ``install_hooks(force=True)``.
    ``hooks-scripts`` requires a full install and is not auto-fixable.
    """
    results: list[CheckResult] = []

    for cr in failed:
        if cr.name != "hooks-integrity":
            results.append(cr)
            continue

        if dry_run:
            results.append(
                CheckResult(
                    name=cr.name,
                    status=CheckStatus.FIXED,
                    message="would reinstall hooks with force=True",
                )
            )
            continue

        try:
            result = install_hooks(ctx.target, force=True)
            if result.installed:
                results.append(
                    CheckResult(
                        name=cr.name,
                        status=CheckStatus.FIXED,
                        message=f"reinstalled hooks: {', '.join(result.installed)}",
                    )
                )
            else:
                results.append(cr)
        except FileNotFoundError:
            results.append(cr)

    return results
