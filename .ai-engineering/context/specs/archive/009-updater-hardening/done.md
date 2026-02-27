---
spec: "009"
completed: "2026-02-11"
branch: "feat/009-updater-hardening"
pr: "#36"
---

# Done — Updater Hardening

## Delivered

All 22/22 tasks completed and merged to main via PR #36.

### Phase 1: Ownership Consistency

- Added `OwnershipMap.is_update_allowed()` method — strict check (only `ALLOW` returns True).
- Widened `.claude/commands/**` to `.claude/**` in default ownership paths.
- Removed `_is_update_allowed()` private function from updater; delegated to model.
- `_evaluate_file_change()` now consults ownership for non-existing files (explicit deny blocks create).

### Phase 2: Template Trees

- `_PROJECT_TEMPLATE_TREES` wired into `_update_project_files()`.
- `.claude/settings.json` and command wrappers updated by `ai-eng update --apply`.

### Phase 3: Rollback

- Refactored `_update_governance_files()` and `_update_project_files()` to pure evaluation (return `list[FileChange]` without writing).
- Added `_backup_targets()` and `_restore_backup()` for transactional safety.
- Rewrote `update()` with eval -> backup -> write -> cleanup flow; try/except restores on failure.

### Phase 4: Diff Preview

- Added `diff` field to `FileChange` dataclass.
- Generated `difflib.unified_diff()` in `_evaluate_file_change()` for action `update`.
- Added `--diff` / `-d` and `--json` flags to `update_cmd()`.

### Phase 5: Tests

- 10 new tests (8 unit + 2 E2E) covering ownership, template trees, rollback, diff generation, binary files, and end-to-end flows.
- All existing tests green, no regressions.

## Decisions Recorded

| ID | Decision |
|----|----------|
| D-009-1 | `.claude/**` replaces `.claude/commands/**` in ownership defaults |
| D-009-2 | Migrations deferred to future spec |
| D-009-3 | `copy_template_tree()` not reused by updater |
| D-009-4 | Diff truncated to 50 lines in CLI, full in `--json` |
