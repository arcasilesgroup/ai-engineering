"""Unit tests for VCS PR description builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.vcs.pr_description import (
    _build_spec_url,
    _get_repo_url,
    _humanize_branch,
    _read_active_spec,
    _recent_commit_subjects,
    build_pr_description,
    build_pr_title,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _humanize_branch
# ---------------------------------------------------------------------------


class TestHumanizeBranch:
    """Tests for branch name humanization."""

    def test_strips_feat_prefix(self) -> None:
        assert _humanize_branch("feat/dual-vcs-provider") == "Dual vcs provider"

    def test_strips_fix_prefix(self) -> None:
        assert _humanize_branch("fix/broken-gate") == "Broken gate"

    def test_no_prefix(self) -> None:
        assert _humanize_branch("my-branch") == "My branch"

    def test_underscores_replaced(self) -> None:
        assert _humanize_branch("feat/some_feature") == "Some feature"

    def test_empty_after_prefix(self) -> None:
        assert _humanize_branch("feat/") == ""

    def test_plain_branch_name(self) -> None:
        assert _humanize_branch("main") == "Main"


# ---------------------------------------------------------------------------
# _read_active_spec
# ---------------------------------------------------------------------------


class TestReadActiveSpec:
    """Tests for reading the active spec identifier."""

    def test_returns_spec_id(self, tmp_path: Path) -> None:
        active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
        active.parent.mkdir(parents=True)
        active.write_text(
            '---\nactive: "014-dual-vcs-provider"\nupdated: "2026-02-22"\n---\n',
            encoding="utf-8",
        )
        assert _read_active_spec(tmp_path) == "014-dual-vcs-provider"

    def test_returns_none_when_none(self, tmp_path: Path) -> None:
        active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
        active.parent.mkdir(parents=True)
        active.write_text('---\nactive: "none"\n---\n', encoding="utf-8")
        assert _read_active_spec(tmp_path) is None

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        assert _read_active_spec(tmp_path) is None

    def test_returns_none_when_no_frontmatter(self, tmp_path: Path) -> None:
        active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
        active.parent.mkdir(parents=True)
        active.write_text("# Active Spec\nNothing here.\n", encoding="utf-8")
        assert _read_active_spec(tmp_path) is None


# ---------------------------------------------------------------------------
# _recent_commit_subjects
# ---------------------------------------------------------------------------


class TestRecentCommitSubjects:
    """Tests for fetching recent commit subjects."""

    def test_returns_subjects_from_diff(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "Fix bug\nAdd feature\n"),
        ):
            subjects = _recent_commit_subjects(tmp_path, max_commits=5)
        assert subjects == ["Fix bug", "Add feature"]

    def test_falls_back_when_diff_empty(self, tmp_path: Path) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], cwd: Path, **kwargs: object) -> tuple[bool, str]:
            calls.append(args)
            if "origin/main..HEAD" in args:
                return (True, "")
            return (True, "Fallback commit\n")

        with patch("ai_engineering.vcs.pr_description.run_git", side_effect=fake_run_git):
            subjects = _recent_commit_subjects(tmp_path)
        assert subjects == ["Fallback commit"]
        assert len(calls) == 2

    def test_returns_empty_on_failure(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(False, ""),
        ):
            subjects = _recent_commit_subjects(tmp_path)
        assert subjects == []


# ---------------------------------------------------------------------------
# build_pr_title
# ---------------------------------------------------------------------------


class TestBuildPrTitle:
    """Tests for PR title generation."""

    def test_includes_spec_prefix(self, tmp_path: Path) -> None:
        active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
        active.parent.mkdir(parents=True)
        active.write_text('---\nactive: "014-dual-vcs-provider"\n---\n', encoding="utf-8")

        with patch(
            "ai_engineering.vcs.pr_description.current_branch",
            return_value="feat/dual-vcs-provider",
        ):
            title = build_pr_title(tmp_path)
        assert title == "spec-014-dual-vcs-provider: Dual vcs provider"

    def test_no_spec_uses_branch_only(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.current_branch",
            return_value="fix/broken-gate",
        ):
            title = build_pr_title(tmp_path)
        assert title == "Broken gate"


# ---------------------------------------------------------------------------
# build_pr_description
# ---------------------------------------------------------------------------


class TestBuildPrDescription:
    """Tests for PR description generation."""

    def test_includes_spec_and_commits(self, tmp_path: Path) -> None:
        active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
        active.parent.mkdir(parents=True)
        active.write_text('---\nactive: "014"\n---\n', encoding="utf-8")

        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "Commit one\nCommit two\n"),
        ):
            body = build_pr_description(tmp_path)
        assert "## Spec" in body
        assert "`014`" in body
        assert "- Commit one" in body
        assert "- Commit two" in body

    def test_no_spec_no_commits(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(False, ""),
        ):
            body = build_pr_description(tmp_path)
        assert body == "No description generated."

    def test_includes_spec_url_when_repo_detected(self, tmp_path: Path) -> None:
        active = tmp_path / ".ai-engineering" / "context" / "specs" / "_active.md"
        active.parent.mkdir(parents=True)
        active.write_text('---\nactive: "036-platform-runbooks"\n---\n', encoding="utf-8")

        def fake_run_git(args: list[str], cwd: Path, **kw: object) -> tuple[bool, str]:
            if "remote" in args:
                return (True, "https://github.com/org/repo")
            return (True, "Some commit\n")

        with patch("ai_engineering.vcs.pr_description.run_git", side_effect=fake_run_git):
            body = build_pr_description(tmp_path)

        assert "[036-platform-runbooks]" in body
        assert "github.com/org/repo/blob/main/" in body
        assert "spec.md)" in body


# ---------------------------------------------------------------------------
# _get_repo_url
# ---------------------------------------------------------------------------


class TestGetRepoUrl:
    """Tests for repository URL detection from git remote."""

    def test_github_ssh(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "git@github.com:org/repo.git"),
        ):
            assert _get_repo_url(tmp_path) == "https://github.com/org/repo"

    def test_github_https(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://github.com/org/repo.git"),
        ):
            assert _get_repo_url(tmp_path) == "https://github.com/org/repo"

    def test_github_https_no_dotgit(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://github.com/org/repo"),
        ):
            assert _get_repo_url(tmp_path) == "https://github.com/org/repo"

    def test_azure_devops_ssh(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "git@ssh.dev.azure.com:v3/myorg/myproj/myrepo"),
        ):
            assert _get_repo_url(tmp_path) == "https://dev.azure.com/myorg/myproj/_git/myrepo"

    def test_azure_devops_https(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://dev.azure.com/myorg/myproj/_git/myrepo.git"),
        ):
            assert _get_repo_url(tmp_path) == "https://dev.azure.com/myorg/myproj/_git/myrepo"

    def test_returns_none_on_failure(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(False, ""),
        ):
            assert _get_repo_url(tmp_path) is None

    def test_returns_none_on_empty_output(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "  "),
        ):
            assert _get_repo_url(tmp_path) is None

    def test_returns_none_for_unknown_host(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://gitlab.com/org/repo"),
        ):
            assert _get_repo_url(tmp_path) is None


# ---------------------------------------------------------------------------
# _build_spec_url
# ---------------------------------------------------------------------------


class TestBuildSpecUrl:
    """Tests for spec URL construction."""

    def test_github_spec_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://github.com/org/repo"),
        ):
            url = _build_spec_url(tmp_path, "036-platform-runbooks")
        assert url == (
            "https://github.com/org/repo/blob/main/"
            ".ai-engineering/context/specs/036-platform-runbooks/spec.md"
        )

    def test_azure_devops_spec_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://dev.azure.com/myorg/myproj/_git/myrepo"),
        ):
            url = _build_spec_url(tmp_path, "036-platform-runbooks")
        assert url == (
            "https://dev.azure.com/myorg/myproj/_git/myrepo"
            "?path=/.ai-engineering/context/specs/036-platform-runbooks/spec.md"
            "&version=GBmain"
        )

    def test_returns_none_when_no_repo(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(False, ""),
        ):
            assert _build_spec_url(tmp_path, "036") is None
