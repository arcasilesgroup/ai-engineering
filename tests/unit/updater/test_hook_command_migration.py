"""spec-158 concern A — settings.json hook-command migrator.

Pins the pure planner (``plan_command_rewrites``) and the IO wrapper
(``migrate_hook_commands``): exact-shape rewrite to ``run-hook.sh``, skip
report for non-canonical commands, idempotency, dry-run vs apply, backup,
minimum-diff, and the run-hook.sh-absent guard.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.updater.hook_command_migration import (
    HookMigrationReport,
    migrate_hook_commands,
    plan_command_rewrites,
)

_PREFIX = "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/"
_RUN_HOOK = f'bash "{_PREFIX}_lib/run-hook.sh"'


def _legacy(script: str, args: str = "") -> str:
    return f'python3 "{_PREFIX}{script}"{args}'


def _settings(*commands: str) -> dict:
    """Build a minimal settings.json with one event group per command."""
    return {
        "permissions": {"allow": ["Read"], "deny": ["Bash(rm -rf /)"]},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"command": c, "timeout": 5}]} for c in commands
            ]
        },
    }


def _seed_run_hook(target: Path) -> None:
    lib = target / ".ai-engineering" / "scripts" / "hooks" / "_lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "run-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")


def _write_settings(target: Path, data: dict) -> Path:
    claude = target / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    path = claude / "settings.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Pure planner
# --------------------------------------------------------------------------


def test_planner_rewrites_exact_shape() -> None:
    rewrites, skipped = plan_command_rewrites(_settings(_legacy("observe.py")))
    assert skipped == []
    assert len(rewrites) == 1
    old, new = rewrites[0]
    assert old == _legacy("observe.py")
    assert new == f'{_RUN_HOOK} "{_PREFIX}observe.py"'


def test_planner_preserves_trailing_args() -> None:
    rewrites, _ = plan_command_rewrites(_settings(_legacy("x.py", " --flag a")))
    assert rewrites[0][1] == f'{_RUN_HOOK} "{_PREFIX}x.py" --flag a'


def test_planner_dedupes_duplicate_command() -> None:
    rewrites, _ = plan_command_rewrites(_settings(_legacy("observe.py"), _legacy("observe.py")))
    assert len(rewrites) == 1


def test_planner_skips_already_migrated() -> None:
    migrated_cmd = f'{_RUN_HOOK} "{_PREFIX}observe.py"'
    rewrites, skipped = plan_command_rewrites(_settings(migrated_cmd))
    assert rewrites == []
    assert skipped == []


def test_planner_reports_noncanonical_framework_command_as_skipped() -> None:
    weird = f'/usr/bin/python3 "{_PREFIX}observe.py"'  # absolute interpreter
    rewrites, skipped = plan_command_rewrites(_settings(weird))
    assert rewrites == []
    assert skipped == [weird]


def test_planner_ignores_non_framework_command() -> None:
    rewrites, skipped = plan_command_rewrites(_settings("echo hello"))
    assert rewrites == []
    assert skipped == []


def test_planner_handles_missing_hooks_block() -> None:
    assert plan_command_rewrites({}) == ([], [])
    assert plan_command_rewrites({"hooks": {}}) == ([], [])


# --------------------------------------------------------------------------
# IO wrapper
# --------------------------------------------------------------------------


def test_migrate_absent_settings_is_empty_report(tmp_path: Path) -> None:
    report = migrate_hook_commands(tmp_path, dry_run=False)
    assert report == HookMigrationReport()
    assert not (tmp_path / ".claude" / "settings.json").exists()


def test_migrate_runhook_absent_defers_to_skipped(tmp_path: Path) -> None:
    # AC8: with no run-hook.sh on disk, do not wire to a missing wrapper.
    _write_settings(tmp_path, _settings(_legacy("observe.py")))
    before = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    report = migrate_hook_commands(tmp_path, dry_run=False)
    assert report.migrated == []
    assert report.skipped == [_legacy("observe.py")]
    assert (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8") == before


def test_migrate_dry_run_reports_without_writing(tmp_path: Path) -> None:
    _seed_run_hook(tmp_path)
    path = _write_settings(tmp_path, _settings(_legacy("observe.py")))
    before = path.read_text(encoding="utf-8")
    report = migrate_hook_commands(tmp_path, dry_run=True)
    assert report.migrated == [_legacy("observe.py")]
    assert report.applied is False
    assert report.backup_path is None
    assert path.read_text(encoding="utf-8") == before  # untouched


def test_migrate_apply_rewrites_with_backup(tmp_path: Path) -> None:
    _seed_run_hook(tmp_path)
    path = _write_settings(tmp_path, _settings(_legacy("observe.py")))
    report = migrate_hook_commands(tmp_path, dry_run=False)
    assert report.applied is True
    assert report.migrated == [_legacy("observe.py")]
    new_data = json.loads(path.read_text(encoding="utf-8"))
    cmd = new_data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == f'{_RUN_HOOK} "{_PREFIX}observe.py"'
    # backup exists and matches the timestamped name.
    assert report.backup_path is not None and report.backup_path.is_file()
    assert report.backup_path.name.startswith("settings.json.bak-")


def test_migrate_preserves_user_keys_and_deny(tmp_path: Path) -> None:
    _seed_run_hook(tmp_path)
    data = _settings(_legacy("observe.py"))
    data["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = 17  # user-tuned
    path = _write_settings(tmp_path, data)
    migrate_hook_commands(tmp_path, dry_run=False)
    new_data = json.loads(path.read_text(encoding="utf-8"))
    assert new_data["permissions"]["deny"] == ["Bash(rm -rf /)"]
    assert new_data["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] == 17
    assert new_data["hooks"]["PreToolUse"][0]["matcher"] == "Bash"


def test_migrate_minimum_diff(tmp_path: Path) -> None:
    _seed_run_hook(tmp_path)
    path = _write_settings(tmp_path, _settings(_legacy("observe.py")))
    before = path.read_text(encoding="utf-8")
    migrate_hook_commands(tmp_path, dry_run=False)
    after = path.read_text(encoding="utf-8")
    # Only the command literal changed: replacing the new literal back with the
    # old one must reproduce the original file byte-for-byte.
    restored = after.replace(
        json.dumps(f'{_RUN_HOOK} "{_PREFIX}observe.py"'),
        json.dumps(_legacy("observe.py")),
    )
    assert restored == before


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    _seed_run_hook(tmp_path)
    _write_settings(tmp_path, _settings(_legacy("observe.py")))
    first = migrate_hook_commands(tmp_path, dry_run=False)
    assert first.migrated == [_legacy("observe.py")]
    second = migrate_hook_commands(tmp_path, dry_run=False)
    assert second.migrated == []
    assert second.applied is False


def test_migrate_skips_command_literal_embedded_in_sibling_value(tmp_path: Path) -> None:
    """Review correctness-1: a legacy command text embedded in a NON-command
    string value must not be silently rewritten; the occurrence-count guard
    skips it for manual review instead."""
    _seed_run_hook(tmp_path)
    legacy = _legacy("observe.py")
    data = _settings(legacy)
    # A sibling non-command value whose JSON encoding equals the command's
    # literal — so the raw text holds the literal twice but only one is a
    # command slot. The occurrence-count guard must refuse to rewrite.
    data["_note"] = legacy
    path = _write_settings(tmp_path, data)
    before = path.read_text(encoding="utf-8")

    report = migrate_hook_commands(tmp_path, dry_run=False)

    # Ambiguous occurrence count -> not migrated, reported skipped, file untouched.
    assert report.migrated == []
    assert legacy in report.skipped
    assert path.read_text(encoding="utf-8") == before
