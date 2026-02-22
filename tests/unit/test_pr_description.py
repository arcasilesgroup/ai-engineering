"""Unit tests for VCS PR description builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.vcs.pr_description import (
    _humanize_branch,
    _read_active_spec,
    _recent_commit_subjects,
    build_pr_description,
    build_pr_title,
)

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
