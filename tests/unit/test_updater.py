"""Tests for updater/service.py — ownership-safe framework updates.

Covers:
- Dry-run mode reports changes without writing.
- Apply mode writes changes to disk.
- Ownership safety: team/project-managed paths never overwritten.
- Ownership deny blocks file creation.
- Framework-managed paths updated correctly.
- Template trees (`.claude/`) updated correctly.
- Unchanged files skipped.
- Audit logging on apply.
- Diff generation for updated files.
- Rollback on write failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.installer.service import install
from ai_engineering.updater.service import FileChange, UpdateResult, update


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Create a fully installed project."""
    install(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRun:
    """Tests for dry-run update mode."""

    def test_dry_run_reports_changes(self, installed_project: Path) -> None:
        result = update(installed_project, dry_run=True)
        assert result.dry_run is True
        assert len(result.changes) > 0

    def test_dry_run_does_not_modify_files(self, installed_project: Path) -> None:
        # Modify a framework-managed file to create a diff
        core_md = installed_project / ".ai-engineering" / "standards" / "framework" / "core.md"
        core_md.read_text()
        core_md.write_text("modified content")

        result = update(installed_project, dry_run=True)

        # File should still be modified (dry-run doesn't change)
        assert core_md.read_text() == "modified content"
        assert result.applied_count > 0  # Would have applied changes

    def test_dry_run_no_audit_log(self, installed_project: Path) -> None:
        audit_path = installed_project / ".ai-engineering" / "state" / "audit-log.ndjson"
        lines_before = _count_lines(audit_path)

        update(installed_project, dry_run=True)

        lines_after = _count_lines(audit_path)
        # The install already created 1 audit entry; dry-run should add nothing
        assert lines_after == lines_before


# ---------------------------------------------------------------------------
# Apply mode
# ---------------------------------------------------------------------------


class TestApply:
    """Tests for apply update mode."""

    def test_applies_changes(self, installed_project: Path) -> None:
        # Modify a framework-managed file
        core_md = installed_project / ".ai-engineering" / "standards" / "framework" / "core.md"
        core_md.write_text("outdated content")

        result = update(installed_project, dry_run=False)

        assert result.dry_run is False
        # File should be restored from template
        assert core_md.read_text() != "outdated content"

    def test_apply_logs_audit_entry(self, installed_project: Path) -> None:
        # Create a diff to trigger an update
        core_md = installed_project / ".ai-engineering" / "standards" / "framework" / "core.md"
        core_md.write_text("outdated")

        audit_path = installed_project / ".ai-engineering" / "state" / "audit-log.ndjson"
        lines_before = _count_lines(audit_path)

        update(installed_project, dry_run=False)

        lines_after = _count_lines(audit_path)
        assert lines_after > lines_before

        last_line = audit_path.read_text().strip().splitlines()[-1]
        entry = json.loads(last_line)
        assert entry["event"] == "update"


# ---------------------------------------------------------------------------
# Ownership safety
# ---------------------------------------------------------------------------


class TestOwnershipSafety:
    """Tests that team/project-managed paths are never modified."""

    def test_team_managed_path_not_overwritten(self, installed_project: Path) -> None:
        team_core = installed_project / ".ai-engineering" / "standards" / "team" / "core.md"
        team_core.write_text("custom team content")

        update(installed_project, dry_run=False)

        assert team_core.read_text() == "custom team content"

    def test_context_path_not_overwritten(self, installed_project: Path) -> None:
        context_file = (
            installed_project / ".ai-engineering" / "context" / "product" / "framework-contract.md"
        )
        if context_file.exists():
            context_file.write_text("custom project content")
            update(installed_project, dry_run=False)
            assert context_file.read_text() == "custom project content"

    def test_denied_changes_reported(self, installed_project: Path) -> None:
        # Modify a team-managed file that exists in templates
        team_core = installed_project / ".ai-engineering" / "standards" / "team" / "core.md"
        team_core.write_text("custom team content")

        result = update(installed_project, dry_run=True)

        # Find the specific team-managed file in the change list
        denied = [
            c
            for c in result.changes
            if c.action == "skip-denied" and "standards" in str(c.path) and "team" in str(c.path)
        ]
        assert len(denied) >= 1, "Expected at least one denied team-managed change"

    def test_create_blocked_by_deny_ownership(self, installed_project: Path) -> None:
        """An explicit deny pattern prevents creation of a new file."""
        # Delete a context file (project-managed → deny) that exists in templates
        context_file = (
            installed_project / ".ai-engineering" / "context" / "product" / "framework-contract.md"
        )
        if context_file.exists():
            context_file.unlink()

            result = update(installed_project, dry_run=True)

            # The file should be reported as skip-denied even though it doesn't exist,
            # because the ownership pattern denies creation on context/** paths
            match = next(
                (c for c in result.changes if c.path == context_file),
                None,
            )
            assert match is not None, "Expected context file in changes"
            assert match.action == "skip-denied"


# ---------------------------------------------------------------------------
# Template trees (.claude/)
# ---------------------------------------------------------------------------


class TestTemplateTrees:
    """Tests that _PROJECT_TEMPLATE_TREES files are processed by the updater."""

    def test_project_template_trees_updated(self, installed_project: Path) -> None:
        """Modify a .claude/commands/ file and verify update restores it."""
        commit_md = installed_project / ".claude" / "commands" / "commit.md"
        if not commit_md.exists():
            pytest.skip("commit.md not found in installed project")

        original = commit_md.read_bytes()
        commit_md.write_text("modified command")

        result = update(installed_project, dry_run=False)

        assert commit_md.read_bytes() == original
        updated = [c for c in result.changes if c.path == commit_md and c.action == "update"]
        assert len(updated) == 1

    def test_claude_settings_updated(self, installed_project: Path) -> None:
        """Modify .claude/settings.json and verify update restores it."""
        settings = installed_project / ".claude" / "settings.json"
        if not settings.exists():
            pytest.skip("settings.json not found in installed project")

        original = settings.read_bytes()
        settings.write_text('{"modified": true}')

        result = update(installed_project, dry_run=False)

        assert settings.read_bytes() == original
        updated = [c for c in result.changes if c.path == settings and c.action == "update"]
        assert len(updated) == 1


# ---------------------------------------------------------------------------
# Unchanged files
# ---------------------------------------------------------------------------


class TestUnchangedFiles:
    """Tests that unchanged files are skipped."""

    def test_unchanged_files_skipped(self, installed_project: Path) -> None:
        # On a fresh install, all files match templates
        result = update(installed_project, dry_run=True)
        unchanged = [c for c in result.changes if c.action == "skip-unchanged"]
        assert len(unchanged) > 0


# ---------------------------------------------------------------------------
# Diff generation
# ---------------------------------------------------------------------------


class TestDiffGeneration:
    """Tests for unified diff generation on updated files."""

    def test_diff_generated_for_updates(self, installed_project: Path) -> None:
        """Modified file should have a unified diff attached."""
        core_md = installed_project / ".ai-engineering" / "standards" / "framework" / "core.md"
        core_md.write_text("outdated content")

        result = update(installed_project, dry_run=True)

        updated = [c for c in result.changes if c.path == core_md and c.action == "update"]
        assert len(updated) == 1
        assert updated[0].diff is not None
        assert "---" in updated[0].diff
        assert "+++" in updated[0].diff

    def test_binary_file_diff_handling(self, installed_project: Path) -> None:
        """Non-UTF8 file should produce '[binary file]' diff."""
        from ai_engineering.updater.service import _generate_diff

        binary_content = b"\x80\x81\x82\xff\xfe"
        text_content = b"hello world"

        diff = _generate_diff(text_content, binary_content, "test.bin")
        assert diff == "[binary file]"


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


class TestRollback:
    """Tests for backup/restore on write failure."""

    def test_rollback_on_write_failure(self, installed_project: Path) -> None:
        """If a write fails mid-apply, already-modified files are restored."""
        # Modify two framework-managed files
        core_md = installed_project / ".ai-engineering" / "standards" / "framework" / "core.md"
        core_md.write_text("will be restored")

        original_write = Path.write_bytes
        call_count = 0

        def failing_write(self_path: Path, data: bytes) -> int:
            nonlocal call_count
            call_count += 1
            # Let the first write succeed, fail on a subsequent one
            if call_count >= 2:
                msg = "Simulated write failure"
                raise OSError(msg)
            return original_write(self_path, data)

        with patch.object(Path, "write_bytes", failing_write), pytest.raises(OSError, match="Simulated"):
            update(installed_project, dry_run=False)

        # The file that was already written should be restored from backup
        # (the one that was modified should be back to "will be restored"
        # since the backup contained the pre-modify state)
        assert core_md.read_text() == "will be restored"


# ---------------------------------------------------------------------------
# UpdateResult
# ---------------------------------------------------------------------------


class TestUpdateResult:
    """Tests for UpdateResult dataclass."""

    def test_applied_count(self) -> None:
        result = UpdateResult(
            dry_run=True,
            changes=[
                FileChange(path=Path("a"), action="create"),
                FileChange(path=Path("b"), action="update"),
                FileChange(path=Path("c"), action="skip-denied"),
                FileChange(path=Path("d"), action="skip-unchanged"),
            ],
        )
        assert result.applied_count == 2

    def test_denied_count(self) -> None:
        result = UpdateResult(
            dry_run=True,
            changes=[
                FileChange(path=Path("a"), action="skip-denied"),
                FileChange(path=Path("b"), action="skip-denied"),
                FileChange(path=Path("c"), action="create"),
            ],
        )
        assert result.denied_count == 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_lines(path: Path) -> int:
    """Count non-empty lines in a file."""
    if not path.exists():
        return 0
    return len([line for line in path.read_text().strip().splitlines() if line.strip()])
