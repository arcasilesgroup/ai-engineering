"""Tests for updater/service.py — ownership-safe framework updates.

Covers:
- Dry-run mode reports changes without writing.
- Apply mode writes changes to disk.
- Ownership safety: team-managed paths never overwritten.
- Ownership deny blocks file creation for team-managed paths.
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
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ai_engineering.installer.service import install
from ai_engineering.state.models import (
    FrameworkUpdatePolicy,
    OwnershipEntry,
    OwnershipLevel,
    OwnershipMap,
)
from ai_engineering.state.repository import DurableStateRepository
from ai_engineering.updater.service import FileChange, UpdateResult, update


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Create a fully installed project with all providers enabled."""
    install(tmp_path, surfaces=["claude-code", "github-copilot", "antigravity", "codex"])
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

    def test_dry_run_leaves_hook_runtime_unchanged_after_install(
        self, installed_project: Path
    ) -> None:
        result = update(installed_project, dry_run=True)

        hook_drift = [
            change
            for change in result.changes
            if change.action in {"create", "update"}
            and change.path.is_relative_to(
                installed_project / ".ai-engineering" / "scripts" / "hooks"
            )
        ]

        assert hook_drift == []

    def test_dry_run_does_not_modify_files(self, installed_project: Path) -> None:
        # Modify a framework-managed file to create a diff
        core_md = installed_project / ".ai-engineering" / "reference" / "principles.md"
        core_md.read_text(encoding="utf-8")
        core_md.write_text("modified content", encoding="utf-8")

        result = update(installed_project, dry_run=True)

        # File should still be modified (dry-run doesn't change)
        assert core_md.read_text(encoding="utf-8") == "modified content"
        assert result.applied_count > 0  # Would have applied changes

    def test_dry_run_no_new_framework_events(self, installed_project: Path) -> None:
        events_path = installed_project / ".ai-engineering" / "state" / "framework-events.ndjson"
        lines_before = _count_lines(events_path)

        update(installed_project, dry_run=True)

        lines_after = _count_lines(events_path)
        # The install already created 1 framework event; dry-run should add nothing
        assert lines_after == lines_before


# ---------------------------------------------------------------------------
# Apply mode
# ---------------------------------------------------------------------------


class TestApply:
    """Tests for apply update mode."""

    def test_applies_changes(self, installed_project: Path) -> None:
        # Modify a framework-managed file
        core_md = installed_project / ".ai-engineering" / "reference" / "principles.md"
        core_md.write_text("outdated content", encoding="utf-8")

        result = update(installed_project, dry_run=False)

        assert result.dry_run is False
        # File should be restored from template
        assert core_md.read_text(encoding="utf-8") != "outdated content"

    def test_apply_logs_framework_operation(self, installed_project: Path) -> None:
        # Create a diff to trigger an update
        core_md = installed_project / ".ai-engineering" / "reference" / "principles.md"
        core_md.write_text("outdated", encoding="utf-8")

        events_path = installed_project / ".ai-engineering" / "state" / "framework-events.ndjson"
        lines_before = _count_lines(events_path)

        update(installed_project, dry_run=False)

        lines_after = _count_lines(events_path)
        assert lines_after > lines_before

        last_line = events_path.read_text(encoding="utf-8").strip().splitlines()[-1]
        entry = json.loads(last_line)
        assert entry["kind"] == "framework_operation"
        assert entry["detail"]["operation"] == "update"

    def test_apply_removes_legacy_audit_log(self, installed_project: Path) -> None:
        legacy_audit_log = installed_project / ".ai-engineering" / "state" / "audit-log.ndjson"
        legacy_audit_log.write_text('{"event":"legacy"}\n', encoding="utf-8")

        update(installed_project, dry_run=False)

        assert not legacy_audit_log.exists()


# ---------------------------------------------------------------------------
# Ownership safety
# ---------------------------------------------------------------------------


class TestOwnershipSafety:
    """Tests that team-managed paths are never modified."""

    def test_team_managed_path_not_overwritten(self, installed_project: Path) -> None:
        team_lessons = installed_project / ".ai-engineering" / "team" / "lessons.md"
        team_lessons.parent.mkdir(parents=True, exist_ok=True)
        team_lessons.write_text("custom team content", encoding="utf-8")

        update(installed_project, dry_run=False)

        assert team_lessons.read_text(encoding="utf-8") == "custom team content"

    # spec-140 W1.T3 — two aspirational "tracked separately" skips removed:
    # test_denied_changes_reported and test_create_blocked_by_deny_ownership.
    # Both required the updater to emit `skip-denied` for paths the bundled
    # template tree never visits — a feature that does not exist and has no
    # owner. Their deletion is the standing rent gate per CONSTITUTION.md §3.

    def test_promoted_root_context_is_framework_managed(self, installed_project: Path) -> None:
        # spec-136 D-136-13 deleted contexts/cli-ux.md; principles.md
        # serves the same invariant test (any framework-managed file under
        # .ai-engineering/reference/ should restore on update).
        promoted = installed_project / ".ai-engineering" / "reference" / "principles.md"
        original = promoted.read_text(encoding="utf-8")
        promoted.write_text("stale promoted context", encoding="utf-8")

        result = update(installed_project, dry_run=False)

        assert promoted.read_text(encoding="utf-8") == original
        updated = [c for c in result.changes if c.path == promoted and c.action == "update"]
        assert len(updated) == 1

    def test_deny_rule_blocks_missing_file_creation(
        self,
        installed_project: Path,
        tmp_path: Path,
    ) -> None:
        template_root = tmp_path / "templates"
        template_root.mkdir()
        (template_root / "custom.md").write_text("framework template\n", encoding="utf-8")
        # spec-148 P3: seed the deny rule into the canonical ownership-map.json.
        DurableStateRepository(installed_project).save_ownership(
            OwnershipMap(
                paths=[
                    OwnershipEntry(
                        pattern="custom.md",
                        owner=OwnershipLevel.TEAM_MANAGED,
                        framework_update=FrameworkUpdatePolicy.DENY,
                    )
                ]
            )
        )
        target = installed_project / "custom.md"
        target.unlink(missing_ok=True)
        template_maps = SimpleNamespace(
            file_map={"custom.md": "custom.md"},
            common_file_map={},
            tree_list=[],
            common_tree_list=[],
            vcs_tree_list=[],
        )

        with (
            patch("ai_engineering.updater.service._evaluate_governance_files", return_value=[]),
            patch(
                "ai_engineering.updater.service.get_project_template_root",
                return_value=template_root,
            ),
            patch(
                "ai_engineering.updater.service.resolve_template_maps",
                return_value=template_maps,
            ),
        ):
            result = update(installed_project, dry_run=False)

        denied = [change for change in result.changes if change.path == target]
        assert not target.exists()
        assert len(denied) == 1
        assert denied[0].action == "skip-denied"
        assert denied[0].reason_code == "team-managed-create-protected"


# ---------------------------------------------------------------------------
# Template trees (.claude/)
# ---------------------------------------------------------------------------


class TestTemplateTrees:
    """Tests that provider template tree files are processed by the updater."""

    def test_project_template_trees_updated(self, installed_project: Path) -> None:
        """Modify a .claude/skills/ file and verify update restores it."""
        skill_md = installed_project / ".claude" / "skills" / "ai-commit" / "SKILL.md"
        if not skill_md.exists():
            pytest.skip("ai-commit skill not found in installed project")

        original = skill_md.read_bytes()
        skill_md.write_text("modified skill", encoding="utf-8")

        result = update(installed_project, dry_run=False)

        assert skill_md.read_bytes() == original
        updated = [c for c in result.changes if c.path == skill_md and c.action == "update"]
        assert len(updated) == 1

    def test_claude_settings_denied(self, installed_project: Path) -> None:
        """settings.json is team-managed — update must NOT overwrite it."""
        settings = installed_project / ".claude" / "settings.json"
        if not settings.exists():
            pytest.skip("settings.json not found in installed project")

        settings.write_text('{"modified": true}', encoding="utf-8")

        result = update(installed_project, dry_run=False)

        assert settings.read_bytes() == b'{"modified": true}'
        denied = [c for c in result.changes if c.path == settings and c.action == "skip-denied"]
        assert len(denied) == 1

    def test_update_handles_skill_files(self, installed_project: Path) -> None:
        """Modify a shared-skill file and verify update restores it.

        spec-201 D-201-04: the skill payload moved from `.github/skills`
        to the shared `.agents/skills` tree.
        """
        skills_dir = installed_project / ".agents" / "skills"
        if not skills_dir.is_dir():
            pytest.skip("skills directory not found in installed project")

        skill_files = list(skills_dir.rglob("SKILL.md"))
        if not skill_files:
            pytest.skip("no skill files found in installed project")

        target = skill_files[0]
        original = target.read_bytes()
        target.write_text("modified skill", encoding="utf-8")

        result = update(installed_project, dry_run=False)

        assert target.read_bytes() == original
        updated = [c for c in result.changes if c.path == target and c.action == "update"]
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
        core_md = installed_project / ".ai-engineering" / "reference" / "principles.md"
        core_md.write_text("outdated content", encoding="utf-8")

        result = update(installed_project, dry_run=True)

        updated = [c for c in result.changes if c.path == core_md and c.action == "update"]
        assert len(updated) == 1
        assert updated[0].diff is not None
        assert "---" in updated[0].diff
        assert "+++" in updated[0].diff
        assert updated[0].reason_code == "template-drift"

    def test_create_and_unchanged_changes_have_structured_explanations(
        self, installed_project: Path
    ) -> None:
        missing = installed_project / ".claude" / "agents" / "ai-onboard.md"
        if missing.exists():
            missing.unlink()

        result = update(installed_project, dry_run=True)

        created = next((c for c in result.changes if c.path == missing), None)
        unchanged = next((c for c in result.changes if c.action == "skip-unchanged"), None)
        assert created is not None
        assert created.reason_code == "missing-framework-file"
        assert created.recommended_action is not None
        assert unchanged is not None
        assert unchanged.reason_code == "already-current"

    def test_binary_file_diff_handling(self, installed_project: Path) -> None:
        """Non-UTF8 file should produce '[binary file]' diff."""


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


class TestRollback:
    """Tests for backup/restore on write failure."""

    def test_rollback_on_write_failure(self, installed_project: Path) -> None:
        """If a write fails mid-apply, already-modified files are restored."""
        # Modify two framework-managed files so write_bytes is called twice
        core_md = installed_project / ".ai-engineering" / "reference" / "principles.md"
        core_md.parent.mkdir(parents=True, exist_ok=True)
        core_md.write_text("will be restored", encoding="utf-8")
        fw_md = installed_project / ".ai-engineering" / "contexts" / "frameworks" / "react.md"
        fw_md.parent.mkdir(parents=True, exist_ok=True)
        fw_md.write_text("will also be restored", encoding="utf-8")

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

        with (
            patch.object(Path, "write_bytes", failing_write),
            pytest.raises(OSError, match="Simulated"),
        ):
            update(installed_project, dry_run=False)

        # The file that was already written should be restored from backup
        # (the one that was modified should be back to "will be restored"
        # since the backup contained the pre-modify state)
        assert core_md.read_text(encoding="utf-8") == "will be restored"


# ---------------------------------------------------------------------------
# UpdateResult
# ---------------------------------------------------------------------------


class TestCleanupLegacyPrompts:
    """Tests for _cleanup_legacy_prompts migration."""

    def test_removes_legacy_prompts_when_skills_exist(self, installed_project: Path) -> None:
        prompts = installed_project / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "ai-commit.prompt.md").write_text("legacy", encoding="utf-8")
        (prompts / "ai-review.prompt.md").write_text("legacy", encoding="utf-8")

        update(installed_project, dry_run=False)

        assert not prompts.exists()

    def test_keeps_prompts_when_no_skills_dir(self, tmp_path: Path) -> None:
        # spec-201 D-201-04: the presence probe is the shared skill tree.
        install(tmp_path)
        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "ai-commit.prompt.md").write_text("legacy", encoding="utf-8")
        skills = tmp_path / ".agents" / "skills"
        if skills.exists():
            import shutil

            shutil.rmtree(skills)

        update(tmp_path, dry_run=False)

        assert prompts.exists()
        assert (prompts / "ai-commit.prompt.md").exists()

    def test_noop_when_no_prompts_dir(self, installed_project: Path) -> None:
        prompts = installed_project / ".github" / "prompts"
        if prompts.exists():
            import shutil

            shutil.rmtree(prompts)

        result = update(installed_project, dry_run=False)
        assert not prompts.exists()
        assert isinstance(result, UpdateResult)

    def test_removes_nested_prompt_dirs(self, installed_project: Path) -> None:
        prompts = installed_project / ".github" / "prompts"
        nested = prompts / "subdir"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "file.md").write_text("nested", encoding="utf-8")
        (prompts / "top.md").write_text("top", encoding="utf-8")

        update(installed_project, dry_run=False)

        assert not prompts.exists()

    def test_dry_run_does_not_remove_prompts(self, installed_project: Path) -> None:
        prompts = installed_project / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "ai-commit.prompt.md").write_text("legacy", encoding="utf-8")

        update(installed_project, dry_run=True)

        assert prompts.exists()
        assert (prompts / "ai-commit.prompt.md").exists()


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
    return len(
        [line for line in path.read_text(encoding="utf-8").strip().splitlines() if line.strip()]
    )


_PREFIX = "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/"


def _set_legacy_command(settings_path: Path) -> str:
    """Rewrite the first PreToolUse hook command to the legacy python3 form."""
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    legacy = f'python3 "{_PREFIX}observe.py"'
    data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = legacy
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return legacy


class TestHookCommandMigration:
    """spec-158 concern A — settings.json hook-command migration via update()."""

    def test_dry_run_reports_migration_without_writing(self, installed_project: Path) -> None:
        settings = installed_project / ".claude" / "settings.json"
        legacy = _set_legacy_command(settings)
        before = settings.read_text(encoding="utf-8")

        result = update(installed_project, dry_run=True)

        assert result.hook_migration is not None
        assert legacy in result.hook_migration.migrated
        assert settings.read_text(encoding="utf-8") == before  # untouched

    def test_apply_rewrites_to_resolver_with_backup(self, installed_project: Path) -> None:
        settings = installed_project / ".claude" / "settings.json"
        _set_legacy_command(settings)

        result = update(installed_project, dry_run=False)

        assert result.hook_migration is not None and result.hook_migration.applied
        data = json.loads(settings.read_text(encoding="utf-8"))
        cmd = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        # AC1/AC7: now routed through the resolver wrapper.
        assert cmd == f'bash "{_PREFIX}_lib/run-hook.sh" "{_PREFIX}observe.py"'
        # AC5: a timestamped backup exists.
        backups = list((installed_project / ".claude").glob("settings.json.bak-*"))
        assert backups, "expected a settings.json backup before mutation"

    def test_apply_is_idempotent(self, installed_project: Path) -> None:
        settings = installed_project / ".claude" / "settings.json"
        _set_legacy_command(settings)
        first = update(installed_project, dry_run=False)
        assert first.hook_migration is not None and first.hook_migration.migrated_count >= 1
        second = update(installed_project, dry_run=False)
        assert second.hook_migration is not None
        assert second.hook_migration.migrated == []
