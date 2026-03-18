"""GitHub VCS provider — wraps the ``gh`` CLI.

Implements :class:`~ai_engineering.vcs.protocol.VcsProvider` for
GitHub repositories using the ``gh`` CLI.

Classes:
    GitHubProvider — ``gh pr create`` / ``gh pr merge --auto``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_engineering.vcs.protocol import (
    CreateTagContext,
    IssueContext,
    PipelineStatusContext,
    VcsContext,
    VcsResult,
)


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
        if not ctx.title and not ctx.body and ctx.body_file is None:
            return self._run(
                ["gh", "pr", "create", "--fill", "--base", ctx.target_branch],
                ctx,
            )

        body_file, cleanup = self._resolve_body_file(ctx)
        try:
            cmd = [
                "gh",
                "pr",
                "create",
                "--title",
                ctx.title or ctx.branch or "PR",
                "--body-file",
                str(body_file),
                "--base",
                ctx.target_branch,
            ]
            return self._run(cmd, ctx)
        finally:
            if cleanup:
                body_file.unlink(missing_ok=True)

    def find_open_pr(self, ctx: VcsContext) -> VcsResult:
        """Find an open PR for the current branch via ``gh pr list``."""
        result = self._run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                ctx.branch,
                "--state",
                "open",
                "--json",
                "number,title,body,url",
            ],
            ctx,
        )
        if not result.success:
            return result
        try:
            prs = json.loads(result.output or "[]")
        except json.JSONDecodeError:
            return VcsResult(success=False, output="Failed to parse GitHub PR list response")
        if not isinstance(prs, list) or not prs:
            return VcsResult(success=True, output="")
        return VcsResult(success=True, output=json.dumps(prs[0]))

    def update_pr(self, ctx: VcsContext, *, pr_number: str, title: str = "") -> VcsResult:
        """Update PR body (and optionally title) via ``gh pr edit``."""
        body_file, cleanup = self._resolve_body_file(ctx)
        try:
            cmd = [
                "gh",
                "pr",
                "edit",
                pr_number,
                "--body-file",
                str(body_file),
            ]
            if title:
                cmd.extend(["--title", title])
            return self._run(cmd, ctx)
        finally:
            if cleanup:
                body_file.unlink(missing_ok=True)

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

    def check_auth(self, ctx: VcsContext) -> VcsResult:
        """Check GitHub authentication status via ``gh auth status``."""
        return self._run(["gh", "auth", "status"], ctx)

    def apply_branch_policy(
        self,
        ctx: VcsContext,
        *,
        branch: str,
        required_checks: list[str],
    ) -> VcsResult:
        """Apply branch protection with required status checks via ``gh api``."""
        checks_csv = ",".join(required_checks)
        cmd = [
            "gh",
            "api",
            "--method",
            "PUT",
            "repos/{owner}/{repo}/branches/{branch}/protection",
            "-F",
            "required_pull_request_reviews={}",
            "-F",
            f"required_status_checks[checks][]={checks_csv}",
            "-F",
            "required_status_checks[strict]=true",
            "-F",
            "enforce_admins=true",
        ]
        return self._run(cmd, ctx)

    def post_pr_review(self, ctx: VcsContext, *, body: str) -> VcsResult:
        """Post PR review comment on current branch via ``gh pr comment``."""
        cmd = ["gh", "pr", "comment", "--body", body]
        return self._run(cmd, ctx)

    def create_tag(self, ctx: CreateTagContext) -> VcsResult:
        """Create tag ref via GitHub API (bypasses local pre-push hook)."""
        cmd = [
            "gh",
            "api",
            "repos/{owner}/{repo}/git/refs",
            "-f",
            f"ref=refs/tags/{ctx.tag_name}",
            "-f",
            f"sha={ctx.commit_sha}",
        ]
        return self._run(cmd, VcsContext(project_root=ctx.project_root))

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        """Get workflow run status filtered by head SHA."""
        cmd = [
            "gh",
            "run",
            "list",
            "--workflow",
            ctx.workflow_name,
            "--json",
            "headSha,status,conclusion,url,databaseId",
        ]
        result = self._run(cmd, VcsContext(project_root=ctx.project_root))
        if not result.success:
            return result

        try:
            runs = json.loads(result.output)
        except json.JSONDecodeError:
            return result

        if isinstance(runs, list):
            filtered = [
                run for run in runs if isinstance(run, dict) and run.get("headSha") == ctx.head_sha
            ]
            result.output = json.dumps(filtered)
        return result

    def create_issue(self, ctx: IssueContext) -> VcsResult:
        """Create a GitHub issue via ``gh issue create``."""
        cmd = [
            "gh",
            "issue",
            "create",
            "--title",
            ctx.title,
            "--body",
            ctx.body,
        ]
        for label in ctx.labels:
            cmd.extend(["--label", label])
        return self._run(cmd, VcsContext(project_root=ctx.project_root))

    def find_issue(self, ctx: IssueContext) -> VcsResult:
        """Find a GitHub issue by ``spec-NNN`` label."""
        spec_label = f"spec-{ctx.spec_id}"
        cmd = [
            "gh",
            "issue",
            "list",
            "--label",
            spec_label,
            "--state",
            "all",
            "--json",
            "number,title,state",
            "--limit",
            "1",
        ]
        result = self._run(cmd, VcsContext(project_root=ctx.project_root))
        if not result.success:
            return result
        try:
            issues = json.loads(result.output or "[]")
        except json.JSONDecodeError:
            return VcsResult(success=False, output="Failed to parse issue list response")
        if not isinstance(issues, list) or not issues:
            return VcsResult(success=True, output="")
        return VcsResult(success=True, output=str(issues[0].get("number", "")))

    def close_issue(self, ctx: IssueContext, *, issue_id: str) -> VcsResult:
        """Close a GitHub issue via ``gh issue close``."""
        return self._run(
            ["gh", "issue", "close", issue_id],
            VcsContext(project_root=ctx.project_root),
        )

    def link_issue_to_pr(self, ctx: IssueContext, *, issue_id: str, pr_number: str) -> VcsResult:
        """No-op — GitHub links via ``Closes #N`` keyword in PR body."""
        del ctx, issue_id, pr_number
        return VcsResult(success=True, output="GitHub links via PR body keyword")

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

    @staticmethod
    def _resolve_body_file(ctx: VcsContext) -> tuple[Path, bool]:
        """Return body file path and whether caller must clean it up."""
        if ctx.body_file is not None:
            return ctx.body_file, False
        fd, temp_path = tempfile.mkstemp(prefix="ai-eng-pr-", suffix=".md")
        path = Path(temp_path)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(ctx.body)
        return path, True
