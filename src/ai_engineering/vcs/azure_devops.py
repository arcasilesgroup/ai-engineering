"""Azure DevOps VCS provider — wraps the ``az repos`` CLI.

Implements :class:`~ai_engineering.vcs.protocol.VcsProvider` for
Azure DevOps repositories using the ``az`` CLI with the DevOps extension.

Classes:
    AzureDevOpsProvider — ``az repos pr create`` / ``az repos pr update``.
"""

from __future__ import annotations

import shutil
import subprocess

from ai_engineering.vcs.protocol import VcsContext, VcsResult


class AzureDevOpsProvider:
    """VCS provider backed by the Azure DevOps CLI (``az repos``).

    All operations shell out to ``az`` with explicit timeouts
    and UTF-8 encoding.
    """

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        """Create a pull request via ``az repos pr create``.

        Args:
            ctx: PR metadata (title, body, source/target branches).

        Returns:
            VcsResult with PR URL on success.
        """
        cmd = [
            "az",
            "repos",
            "pr",
            "create",
            "--title",
            ctx.title or ctx.branch,
            "--description",
            ctx.body or "",
            "--source-branch",
            ctx.branch,
            "--target-branch",
            ctx.target_branch,
            "--output",
            "json",
        ]
        result = self._run(cmd, ctx)

        # Extract PR URL from JSON output
        if result.success:
            import json

            try:
                data = json.loads(result.output.split("\n")[0])
                web_url = data.get("repository", {}).get("webUrl", "")
                pr_id = data.get("pullRequestId", "")
                if web_url and pr_id:
                    result.url = f"{web_url}/pullrequest/{pr_id}"
            except (json.JSONDecodeError, IndexError, AttributeError):
                pass

        return result

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        """Enable auto-complete via ``az repos pr update``.

        Sets the auto-complete target merge strategy to squash.

        Args:
            ctx: PR metadata (branch used to find the PR).

        Returns:
            VcsResult indicating success.
        """
        # First, find the active PR for this branch
        list_cmd = [
            "az",
            "repos",
            "pr",
            "list",
            "--source-branch",
            ctx.branch,
            "--status",
            "active",
            "--output",
            "json",
        ]
        list_result = self._run(list_cmd, ctx)
        if not list_result.success:
            return list_result

        import json

        try:
            prs = json.loads(list_result.output.split("\n")[0])
            if not prs:
                return VcsResult(
                    success=False,
                    output=f"No active PR found for branch '{ctx.branch}'",
                )
            pr_id = str(prs[0]["pullRequestId"])
        except (json.JSONDecodeError, IndexError, KeyError):
            return VcsResult(
                success=False,
                output="Failed to parse PR list response",
            )

        # Enable auto-complete with squash merge
        update_cmd = [
            "az",
            "repos",
            "pr",
            "update",
            "--id",
            pr_id,
            "--auto-complete",
            "true",
            "--squash",
            "true",
            "--delete-source-branch",
            "true",
        ]
        return self._run(update_cmd, ctx)

    def is_available(self) -> bool:
        """Check if the ``az`` CLI is on PATH.

        Returns:
            True if ``az`` is found.
        """
        return shutil.which("az") is not None

    def provider_name(self) -> str:
        """Return ``"azure_devops"``."""
        return "azure_devops"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _run(cmd: list[str], ctx: VcsContext) -> VcsResult:
        """Execute an ``az`` command and return a VcsResult.

        Args:
            cmd: Command and arguments.
            ctx: VcsContext providing the working directory.

        Returns:
            VcsResult with captured output.
        """
        try:
            proc = subprocess.run(
                cmd,
                cwd=ctx.project_root,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            output = (proc.stdout + "\n" + proc.stderr).strip()
            return VcsResult(
                success=proc.returncode == 0,
                output=output,
            )
        except FileNotFoundError:
            return VcsResult(success=False, output="az CLI not found on PATH")
        except subprocess.TimeoutExpired:
            return VcsResult(success=False, output="az command timed out after 60s")
