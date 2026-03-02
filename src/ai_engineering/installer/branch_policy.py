"""Branch policy application with deterministic manual fallback guides."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_engineering.vcs.protocol import VcsContext, VcsProvider


@dataclass
class BranchPolicyResult:
    """Result of branch policy enforcement attempt."""

    applied: bool
    mode: str
    message: str
    manual_guide: str | None = None


def apply_branch_policy(
    *,
    provider_name: str,
    provider: VcsProvider,
    project_root: Path,
    branch: str,
    required_checks: list[str],
    mode: str,
) -> BranchPolicyResult:
    """Apply branch policy and fallback to a manual guide when blocked."""
    if mode == "api":
        guide = _format_manual_guide(provider_name, branch, required_checks)
        return BranchPolicyResult(
            applied=False,
            mode="api",
            message="Automatic policy apply unavailable; manual guide available",
            manual_guide=guide,
        )

    result = provider.apply_branch_policy(
        VcsContext(project_root=project_root),
        branch=branch,
        required_checks=required_checks,
    )
    if result.success:
        return BranchPolicyResult(applied=True, mode="cli", message="Branch policy applied")

    guide = _format_manual_guide(provider_name, branch, required_checks)
    return BranchPolicyResult(
        applied=False,
        mode="api",
        message=f"Automatic policy apply failed; manual guide available ({result.output})",
        manual_guide=guide,
    )


def _format_manual_guide(
    provider_name: str,
    branch: str,
    required_checks: list[str],
) -> str:
    checks = "\n".join([f"- `{check}`" for check in required_checks])
    return (
        f"# Manual Branch Policy Setup ({provider_name})\n\n"
        f"## Target Branch\n\n"
        f"`{branch}`\n\n"
        f"## Required Checks\n\n{checks}\n\n"
        "## Notes\n\n"
        "- Enforce pull request reviews before merge.\n"
        "- Block direct pushes to protected branches.\n"
        "- Require all checks above before merge.\n"
    )
