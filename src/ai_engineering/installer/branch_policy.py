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

    github_steps = (
        "## GitHub Setup\n\n"
        "1. Go to **Settings > Branches > Branch protection rules > Add rule**\n"
        f"2. Set **Branch name pattern** to `{branch}`\n"
        "3. Enable **Require a pull request before merging**\n"
        "   - Set the minimum number of approvals your team requires\n"
        "4. Enable **Require status checks to pass before merging**\n"
        "   - Check **Require branches to be up to date before merging**\n"
        "   - Add each required check listed above\n"
        "5. Enable **Do not allow bypassing the above settings** (recommended)\n"
        "6. Click **Create** to save the rule\n"
    )

    azure_devops_steps = (
        "## Azure DevOps Setup\n\n"
        "1. Go to **Project Settings > Repos > Policies > Branch Policies**\n"
        f"2. Select the `{branch}` branch\n"
        "3. Under **Minimum number of reviewers**, set the count your team requires\n"
        "4. Under **Build validation**, click **Add build policy**\n"
        "   - Select the pipeline that runs the required checks listed above\n"
        "   - Set **Trigger** to *Automatic*\n"
        "   - Set **Policy requirement** to *Required*\n"
        "5. Under **Comment resolution**, set to *Required*\n"
        "6. Save the policy\n"
    )

    provider_lower = provider_name.lower()
    if provider_lower == "github":
        provider_section = github_steps
    elif provider_lower in ("azure_devops", "azuredevops", "azure devops"):
        provider_section = azure_devops_steps
    else:
        provider_section = f"{github_steps}\n{azure_devops_steps}"

    return (
        f"# Manual Branch Policy Setup ({provider_name})\n\n"
        f"## Target Branch\n\n"
        f"`{branch}`\n\n"
        f"## Required Checks\n\n{checks}\n\n"
        f"{provider_section}\n"
        "## General Notes\n\n"
        "- Enforce pull request reviews before merge.\n"
        "- Block direct pushes to protected branches.\n"
        "- Require all checks above to pass before merge.\n"
    )
