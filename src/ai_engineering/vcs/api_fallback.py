"""API fallback VCS provider.

Used when provider CLI tools are unavailable or blocked.
"""

from __future__ import annotations

from ai_engineering.vcs.protocol import VcsContext, VcsResult


class ApiFallbackProvider:
    """Minimal provider that signals API/manual fallback mode."""

    def __init__(self, provider: str) -> None:
        self._provider = provider

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        return VcsResult(
            success=False,
            output=(
                f"{self._provider} API fallback active: PR creation is not automated in this mode"
            ),
        )

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
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
        return VcsResult(success=False, output="API fallback mode")

    def apply_branch_policy(
        self,
        ctx: VcsContext,
        *,
        branch: str,
        required_checks: list[str],
    ) -> VcsResult:
        return VcsResult(
            success=False,
            output=(
                f"{self._provider} API fallback active: "
                "branch policy requires manual/API credentials"
            ),
        )

    def post_pr_review(self, ctx: VcsContext, *, body: str) -> VcsResult:
        return VcsResult(
            success=False,
            output=f"{self._provider} API fallback active: PR review posting not automated",
        )
