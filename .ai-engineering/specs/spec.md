---
id: spec-069
title: "Nuclear Removal of TEST_SCOPE_RULES"
status: draft
created: 2026-03-25
refs: []
---

# spec-069: Nuclear Removal of TEST_SCOPE_RULES

## Problem

`TEST_SCOPE_RULES` is a manual test-selection system (760 LOC, 25 `ScopeRule` declarations) that maps source globs to test files. It requires manual maintenance every time a module or test is added, validated by integrity checks (`check_test_mapping.py`, `test_real_project_integrity.py`).

### Why it must go

- **Maintenance burden without payoff**: 25 rules must be manually updated for every new module. The integrity check fails if forgotten, creating friction without proportional value.
- **Precision is low**: Glob-based mappings are coarse (e.g., all of `lib/**` maps to the same 10 tests), so the system over-selects anyway.
- **Never enforced**: The system operates in `shadow` mode -- it calculates scope but CI always runs the full suite on `main`.
- **Suite is fast**: Unit tests run in 24s (1,879 tests), e2e in 50s (21 tests), integration in 5m (451 tests). Full suite is acceptable without filtering.
- **Confidence gap**: No evidence that the manual mappings reflect actual code dependencies.

## Solution

Delete `test_scope.py` and all its consumers. Simplify CI to always run the full test suite per tier. Add `paths-ignore` to CI workflows for docs-only changes.

## Scope

### In Scope

1. Delete `src/ai_engineering/policy/test_scope.py` (760 LOC)
2. Delete `scripts/check_test_mapping.py` (called from `ci.yml:485`)
3. Remove `test_test_scope_covers_all_source_files` from `tests/unit/test_real_project_integrity.py`
4. Remove any other `TEST_SCOPE_RULES`-related tests from `tests/unit/` and `tests/integration/`
4. Remove `compute_test_scope` / `resolve_scope_mode` imports and calls from `policy/gates.py`
5. Remove test-scope metrics from `lib/signals.py`
6. Remove env vars `AI_ENG_TEST_SCOPE` / `AI_ENG_TEST_SCOPE_MODE` from CI and code
7. Simplify CI workflows: replace scope-computed test args with `pytest tests/unit`, `pytest tests/integration`, `pytest tests/e2e`
8. Add `paths-ignore` to CI workflow for docs-only changes (`**.md`, `**.mdx`, `**.rst`, `**.txt`, `docs/**`)
9. Remove `ScopeRule`, `ScopeMode`, `TestTier` types if they become unused
10. Clean up any `manifest.yml` references to test scope config

### Out of Scope

- Adding any replacement system (no convention-based, no coverage-based, no `pytest-testmon`). This is a pure removal. If needed in the future, it must be a separate spec.
- Changes to test structure, test names, or test organization
- Changes to the test tiers themselves (unit/integration/e2e split stays)
- Changes to coverage reporting or thresholds
- Refactoring `gates.py` beyond removing scope imports
- Changes to autopilot handler references to `check_test_mapping.py` (those are template docs, updated separately)

## Acceptance Criteria

- [ ] AC1: No file named `test_scope.py` exists in `src/`
- [ ] AC2: `grep -r "TEST_SCOPE_RULES" src/` returns zero results
- [ ] AC3: `grep -r "compute_test_scope\|resolve_scope_mode\|ScopeRule\|ScopeMode" src/` returns zero results
- [ ] AC4: `grep -r "AI_ENG_TEST_SCOPE" src/ .github/` returns zero results
- [ ] AC5: CI workflow runs `pytest tests/unit` unconditionally (no scope calculation)
- [ ] AC6: CI workflow runs `pytest tests/integration` unconditionally (no scope calculation)
- [ ] AC7: CI workflow has `paths-ignore` that skips docs-only changes (verified by `grep "paths-ignore" .github/workflows/ci.yml`)
- [ ] AC8: All existing tests pass (zero regressions) -- excluding tests that tested scope itself
- [ ] AC9: `scripts/check_test_mapping.py` does not exist (deleted)
- [ ] AC10: `signals.py` no longer emits test-scope-mapping metrics
- [ ] AC11: CI step "Test mapping integrity" (`ci.yml:484-485`) is removed

## Assumptions

- ASSUMPTION: The test suite will remain under 10 minutes total for the foreseeable future, making full-suite runs acceptable
- ASSUMPTION: If the suite grows significantly, `pytest-testmon` can be added later without needing the manual rules infrastructure

## Risks

| Risk | Mitigation |
|------|-----------|
| Suite grows and 5m integration becomes 15m+ | Add `pytest-testmon` as a future spec. The manual rules system would not have been the right solution anyway. |
| docs-only `paths-ignore` misses a case where docs change breaks code | Conservative glob list. Only pure doc extensions, not `.py` docstrings. |
| Consumers of `test_scope` we have not identified | AC2, AC3, AC4 are grep-verified -- any missed import will fail at import time. |

## Dependencies

- None. This is a pure removal spec with no new dependencies.
