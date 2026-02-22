"""GitHub VCS provider — wraps the ``gh`` CLI.

Implements :class:`~ai_engineering.vcs.protocol.VcsProvider` for
GitHub repositories using the ``gh`` CLI.

Classes:
    GitHubProvider — ``gh pr create`` / ``gh pr merge --auto``.
"""

from __future__ import annotations

import shutil
import subprocess

from ai_engineering.vcs.protocol import VcsContext, VcsResult


class GitHubProvider:
    """VCS provider backed by the GitHub CLI (``gh``).

    All operations shell out to ``gh`` with explicit timeouts
    and UTF-8 encoding.
    """

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        """Create a pull request via ``gh pr create``.

        Args:
            ctx: PR metadata (title, body, target branch).

        Returns:
            VcsResult with PR URL on success.
        """
        cmd = [
            "gh",
            "pr",
            "create",
            "--title",
            ctx.title or "--fill",
            "--body",
            ctx.body or "",
            "--base",
            ctx.target_branch,
        ]
        # If no explicit title, use --fill instead
        if not ctx.title:
            cmd = ["gh", "pr", "create", "--fill"]

        return self._run(cmd, ctx)

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        """Enable auto-merge via ``gh pr merge --auto --squash --delete-branch``.

        Args:
            ctx: PR metadata (branch used to identify the PR).

        Returns:
            VcsResult indicating success.
        """
        cmd = ["gh", "pr", "merge", "--auto", "--squash", "--delete-branch"]
        return self._run(cmd, ctx)

    def is_available(self) -> bool:
        """Check if ``gh`` CLI is on PATH.

        Returns:
            True if ``gh`` is found.
        """
        return shutil.which("gh") is not None

    def provider_name(self) -> str:
        """Return ``"github"``."""
        return "github"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _run(cmd: list[str], ctx: VcsContext) -> VcsResult:
        """Execute a ``gh`` command and return a VcsResult.

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
            url = ""
            if proc.returncode == 0:
                # gh pr create prints the PR URL on stdout
                for line in proc.stdout.strip().splitlines():
                    if line.startswith("https://"):
                        url = line.strip()
                        break
            return VcsResult(
                success=proc.returncode == 0,
                output=output,
                url=url,
            )
        except FileNotFoundError:
            return VcsResult(success=False, output="gh CLI not found on PATH")
        except subprocess.TimeoutExpired:
            return VcsResult(success=False, output="gh command timed out after 60s")
