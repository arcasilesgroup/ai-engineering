"""Azure DevOps VCS provider — wraps the ``az repos`` CLI.

Implements :class:`~ai_engineering.vcs.protocol.VcsProvider` for
Azure DevOps repositories using the ``az`` CLI with the DevOps extension.

Classes:
    AzureDevOpsProvider — ``az repos pr create`` / ``az repos pr update``.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from ai_engineering.vcs.protocol import (
    CreateTagContext,
    IssueContext,
    PipelineStatusContext,
    VcsContext,
    VcsResult,
)


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
            self._read_body(ctx),
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

    def find_open_pr(self, ctx: VcsContext) -> VcsResult:
        """Find an active PR for the current branch via ``az repos pr list``."""
        list_result = self._run(
            [
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
            ],
            ctx,
        )
        if not list_result.success:
            return list_result

        try:
            payload = json.loads(list_result.output.split("\n")[0])
        except json.JSONDecodeError:
            return VcsResult(success=False, output="Failed to parse PR list response")
        if not isinstance(payload, list) or not payload:
            return VcsResult(success=True, output="")
        parsed = payload[0]
        if not isinstance(parsed, dict):
            return VcsResult(success=False, output="Failed to parse PR list response")

        pr_id = str(parsed.get("pullRequestId", ""))
        title = parsed.get("title", "")
        body = parsed.get("description", "")
        web_url = parsed.get("repository", {}).get("webUrl", "")
        url = f"{web_url}/pullrequest/{pr_id}" if web_url and pr_id else ""
        return VcsResult(
            success=True,
            output=json.dumps({"number": pr_id, "title": title, "body": body, "url": url}),
            url=url,
        )

    def update_pr(self, ctx: VcsContext, *, pr_number: str, title: str = "") -> VcsResult:
        """Update PR description/title via ``az repos pr update``."""
        cmd = [
            "az",
            "repos",
            "pr",
            "update",
            "--id",
            pr_number,
            "--description",
            self._read_body(ctx),
            "--output",
            "json",
        ]
        if title:
            cmd.extend(["--title", title])
        return self._run(cmd, ctx)

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        """Enable auto-complete via ``az repos pr update``.

        Sets the auto-complete target merge strategy to squash.

        Args:
            ctx: PR metadata (branch used to find the PR).

        Returns:
            VcsResult indicating success.
        """
        existing = self.find_open_pr(ctx)
        if not existing.success:
            return existing
        if not existing.output:
            return VcsResult(success=False, output=f"No active PR found for branch '{ctx.branch}'")

        try:
            pr_id = str(json.loads(existing.output).get("number", ""))
        except json.JSONDecodeError:
            return VcsResult(success=False, output="Failed to parse PR list response")
        if not pr_id:
            return VcsResult(success=False, output="Failed to parse PR list response")

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

    def check_auth(self, ctx: VcsContext) -> VcsResult:
        """Check Azure authentication status via ``az account show``."""
        return self._run(["az", "account", "show", "--output", "json"], ctx)

    def apply_branch_policy(
        self,
        ctx: VcsContext,
        *,
        branch: str,
        required_checks: list[str],
    ) -> VcsResult:
        """Apply Azure DevOps branch policy/build validation defaults.

        This validates API access and emits a deterministic no-op success when
        command plumbing is available. Concrete policy templates are generated
        by installer guidance for repository admins.
        """
        checks_csv = ",".join(required_checks)
        cmd = [
            "az",
            "repos",
            "policy",
            "list",
            "--branch",
            branch,
            "--output",
            "json",
        ]
        result = self._run(cmd, ctx)
        if result.success:
            result.output = f"Azure policy API reachable; required checks: {checks_csv}"
        return result

    def post_pr_review(self, ctx: VcsContext, *, body: str) -> VcsResult:
        """Post PR thread comment via ``az repos pr comment create``."""
        existing = self.find_open_pr(ctx)
        if not existing.success:
            return existing
        if not existing.output:
            return VcsResult(success=False, output=f"No active PR found for branch '{ctx.branch}'")
        try:
            pr_id = str(json.loads(existing.output).get("number", ""))
        except json.JSONDecodeError:
            return VcsResult(success=False, output="Failed to parse PR list response")
        if not pr_id:
            return VcsResult(success=False, output="Failed to parse PR list response")

        return self._run(
            [
                "az",
                "repos",
                "pr",
                "comment",
                "create",
                "--id",
                pr_id,
                "--content",
                body,
                "--output",
                "json",
            ],
            ctx,
        )

    def create_tag(self, ctx: CreateTagContext) -> VcsResult:
        """Create tag ref via ``az repos ref create``."""
        return self._run(
            [
                "az",
                "repos",
                "ref",
                "create",
                "--name",
                f"refs/tags/{ctx.tag_name}",
                "--object-id",
                ctx.commit_sha,
            ],
            VcsContext(project_root=ctx.project_root),
        )

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        """Get Azure pipeline runs filtered by source version SHA."""
        result = self._run(
            [
                "az",
                "pipelines",
                "runs",
                "list",
                "--top",
                "10",
                "--query-order",
                "FinishTimeDesc",
                "--output",
                "json",
            ],
            VcsContext(project_root=ctx.project_root),
        )
        if not result.success:
            return result

        try:
            runs = json.loads(result.output)
        except json.JSONDecodeError:
            return result

        if isinstance(runs, list):
            filtered = []
            for run in runs:
                if not isinstance(run, dict):
                    continue
                source_version = run.get("sourceVersion") or run.get("source_version")
                if source_version == ctx.head_sha:
                    filtered.append(run)
            result.output = json.dumps(filtered)
        return result

    def create_issue(self, ctx: IssueContext) -> VcsResult:
        """Create an Azure DevOps work item via ``az boards work-item create``."""
        spec_tag = f"spec-{ctx.spec_id}"
        cmd = [
            "az",
            "boards",
            "work-item",
            "create",
            "--type",
            ctx.work_item_type,
            "--title",
            ctx.title,
            "--description",
            ctx.body,
            "--fields",
            f"System.Tags={spec_tag}",
            "--output",
            "json",
        ]
        result = self._run(cmd, VcsContext(project_root=ctx.project_root))
        if result.success:
            try:
                data = json.loads(result.output.split("\n")[0])
                wi_id = str(data.get("id", ""))
                if wi_id:
                    result.output = wi_id
            except (json.JSONDecodeError, IndexError, AttributeError):
                pass
        return result

    def find_issue(self, ctx: IssueContext) -> VcsResult:
        """Find an Azure DevOps work item by ``spec-NNN`` tag via WIQL."""
        spec_tag = f"spec-{ctx.spec_id}"
        wiql = f"SELECT [System.Id] FROM WorkItems WHERE [System.Tags] CONTAINS '{spec_tag}'"
        cmd = [
            "az",
            "boards",
            "query",
            "--wiql",
            wiql,
            "--output",
            "json",
        ]
        result = self._run(cmd, VcsContext(project_root=ctx.project_root))
        if not result.success:
            return result
        try:
            items = json.loads(result.output.split("\n")[0])
        except json.JSONDecodeError:
            return VcsResult(success=False, output="Failed to parse WIQL response")
        if not isinstance(items, list) or not items:
            return VcsResult(success=True, output="")
        first = items[0]
        wi_id = str(first.get("id", ""))
        return VcsResult(success=True, output=wi_id)

    def close_issue(self, ctx: IssueContext, *, issue_id: str) -> VcsResult:
        """Close an Azure DevOps work item via ``az boards work-item update``."""
        return self._run(
            [
                "az",
                "boards",
                "work-item",
                "update",
                "--id",
                issue_id,
                "--state",
                "Done",
                "--output",
                "json",
            ],
            VcsContext(project_root=ctx.project_root),
        )

    def link_issue_to_pr(self, ctx: IssueContext, *, issue_id: str, pr_number: str) -> VcsResult:
        """Link a work item to a PR via ``az repos pr update --work-items``."""
        return self._run(
            [
                "az",
                "repos",
                "pr",
                "update",
                "--id",
                pr_number,
                "--work-items",
                issue_id,
                "--output",
                "json",
            ],
            VcsContext(project_root=ctx.project_root),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    _AZ_BIN = shutil.which("az") or "az"

    @staticmethod
    def _run(cmd: list[str], ctx: VcsContext) -> VcsResult:
        """Execute an ``az`` command and return a VcsResult.

        Args:
            cmd: Command and arguments (first element must be ``"az"``).
            ctx: VcsContext providing the working directory.

        Returns:
            VcsResult with captured output.
        """
        if not cmd or cmd[0] != "az":
            return VcsResult(
                success=False,
                output="Invalid command: must start with 'az'",
            )
        # Replace bare "az" with resolved binary path; validate all args are strings
        safe_cmd = [AzureDevOpsProvider._AZ_BIN]
        for arg in cmd[1:]:
            if not isinstance(arg, str):
                return VcsResult(
                    success=False,
                    output=f"Invalid argument type: {type(arg).__name__}",
                )
            safe_cmd.append(arg)
        try:
            proc = subprocess.run(
                safe_cmd,
                cwd=ctx.project_root,
                capture_output=True,
                text=True,
                timeout=60,
                shell=False,
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

    @staticmethod
    def _read_body(ctx: VcsContext) -> str:
        """Resolve PR body from context or body file path."""
        if ctx.body_file is not None:
            try:
                return ctx.body_file.read_text(encoding="utf-8")
            except OSError:
                return ctx.body
        return ctx.body
