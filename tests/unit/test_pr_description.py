"""Unit tests for VCS PR description builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.vcs.pr_description import (
    _build_spec_url,
    _extract_section,
    _get_repo_url,
    _git_diff_stats,
    _humanize_branch,
    _read_active_spec,
    _read_spec_context,
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

    def test_what_why_how_sections_with_spec(self, tmp_path: Path) -> None:
        specs_dir = tmp_path / ".ai-engineering" / "context" / "specs"
        active = specs_dir / "_active.md"
        specs_dir.mkdir(parents=True)
        active.write_text('---\nactive: "014-my-feature"\n---\n', encoding="utf-8")
        spec_file = specs_dir / "014-my-feature" / "spec.md"
        spec_file.parent.mkdir()
        spec_file.write_text(
            "---\nid: 014\n---\n# Spec 014 — My Feature\n\n"
            "## Problem\n\nSomething is broken.\n\n## Solution\n\nFix it.\n",
            encoding="utf-8",
        )

        with (
            patch(
                "ai_engineering.vcs.pr_description.run_git",
                return_value=(True, "Commit one\nCommit two\n"),
            ),
            patch(
                "ai_engineering.vcs.pr_description.current_branch",
                return_value="spec-014/my-feature",
            ),
        ):
            body = build_pr_description(tmp_path)
        assert "## What" in body
        assert "Implements Spec 014 — My Feature." in body
        assert "## Why" in body
        assert "Something is broken." in body
        assert "## How" in body
        assert "- Commit one" in body
        assert "## Checklist" in body
        assert "## Stats" not in body or "commits on" in body

    def test_no_spec_uses_branch(self, tmp_path: Path) -> None:
        with (
            patch(
                "ai_engineering.vcs.pr_description.run_git",
                return_value=(True, "Fix things\n"),
            ),
            patch(
                "ai_engineering.vcs.pr_description.current_branch",
                return_value="fix/broken-gate",
            ),
        ):
            body = build_pr_description(tmp_path)
        assert "## What" in body
        assert "Broken gate." in body
        assert "## Why" not in body
        assert "## How" in body

    def test_no_spec_no_commits(self, tmp_path: Path) -> None:
        with (
            patch(
                "ai_engineering.vcs.pr_description.run_git",
                return_value=(False, ""),
            ),
            patch(
                "ai_engineering.vcs.pr_description.current_branch",
                return_value="main",
            ),
        ):
            body = build_pr_description(tmp_path)
        assert "## What" in body
        assert "## Checklist" in body

    def test_includes_spec_url_when_repo_detected(self, tmp_path: Path) -> None:
        specs_dir = tmp_path / ".ai-engineering" / "context" / "specs"
        active = specs_dir / "_active.md"
        specs_dir.mkdir(parents=True)
        active.write_text('---\nactive: "036-platform-runbooks"\n---\n', encoding="utf-8")
        spec_file = specs_dir / "036-platform-runbooks" / "spec.md"
        spec_file.parent.mkdir()
        spec_file.write_text(
            "# Spec 036 — Platform Runbooks\n\n## Problem\n\nMissing.\n",
            encoding="utf-8",
        )

        def fake_run_git(args: list[str], cwd: Path, **kw: object) -> tuple[bool, str]:
            if "remote" in args:
                return (True, "https://github.com/org/repo")
            return (True, "Some commit\n")

        with (
            patch("ai_engineering.vcs.pr_description.run_git", side_effect=fake_run_git),
            patch(
                "ai_engineering.vcs.pr_description.current_branch",
                return_value="spec-036/platform-runbooks",
            ),
        ):
            body = build_pr_description(tmp_path)

        assert "[036-platform-runbooks]" in body
        assert "github.com/org/repo/blob/main/" in body
        assert "spec.md)" in body

    def test_stats_section_with_diff(self, tmp_path: Path) -> None:
        specs_dir = tmp_path / ".ai-engineering" / "context" / "specs"
        active = specs_dir / "_active.md"
        specs_dir.mkdir(parents=True)
        active.write_text('---\nactive: "001-test"\n---\n', encoding="utf-8")
        spec_file = specs_dir / "001-test" / "spec.md"
        spec_file.parent.mkdir()
        spec_file.write_text("# Spec 001 — Test\n", encoding="utf-8")

        call_count = 0

        def fake_run_git(args: list[str], cwd: Path, **kw: object) -> tuple[bool, str]:
            nonlocal call_count
            call_count += 1
            if "remote" in args:
                return (False, "")
            if "diff" in args and "--stat" in args:
                return (True, " 5 files changed, 120 insertions(+), 30 deletions(-)\n")
            if "origin/main..HEAD" in " ".join(args):
                return (True, "Commit A\n")
            return (True, "Commit A\n")

        with (
            patch("ai_engineering.vcs.pr_description.run_git", side_effect=fake_run_git),
            patch(
                "ai_engineering.vcs.pr_description.current_branch",
                return_value="spec-001/test",
            ),
        ):
            body = build_pr_description(tmp_path)

        assert "## Stats" in body
        assert "5 files changed" in body
        assert "1 commits on `spec-001/test`" in body


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

    def test_github_spec_url_active(self, tmp_path: Path) -> None:
        """Active (non-archived) spec uses specs/{slug}/ path."""
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://github.com/org/repo"),
        ):
            url = _build_spec_url(tmp_path, "036-platform-runbooks")
        assert url == (
            "https://github.com/org/repo/blob/main/"
            ".ai-engineering/context/specs/036-platform-runbooks/spec.md"
        )

    def test_github_spec_url_archived(self, tmp_path: Path) -> None:
        """Archived spec uses specs/archive/{slug}/ path."""
        archive = (
            tmp_path / ".ai-engineering" / "context" / "specs" / "archive" / "036-platform-runbooks"
        )
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text("# Spec", encoding="utf-8")

        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://github.com/org/repo"),
        ):
            url = _build_spec_url(tmp_path, "036-platform-runbooks")
        assert url == (
            "https://github.com/org/repo/blob/main/"
            ".ai-engineering/context/specs/archive/036-platform-runbooks/spec.md"
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

    def test_azure_devops_spec_url_archived(self, tmp_path: Path) -> None:
        """Archived spec uses archive path on Azure DevOps."""
        archive = (
            tmp_path / ".ai-engineering" / "context" / "specs" / "archive" / "036-platform-runbooks"
        )
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text("# Spec", encoding="utf-8")

        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://dev.azure.com/myorg/myproj/_git/myrepo"),
        ):
            url = _build_spec_url(tmp_path, "036-platform-runbooks")
        assert url == (
            "https://dev.azure.com/myorg/myproj/_git/myrepo"
            "?path=/.ai-engineering/context/specs/archive/036-platform-runbooks/spec.md"
            "&version=GBmain"
        )

    def test_returns_none_when_no_repo(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(False, ""),
        ):
            assert _build_spec_url(tmp_path, "036") is None

    def test_returns_none_for_unknown_provider(self, tmp_path: Path) -> None:
        specs = tmp_path / ".ai-engineering" / "context" / "specs" / "036" / "spec.md"
        specs.parent.mkdir(parents=True)
        specs.write_text("spec", encoding="utf-8")
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "https://gitlab.com/org/repo.git"),
        ):
            assert _build_spec_url(tmp_path, "036") is None


# ---------------------------------------------------------------------------
# _read_spec_context
# ---------------------------------------------------------------------------


class TestReadSpecContext:
    """Tests for reading spec sections."""

    def test_reads_title_problem_solution(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / ".ai-engineering" / "context" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "---\nid: 001\n---\n# Spec 001 — My Feature Title\n\n"
            "## Problem\n\nThings are broken.\n\n## Solution\n\nFix them.\n",
            encoding="utf-8",
        )
        ctx = _read_spec_context(tmp_path, "001-test")
        assert ctx["title"] == "My Feature Title"
        assert ctx["problem"] == "Things are broken."
        assert ctx["solution"] == "Fix them."

    def test_reads_from_archive(self, tmp_path: Path) -> None:
        archive = tmp_path / ".ai-engineering" / "context" / "specs" / "archive" / "001-test"
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text(
            "# Spec 001 — Archived Feature\n\n## Problem\n\nOld issue.\n",
            encoding="utf-8",
        )
        ctx = _read_spec_context(tmp_path, "001-test")
        assert ctx["title"] == "Archived Feature"
        assert ctx["problem"] == "Old issue."

    def test_returns_empty_when_missing(self, tmp_path: Path) -> None:
        ctx = _read_spec_context(tmp_path, "nonexistent")
        assert ctx == {"title": "", "problem": "", "solution": ""}

    def test_returns_empty_on_os_error(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / ".ai-engineering" / "context" / "specs" / "003-err"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Spec 003 — Err\n", encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=OSError("perm denied")):
            ctx = _read_spec_context(tmp_path, "003-err")
        assert ctx == {"title": "", "problem": "", "solution": ""}

    def test_returns_first_paragraph_only(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / ".ai-engineering" / "context" / "specs" / "002-multi"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(
            "# Spec 002 — Multi Para\n\n## Problem\n\nFirst paragraph.\n\nSecond paragraph.\n",
            encoding="utf-8",
        )
        ctx = _read_spec_context(tmp_path, "002-multi")
        assert ctx["problem"] == "First paragraph."


# ---------------------------------------------------------------------------
# _extract_section
# ---------------------------------------------------------------------------


class TestExtractSection:
    """Tests for Markdown section extraction."""

    def test_extracts_section(self) -> None:
        text = "## Problem\n\nBroken.\n\n## Solution\n\nFix.\n"
        assert _extract_section(text, "Problem") == "Broken."
        assert _extract_section(text, "Solution") == "Fix."

    def test_returns_empty_for_missing_heading(self) -> None:
        assert _extract_section("## Other\n\nContent.\n", "Problem") == ""

    def test_handles_last_section(self) -> None:
        text = "## Problem\n\nOnly section content here.\n"
        assert _extract_section(text, "Problem") == "Only section content here."


# ---------------------------------------------------------------------------
# _git_diff_stats
# ---------------------------------------------------------------------------


class TestGitDiffStats:
    """Tests for git diff statistics."""

    def test_returns_summary_line(self, tmp_path: Path) -> None:
        output = " src/file.py | 10 +++++\n 3 files changed, 25 insertions(+), 5 deletions(-)\n"
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, output),
        ):
            stats = _git_diff_stats(tmp_path)
        assert stats == "3 files changed, 25 insertions(+), 5 deletions(-)"

    def test_returns_none_on_failure(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(False, ""),
        ):
            assert _git_diff_stats(tmp_path) is None

    def test_returns_none_on_empty(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.pr_description.run_git",
            return_value=(True, "  "),
        ):
            assert _git_diff_stats(tmp_path) is None
