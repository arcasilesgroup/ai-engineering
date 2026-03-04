"""Branch protection, version deprecation, and hook integrity checks."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.git.operations import PROTECTED_BRANCHES, current_branch
from ai_engineering.hooks.manager import verify_hooks
from ai_engineering.policy.gates import GateCheckResult, GateResult


def check_branch_protection(project_root: Path, result: GateResult) -> None:
    """Block direct commits to protected branches."""
    branch = current_branch(project_root)
    if branch and branch in PROTECTED_BRANCHES:
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=False,
                output=f"Direct commits to '{branch}' are blocked. Use a feature branch.",
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=True,
                output=f"On branch: {branch or 'unknown'}",
            )
        )


def check_version_deprecation(result: GateResult) -> None:
    """Block gate execution if the installed version is deprecated or EOL."""
    from ai_engineering.__version__ import __version__
    from ai_engineering.version.checker import check_version

    check = check_version(__version__)

    if check.is_deprecated or check.is_eol:
        status_label = "deprecated" if check.is_deprecated else "end-of-life"
        result.checks.append(
            GateCheckResult(
                name="version-deprecation",
                passed=False,
                output=(
                    f"ai-engineering {__version__} is {status_label}. "
                    f"{check.message}. "
                    f"Run 'ai-eng update' to upgrade."
                ),
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="version-deprecation",
                passed=True,
                output=f"Version lifecycle: {check.message}",
            )
        )


def check_hook_integrity(project_root: Path, result: GateResult) -> None:
    """Verify managed hooks are intact (marker + optional hash check)."""
    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        result.checks.append(
            GateCheckResult(
                name="hook-integrity",
                passed=True,
                output="No .git/hooks directory — skipped",
            )
        )
        return

    status = verify_hooks(project_root)
    failing = [hook for hook, ok in status.items() if not ok and (hooks_dir / hook).exists()]
    if failing:
        result.checks.append(
            GateCheckResult(
                name="hook-integrity",
                passed=False,
                output=(
                    "Hook integrity check failed for: "
                    + ", ".join(sorted(failing))
                    + ". Reinstall hooks with 'ai-eng doctor --fix-hooks'."
                ),
            )
        )
        return

    result.checks.append(
        GateCheckResult(
            name="hook-integrity",
            passed=True,
            output="Hook integrity verified",
        )
    )
