---
spec: "009"
total: 22
completed: 4
last_session: "2026-02-11"
next_session: "Phase 1 — Ownership Consistency"
---

# Tasks — Updater Hardening

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/009-updater-hardening` from main
- [x] 0.2 Create spec 009 scaffold (spec.md, plan.md, tasks.md)
- [x] 0.3 Activate spec 009 in _active.md
- [x] 0.4 Update product-contract.md → 009

## Phase 1: Ownership Consistency [S]

- [ ] 1.1 Add `is_update_allowed(path: str) -> bool` to `OwnershipMap` in `state/models.py` — only `ALLOW` returns True; docstring explains distinction with `is_writable_by_framework()`
- [ ] 1.2 Replace `.claude/commands/**` with `.claude/**` in `_DEFAULT_OWNERSHIP_PATHS` in `state/defaults.py`
- [ ] 1.3 Remove `_is_update_allowed()` from `updater/service.py`; replace calls with `ownership.is_update_allowed(path)`
- [ ] 1.4 Update `_evaluate_file_change()` — consult ownership for non-existing files: explicit `deny` blocks `create`

## Phase 2: Template Trees [S]

- [ ] 2.1 Import `_PROJECT_TEMPLATE_TREES` in `updater/service.py`
- [ ] 2.2 Add template tree iteration loop in `_update_project_files()` after `_PROJECT_TEMPLATE_MAP` loop

## Phase 3: Rollback [M]

- [ ] 3.1 Refactor `_update_governance_files()` to pure evaluation — return `list[FileChange]` without writing
- [ ] 3.2 Refactor `_update_project_files()` to pure evaluation — return `list[FileChange]` without writing
- [ ] 3.3 Create `_backup_targets(changes, target) -> Path | None` — backup existing files that will be overwritten
- [ ] 3.4 Create `_restore_backup(backup_dir, target) -> None` — restore backed-up files
- [ ] 3.5 Rewrite `update()` with eval → backup → write → cleanup flow; try/except with restore on failure

## Phase 4: Diff Preview [M]

- [ ] 4.1 Add `diff: str | None = None` field to `FileChange` dataclass
- [ ] 4.2 Generate `difflib.unified_diff()` in `_evaluate_file_change()` for action `update` — UTF-8 with `errors="replace"`, truncate 50 lines
- [ ] 4.3 Add `--diff` / `-d` flag to `update_cmd()` in `cli_commands/core.py` — show diff per file
- [ ] 4.4 Add `--json` flag to `update_cmd()` — emit `UpdateResult` as structured JSON

## Phase 5: Tests [M]

- [ ] 5.1 Fix `test_denied_changes_reported` — assert specific team-managed file has action `skip-denied`
- [ ] 5.2 Add `test_create_blocked_by_deny_ownership` — deny pattern blocks file creation
- [ ] 5.3 Add `test_project_template_trees_updated` — modify `.claude/commands/` file, verify update restores it
- [ ] 5.4 Add `test_claude_settings_updated` — modify `.claude/settings.json`, verify update restores it
- [ ] 5.5 Add `test_rollback_on_write_failure` — monkeypatch write to fail, verify backup restores
- [ ] 5.6 Add `test_diff_generated_for_updates` — verify `FileChange.diff` contains unified diff headers
- [ ] 5.7 Add `test_binary_file_diff_handling` — non-UTF8 file, verify diff = `[binary file]`
- [ ] 5.8 Add `test_is_update_allowed_on_model` in `test_state.py` — unit test new method on `OwnershipMap`
- [ ] 5.9 Add E2E `test_update_applies_to_claude_tree` — install → modify → update apply → verify restored
- [ ] 5.10 Add E2E `test_update_rollback_preserves_state` — simulated partial failure → verify integrity
