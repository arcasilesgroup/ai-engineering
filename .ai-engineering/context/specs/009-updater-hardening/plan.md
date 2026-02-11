---
spec: "009"
phases: 5
sessions: 1
---

# Plan — Updater Hardening

## Architecture

This spec hardens the updater service with rollback safety, diff preview, ownership consolidation, template tree support, and test hardening. Changes span the updater, state models, state defaults, CLI commands, and test suites.

### Modified Files

| File | Action | Purpose |
|------|--------|---------|
| `src/ai_engineering/updater/service.py` | EDIT | Rollback, eval/exec split, diff generation, template trees, remove `_is_update_allowed` |
| `src/ai_engineering/state/models.py` | EDIT | Add `OwnershipMap.is_update_allowed()` |
| `src/ai_engineering/state/defaults.py` | EDIT | Replace `.claude/commands/**` with `.claude/**` |
| `src/ai_engineering/cli_commands/core.py` | EDIT | `--diff` and `--json` flags in `update_cmd` |
| `tests/unit/test_updater.py` | EDIT | 8 new tests, strengthen existing assertions |
| `tests/unit/test_state.py` | EDIT | Test `is_update_allowed()` on model |
| `tests/e2e/test_install_existing.py` | EDIT | 2 new E2E tests |

### New Files

None. All changes modify existing files.

## Dependency Graph

```text
Phase 1 (Ownership) ─┐
                      ├── Phase 3 (Rollback) ── Phase 4 (Diff) ── Phase 5 (Tests)
Phase 2 (Trees) ──────┘
```

Phases 1 and 2 are independent and can be implemented in either order. Phase 3 depends on both (refactors `update()` which consumes ownership and trees). Phase 4 extends Phase 3's `FileChange`. Phase 5 tests everything.

## Session Map

| Phase | Size | Files Touched | Dependencies |
|-------|------|---------------|-------------|
| 0 — Scaffold | S | spec.md, plan.md, tasks.md, _active.md | — |
| 1 — Ownership | S | models.py, defaults.py, service.py | — |
| 2 — Template Trees | S | service.py | — |
| 3 — Rollback | M | service.py | 1, 2 |
| 4 — Diff Preview | M | service.py, core.py | 3 |
| 5 — Tests | M | test_updater.py, test_state.py, test_install_existing.py | 1, 2, 3, 4 |

## Patterns

- **Eval-then-execute**: `_update_governance_files()` and `_update_project_files()` become pure evaluation functions returning `list[FileChange]`. All writes happen in `update()` after backup.
- **Backup via tempdir**: `tempfile.mkdtemp(prefix="ai-eng-backup-")` copies existing files before overwrite. On failure, restore and re-raise. On success, `shutil.rmtree()`.
- **Diff generation**: `difflib.unified_diff()` with UTF-8 decode (`errors="replace"`). Truncated to 50 lines in CLI; full in JSON output.
- **Ownership delegation**: updater calls `ownership.is_update_allowed(path)` instead of implementing its own fnmatch loop.
- **Conservative create policy**: new files with an explicit `deny` ownership pattern are blocked. No-match + not-exists = create (same as current behaviour for unmatched paths, but inverted from current deny-by-default for existing files).
