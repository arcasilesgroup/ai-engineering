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
    branch: str = ""
    target_branch: str = "main"


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
