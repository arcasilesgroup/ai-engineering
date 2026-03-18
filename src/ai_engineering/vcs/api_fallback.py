"""API fallback VCS provider.

Used when provider CLI tools are unavailable or blocked.
"""

from __future__ import annotations

from ai_engineering.vcs.protocol import (
    CreateTagContext,
    IssueContext,
    PipelineStatusContext,
    VcsContext,
    VcsResult,
)


class ApiFallbackProvider:
    """Minimal provider that signals API/manual fallback mode."""

    def __init__(self, provider: str) -> None:
        self._provider = provider

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=(
                f"{self._provider} API fallback active: PR creation is not automated in this mode"
            ),
        )

    def find_open_pr(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: PR lookup is not automated",
        )

    def update_pr(self, ctx: VcsContext, *, pr_number: str, title: str = "") -> VcsResult:
        del ctx, pr_number, title
        return VcsResult(
            success=False,
            output=(
                f"{self._provider} API fallback active: PR update is not automated in this mode"
            ),
        )

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=(
                f"{self._provider} API fallback active: auto-complete is not automated in this mode"
            ),
        )

    def is_available(self) -> bool:
        return True

    def provider_name(self) -> str:
        return self._provider

    def check_auth(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(success=False, output="API fallback mode")

    def apply_branch_policy(
        self,
        ctx: VcsContext,
        *,
        branch: str,
        required_checks: list[str],
    ) -> VcsResult:
        del ctx, branch, required_checks
        return VcsResult(
            success=False,
            output=(
                f"{self._provider} API fallback active: "
                "branch policy requires manual/API credentials"
            ),
        )

    def post_pr_review(self, ctx: VcsContext, *, body: str) -> VcsResult:
        del ctx, body
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: PR review posting not automated",
        )

    def create_tag(self, ctx: CreateTagContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: tag creation not automated",
        )

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: pipeline status not automated",
        )

    def create_issue(self, ctx: IssueContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: issue creation not automated",
        )

    def find_issue(self, ctx: IssueContext) -> VcsResult:
        del ctx
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: issue lookup not automated",
        )

    def close_issue(self, ctx: IssueContext, *, issue_id: str) -> VcsResult:
        del ctx, issue_id
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: issue close not automated",
        )

    def link_issue_to_pr(self, ctx: IssueContext, *, issue_id: str, pr_number: str) -> VcsResult:
        del ctx, issue_id, pr_number
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: issue-PR linking not automated",
        )
