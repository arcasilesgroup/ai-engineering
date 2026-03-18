"""VCS provider protocol and shared types.

Defines the structural interface every VCS backend must satisfy,
plus the ``VcsContext`` dataclass carrying PR metadata.

Classes:
    VcsContext — metadata for a PR operation.
    VcsProvider — Protocol that GitHub and Azure DevOps backends implement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class VcsContext:
    """Metadata required for a VCS operation (e.g. PR creation).

    Attributes:
        project_root: Root directory of the project.
        title: PR title.
        body: PR body (Markdown).
        branch: Source branch name.
        target_branch: Target branch for the PR.
    """

    project_root: Path
    title: str = ""
    body: str = ""
    body_file: Path | None = None
    branch: str = ""
    target_branch: str = "main"


@dataclass(frozen=True)
class CreateTagContext:
    """Context for creating a tag reference in a provider."""

    project_root: Path
    tag_name: str
    commit_sha: str


@dataclass(frozen=True)
class PipelineStatusContext:
    """Context for querying release pipeline status for a commit."""

    project_root: Path
    head_sha: str
    workflow_name: str = "Release"


@dataclass(frozen=True)
class IssueContext:
    """Context for work-item / issue operations.

    Attributes:
        project_root: Root directory of the project.
        spec_id: Spec identifier (e.g. ``"037"``).
        title: Issue title.
        body: Issue body (Markdown).
        labels: Labels/tags to apply.
        work_item_type: Azure DevOps work-item type.
    """

    project_root: Path
    spec_id: str = ""
    title: str = ""
    body: str = ""
    labels: tuple[str, ...] = ()
    work_item_type: str = "User Story"


@dataclass
class VcsResult:
    """Outcome of a VCS operation.

    Attributes:
        success: Whether the operation succeeded.
        output: Combined stdout/stderr output.
        url: URL of the created resource (e.g. PR URL), if any.
    """

    success: bool
    output: str = ""
    url: str = ""


class VcsProvider(Protocol):
    """Structural interface for VCS backends.

    Implementors only need matching method signatures — no inheritance
    required (structural subtyping via Protocol).
    """

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        """Create a pull request.

        Args:
            ctx: PR metadata.

        Returns:
            VcsResult with success flag and PR URL on success.
        """
        ...  # pragma: no cover

    def find_open_pr(self, ctx: VcsContext) -> VcsResult:
        """Find an existing open pull request for ``ctx.branch``.

        Returns:
            VcsResult where ``output`` contains a single PR JSON object,
            or empty output when no open PR exists.
        """
        ...  # pragma: no cover

    def update_pr(self, ctx: VcsContext, *, pr_number: str, title: str = "") -> VcsResult:
        """Update an existing pull request.

        Args:
            ctx: PR metadata containing updated body and optional title.
            pr_number: Provider PR identifier.
            title: Optional title override. Empty keeps existing title.

        Returns:
            VcsResult with success flag.
        """
        ...  # pragma: no cover

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        """Enable auto-complete / auto-merge on the current PR.

        Args:
            ctx: PR metadata (branch used to identify the PR).

        Returns:
            VcsResult with success flag.
        """
        ...  # pragma: no cover

    def is_available(self) -> bool:
        """Check if the provider CLI tool is installed and accessible.

        Returns:
            True if the CLI tool is found on PATH.
        """
        ...  # pragma: no cover

    def provider_name(self) -> str:
        """Return the provider identifier.

        Returns:
            Provider name string (e.g. ``"github"``, ``"azure_devops"``).
        """
        ...  # pragma: no cover

    def check_auth(self, ctx: VcsContext) -> VcsResult:
        """Check whether provider authentication is currently valid.

        Args:
            ctx: Execution context with project root.

        Returns:
            VcsResult with success=True when auth is valid.
        """
        ...  # pragma: no cover

    def apply_branch_policy(
        self,
        ctx: VcsContext,
        *,
        branch: str,
        required_checks: list[str],
    ) -> VcsResult:
        """Apply branch protection/build policy to a branch.

        Args:
            ctx: Execution context with project root.
            branch: Target protected branch (for example ``main``).
            required_checks: Status checks/build validations to require.

        Returns:
            VcsResult for policy application.
        """
        ...  # pragma: no cover

    def post_pr_review(self, ctx: VcsContext, *, body: str) -> VcsResult:
        """Post a PR review comment for the current branch/PR.

        Args:
            ctx: Execution context with branch metadata.
            body: Review body markdown/text.

        Returns:
            VcsResult for the review operation.
        """
        ...  # pragma: no cover

    def create_tag(self, ctx: CreateTagContext) -> VcsResult:
        """Create a tag reference for a commit SHA."""
        ...  # pragma: no cover

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        """Return pipeline/workflow status for a commit SHA."""
        ...  # pragma: no cover

    def create_issue(self, ctx: IssueContext) -> VcsResult:
        """Create a work item / issue linked to a spec.

        Args:
            ctx: Issue metadata (title, body, labels).

        Returns:
            VcsResult with issue number/ID in ``output``.
        """
        ...  # pragma: no cover

    def find_issue(self, ctx: IssueContext) -> VcsResult:
        """Find an existing issue by ``spec-NNN`` label/tag.

        Returns:
            VcsResult where ``output`` contains the issue number/ID,
            or empty output when no issue exists.
        """
        ...  # pragma: no cover

    def close_issue(self, ctx: IssueContext, *, issue_id: str) -> VcsResult:
        """Close a work item / issue.

        Args:
            ctx: Issue context.
            issue_id: Provider issue identifier.

        Returns:
            VcsResult with success flag.
        """
        ...  # pragma: no cover

    def link_issue_to_pr(self, ctx: IssueContext, *, issue_id: str, pr_number: str) -> VcsResult:
        """Link a work item to a pull request.

        Args:
            ctx: Issue context.
            issue_id: Provider issue identifier.
            pr_number: Provider PR identifier.

        Returns:
            VcsResult with success flag.
        """
        ...  # pragma: no cover
