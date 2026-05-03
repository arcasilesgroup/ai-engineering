"""Unit tests for work-item sync service and PR description issue linking."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_engineering.state.models import TaskLedger, TaskLedgerTask, TaskLifecycleState
from ai_engineering.state.work_plane import write_task_ledger
from ai_engineering.vcs.protocol import VcsResult
from ai_engineering.work_items.service import (
    SyncReport,
    get_hierarchy_rules,
    get_linked_issue_id,
    resolve_closeable_refs,
    sync_spec_issues,
)


def _make_spec_dir(root: Path, spec_id: str, *, done: bool = False, spec_text: str = "") -> Path:
    """Create a minimal spec directory structure."""
    spec_dir = root / ".ai-engineering" / "specs" / spec_id
    spec_dir.mkdir(parents=True, exist_ok=True)
    if spec_text:
        (spec_dir / "spec.md").write_text(spec_text, encoding="utf-8")
    if done:
        (spec_dir / "done.md").write_text("Done.", encoding="utf-8")
    return spec_dir


def _mock_provider(
    *,
    find_output: str = "",
    find_success: bool = True,
    create_success: bool = True,
    close_success: bool = True,
) -> MagicMock:
    """Build a mock VCS provider with configurable issue methods."""
    provider = MagicMock()
    provider.find_issue.return_value = VcsResult(success=find_success, output=find_output)
    provider.create_issue.return_value = VcsResult(
        success=create_success, output="42" if create_success else "error"
    )
    provider.close_issue.return_value = VcsResult(
        success=close_success, output="closed" if close_success else "error"
    )
    provider.provider_name.return_value = "github"
    return provider


# ── sync_spec_issues ─────────────────────────────────────────────


class TestSyncSpecIssues:
    """Tests for sync_spec_issues."""

    def test_creates_when_not_found(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync", spec_text="# Spec 037 — Sync\n## Problem\nNeed sync.")
        provider = _mock_provider(find_output="")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert "037-sync" in report.created
        provider.create_issue.assert_called_once()

    def test_skips_when_exists(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync")
        provider = _mock_provider(find_output="42")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert "037-sync" in report.found
        provider.create_issue.assert_not_called()

    def test_closes_when_done_md(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync", done=True)
        provider = _mock_provider(find_output="42")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert "037-sync" in report.closed
        provider.close_issue.assert_called_once()

    def test_dry_run_no_writes(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync")
        _make_spec_dir(tmp_path, "038-other", done=True)
        provider = _mock_provider(find_output="")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path, dry_run=True)

        # Assert — should report what would happen but not call provider write methods
        assert len(report.created) == 2
        provider.create_issue.assert_not_called()
        provider.close_issue.assert_not_called()

    def test_handles_find_error(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync")
        provider = _mock_provider(find_success=False)
        provider.find_issue.return_value = VcsResult(success=False, output="auth failed")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert len(report.errors) == 1
        assert "037-sync" in report.errors[0]

    def test_returns_empty_when_specs_dir_missing(self, tmp_path: Path) -> None:
        # Arrange
        provider = _mock_provider()

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert report == SyncReport()
        provider.find_issue.assert_not_called()

    def test_close_issue_error(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync", done=True)
        provider = _mock_provider(find_output="42", close_success=False)
        provider.close_issue.return_value = VcsResult(success=False, output="auth failed")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert len(report.errors) == 1
        assert "close failed" in report.errors[0]

    def test_create_issue_error(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync")
        provider = _mock_provider(find_output="", create_success=False)
        provider.create_issue.return_value = VcsResult(success=False, output="rate limited")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        assert len(report.errors) == 1
        assert "create failed" in report.errors[0]

    def test_dry_run_closes_existing_done(self, tmp_path: Path) -> None:
        # Arrange
        _make_spec_dir(tmp_path, "037-sync", done=True)
        provider = _mock_provider(find_output="42")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path, dry_run=True)

        # Assert
        assert "037-sync" in report.closed
        provider.close_issue.assert_not_called()

    def test_parse_spec_oserror(self, tmp_path: Path) -> None:
        # Arrange
        from ai_engineering.work_items.service import _parse_spec_for_issue

        spec_md = tmp_path / "spec.md"
        spec_md.write_text("content", encoding="utf-8")

        # Act
        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            title, body = _parse_spec_for_issue(spec_md, "037")

        # Assert
        assert "spec-037" in title
        assert body == ""

    def test_skips_archive_and_special_files(self, tmp_path: Path) -> None:
        # Arrange
        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "_history.md").write_text("# History", encoding="utf-8")
        (specs_dir / "spec.md").write_text("# No active spec", encoding="utf-8")
        (specs_dir / "plan.md").write_text("# No active plan", encoding="utf-8")
        archive_dir = specs_dir / "archive"
        archive_dir.mkdir()
        (archive_dir / "spec.md").write_text("# Old spec", encoding="utf-8")
        provider = _mock_provider()

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        # Assert
        provider.find_issue.assert_not_called()
        assert report == SyncReport()

    def test_uses_resolved_work_plane_specs_dir(self, tmp_path: Path, monkeypatch) -> None:
        resolved_specs_dir = tmp_path / "resolved-work-plane"
        resolved_specs_dir.mkdir(parents=True)
        pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(
            json.dumps({"specsDir": "resolved-work-plane"}),
            encoding="utf-8",
        )
        (resolved_specs_dir / "_history.md").write_text("# History", encoding="utf-8")
        spec_dir = resolved_specs_dir / "037-sync"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text(
            "# Spec 037 — Sync\n\n## Problem\n\nNeed sync.",
            encoding="utf-8",
        )

        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "037-sync" in report.created
        provider.create_issue.assert_called_once()

    def test_syncs_when_resolved_work_plane_is_the_active_spec_root(self, tmp_path: Path) -> None:
        resolved_specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
        resolved_specs_dir.mkdir(parents=True)
        pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(
            json.dumps({"specsDir": ".ai-engineering/specs/spec-117-hx-02"}),
            encoding="utf-8",
        )
        (resolved_specs_dir / "spec.md").write_text(
            "# Spec 117 — Work Plane and Task Ledger\n\n## Problem\n\nNeed activation-aware sync.",
            encoding="utf-8",
        )

        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "117-hx-02" in report.created
        provider.create_issue.assert_called_once()
        issue_ctx = provider.find_issue.call_args.args[0]
        assert issue_ctx.spec_id == "117-hx-02"
        assert issue_ctx.labels == ("spec-117-hx-02",)

    def test_syncs_legacy_active_spec_root_from_declared_spec_id(self, tmp_path: Path) -> None:
        specs_dir = tmp_path / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            '---\nid: "117-hx-02"\n---\n\n# Spec 117 — Work Plane\n',
            encoding="utf-8",
        )

        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "117-hx-02" in report.created
        issue_ctx = provider.find_issue.call_args.args[0]
        assert issue_ctx.spec_id == "117-hx-02"
        assert issue_ctx.labels == ("spec-117-hx-02",)

    def test_syncs_placeholder_active_spec_root_when_resolved_ledger_has_live_task(
        self,
        tmp_path: Path,
    ) -> None:
        resolved_specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
        resolved_specs_dir.mkdir(parents=True)
        pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(
            json.dumps({"specsDir": ".ai-engineering/specs/spec-117-hx-02"}),
            encoding="utf-8",
        )
        (resolved_specs_dir / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
            encoding="utf-8",
        )
        write_task_ledger(
            tmp_path,
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="HX-02-T-5.1-work-items-ledger-aware-active-spec-dir",
                        title="Cut work-item sync over to the resolved ledger",
                        ownerRole="Build",
                        status=TaskLifecycleState.IN_PROGRESS,
                        writeScope=["src/ai_engineering/work_items/service.py"],
                    )
                ]
            ),
        )

        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "117-hx-02" in report.created
        provider.create_issue.assert_called_once()

    def test_placeholder_active_spec_root_with_done_resolved_ledger_stays_idle(
        self,
        tmp_path: Path,
    ) -> None:
        resolved_specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
        resolved_specs_dir.mkdir(parents=True)
        pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(
            json.dumps({"specsDir": ".ai-engineering/specs/spec-117-hx-02"}),
            encoding="utf-8",
        )
        (resolved_specs_dir / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
            encoding="utf-8",
        )
        write_task_ledger(
            tmp_path,
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="HX-02-T-5.1-work-items-ledger-aware-active-spec-dir",
                        title="Cut work-item sync over to the resolved ledger",
                        ownerRole="Build",
                        status=TaskLifecycleState.DONE,
                        writeScope=["src/ai_engineering/work_items/service.py"],
                    )
                ]
            ),
        )

        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert report == SyncReport()
        provider.find_issue.assert_not_called()

    def test_placeholder_active_spec_root_with_unreadable_resolved_ledger_stays_idle(
        self,
        tmp_path: Path,
    ) -> None:
        resolved_specs_dir = tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02"
        resolved_specs_dir.mkdir(parents=True)
        pointer_path = tmp_path / ".ai-engineering" / "specs" / "active-work-plane.json"
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(
            json.dumps({"specsDir": ".ai-engineering/specs/spec-117-hx-02"}),
            encoding="utf-8",
        )
        (resolved_specs_dir / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
            encoding="utf-8",
        )
        (resolved_specs_dir / "task-ledger.json").write_text("{not-json", encoding="utf-8")

        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert report == SyncReport()
        provider.find_issue.assert_not_called()


# ── get_linked_issue_id ──────────────────────────────────────────


class TestGetLinkedIssueId:
    """Tests for get_linked_issue_id."""

    def test_returns_number(self, tmp_path: Path) -> None:
        # Arrange
        provider = _mock_provider(find_output="42")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            result = get_linked_issue_id(tmp_path, "037-sync")

        # Assert
        assert result == "42"

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        # Arrange
        provider = _mock_provider(find_output="")

        # Act
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            result = get_linked_issue_id(tmp_path, "037-sync")

        # Assert
        assert result is None


# ── PR description issue linking ─────────────────────────────────


class TestPrDescriptionIssueLink:
    """Tests for _build_issue_reference in pr_description module."""

    def test_github_closes_keyword(self, tmp_path: Path) -> None:
        from ai_engineering.vcs.pr_description import _build_issue_reference

        # Act
        with (
            patch(
                "ai_engineering.work_items.service.get_provider",
                return_value=_mock_provider(find_output="7"),
            ),
            patch(
                "ai_engineering.vcs.factory.detect_from_remote",
                return_value="github",
            ),
        ):
            result = _build_issue_reference(tmp_path, "037-sync")

        # Assert
        assert result == "Closes #7"

    def test_azure_ab_keyword(self, tmp_path: Path) -> None:
        from ai_engineering.vcs.pr_description import _build_issue_reference

        # Act
        with (
            patch(
                "ai_engineering.work_items.service.get_provider",
                return_value=_mock_provider(find_output="101"),
            ),
            patch(
                "ai_engineering.vcs.factory.detect_from_remote",
                return_value="azure_devops",
            ),
        ):
            result = _build_issue_reference(tmp_path, "037-sync")

        # Assert
        assert result == "AB#101"

    def test_no_issue_returns_none(self, tmp_path: Path) -> None:
        from ai_engineering.vcs.pr_description import _build_issue_reference

        # Act
        with patch(
            "ai_engineering.work_items.service.get_provider",
            return_value=_mock_provider(find_output=""),
        ):
            result = _build_issue_reference(tmp_path, "037-sync")

        # Assert
        assert result is None


# ---------------------------------------------------------------
# Hierarchy rules + closeable refs
# ---------------------------------------------------------------


class TestGetHierarchyRules:
    """Tests for get_hierarchy_rules()."""

    def test_returns_defaults_when_no_manifest(self, tmp_path: Path) -> None:
        rules = get_hierarchy_rules(tmp_path)
        assert rules["feature"] == "never_close"
        assert rules["task"] == "close_on_pr"

    def test_reads_hierarchy_from_manifest(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            "work_items:\n"
            "  hierarchy:\n"
            "    feature: never_close\n"
            "    user_story: close_on_pr\n"
            "    task: close_on_pr\n"
            "    bug: close_on_pr\n"
        )
        rules = get_hierarchy_rules(tmp_path)
        assert rules["feature"] == "never_close"
        assert rules["bug"] == "close_on_pr"

    def test_returns_defaults_on_malformed_yaml(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(": invalid yaml [[[")
        rules = get_hierarchy_rules(tmp_path)
        assert "feature" in rules

    def test_returns_defaults_when_no_work_items(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("name: test\n")
        rules = get_hierarchy_rules(tmp_path)
        assert rules["feature"] == "never_close"

    def test_returns_defaults_when_no_hierarchy(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("work_items:\n  provider: github\n")
        rules = get_hierarchy_rules(tmp_path)
        assert rules["feature"] == "never_close"

    def test_merges_custom_over_defaults(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("work_items:\n  hierarchy:\n    custom_type: track_only\n")
        rules = get_hierarchy_rules(tmp_path)
        assert rules["custom_type"] == "track_only"
        assert rules["feature"] == "never_close"


class TestResolveCloseableRefs:
    """Tests for resolve_closeable_refs()."""

    def test_features_never_closed(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            "work_items:\n  hierarchy:\n    feature: never_close\n    task: close_on_pr\n"
        )
        refs = {"features": ["AB#100"], "tasks": ["AB#101", "AB#102"]}
        closeable, mention_only = resolve_closeable_refs(tmp_path, refs)
        assert "AB#100" in mention_only
        assert "AB#101" in closeable
        assert "AB#102" in closeable

    def test_empty_refs(self, tmp_path: Path) -> None:
        closeable, mention_only = resolve_closeable_refs(tmp_path, {})
        assert closeable == []
        assert mention_only == []

    def test_unknown_category_ignored(self, tmp_path: Path) -> None:
        refs = {"unknowns": ["X#1"]}
        closeable, mention_only = resolve_closeable_refs(tmp_path, refs)
        assert closeable == []
        assert mention_only == []

    def test_issues_closeable_by_default(self, tmp_path: Path) -> None:
        refs = {"issues": ["#45", "#46"]}
        closeable, mention_only = resolve_closeable_refs(tmp_path, refs)
        assert "#45" in closeable
        assert "#46" in closeable
        assert mention_only == []
