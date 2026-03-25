---
id: spec-075
title: "Missing Test Coverage: VCS CLI, Stack Operations, Install Pipeline"
status: approved
created: 2026-03-25
refs: []
---

# spec-075: Missing Test Coverage: VCS CLI, Stack Operations, Install Pipeline

## Problem

The CLI audit (spec-073) identified 3 areas with zero or insufficient test coverage:

1. **`vcs` CLI commands** — `vcs_status` and `vcs_set_primary` have zero CLI-level tests. The VCS providers and factory are tested, but the CLI layer (output formatting, error handling, JSON mode) is not.

2. **`stack` operations** — `add_stack()` and `remove_stack()` in `operations.py` have zero unit tests. They are only tested indirectly through install integration tests.

3. **`install_with_pipeline()` e2e** — The e2e tests in `tests/e2e/` call the legacy `install()` function, not the new `install_with_pipeline()` pipeline path (introduced in spec-064). If `_summary_to_install_result()` has a bug, e2e tests don't catch it.

## Solution

Write focused tests for each gap. No production code changes — tests only.

### Group 1: VCS CLI Tests

New test file `tests/unit/test_vcs_cmd.py` covering:
- `vcs_status` — shows provider name and availability
- `vcs_status` — JSON mode output
- `vcs_status` — error when framework not installed
- `vcs_set_primary` — writes to manifest
- `vcs_set_primary` — rejects invalid provider
- `vcs_set_primary` — JSON mode output
- `vcs_set_primary` — alias `azdo` resolves to `azure_devops`

### Group 2: Stack Operation Tests

New test file `tests/unit/test_stack_operations.py` covering:
- `add_stack` — adds to manifest, returns updated config
- `add_stack` — rejects unknown stack (not in available stacks)
- `add_stack` — duplicate detection (already present)
- `remove_stack` — removes from manifest
- `remove_stack` — rejects stack not present
- `list_status` — returns current stacks from manifest

### Group 3: Install Pipeline E2E Tests

New tests in existing `tests/e2e/test_install_clean.py` or new file `tests/e2e/test_install_pipeline.py` covering:
- `install_with_pipeline()` on clean directory — produces valid InstallResult
- `install_with_pipeline()` with `dry_run=True` — no files written
- `install_with_pipeline()` on existing installation — detects REPAIR mode
- Verify `_summary_to_install_result()` maps pipeline summary correctly

## Scope

### In Scope

1. Create `tests/unit/test_vcs_cmd.py` — 7 VCS CLI tests
2. Create `tests/unit/test_stack_operations.py` — 6 stack operation tests
3. Create or extend e2e tests for `install_with_pipeline()` — 4 pipeline tests
4. All tests must pass with current production code (no code changes needed)

### Out of Scope

- Modifying any production source code
- Adding tests for `ide` command (spec-074 changed the model, tests would be premature)
- Changing existing test files
- Test coverage for commands not flagged in the audit

## Acceptance Criteria

- [ ] AC1: `tests/unit/test_vcs_cmd.py` exists with >= 7 tests
- [ ] AC2: `tests/unit/test_stack_operations.py` exists with >= 6 tests
- [ ] AC3: E2E tests for `install_with_pipeline()` exist with >= 3 tests
- [ ] AC4: All new tests pass (`pytest tests/unit/test_vcs_cmd.py tests/unit/test_stack_operations.py -v`)
- [ ] AC5: All existing tests still pass (`pytest tests/unit/ -x`)
- [ ] AC6: `ruff check tests/` passes
- [ ] AC7: No production code modified (only test files created/modified)

## Files Modified

| File | Change |
|------|--------|
| `tests/unit/test_vcs_cmd.py` | CREATE — VCS CLI tests |
| `tests/unit/test_stack_operations.py` | CREATE — stack operation tests |
| `tests/e2e/test_install_pipeline.py` | CREATE — install pipeline e2e tests |

## Risks

| Risk | Mitigation |
|------|-----------|
| Tests discover bugs in production code | Document findings but do NOT fix — out of scope for this spec |
| E2e install tests are slow | Use `tmp_path` fixtures, mock network calls |
| VCS tests need manifest fixture | Create minimal fixture with `providers.vcs` set |
