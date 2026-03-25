# Plan: spec-069 Nuclear Removal of TEST_SCOPE_RULES

## Pipeline: standard
## Phases: 4
## Tasks: 11 (build: 9, verify: 2)
## Status: COMPLETE

### Phase 1: Remove production consumers
**Gate**: PASSED

- [x] T-1.1: Remove test scope integration from `gates.py` (agent: build) -- DONE
- [x] T-1.2: Remove test scope metrics from `signals.py` (agent: build) -- DONE

### Phase 2: Remove test code and scripts
**Gate**: PASSED

- [x] T-2.1: Delete `tests/unit/test_test_scope.py` (agent: build) -- DONE
- [x] T-2.2: Remove scope test from `test_real_project_integrity.py` (agent: build) -- DONE
- [x] T-2.3: Clean `TestScope` references from gate tests (agent: build) -- DONE
- [x] T-2.4: Delete `scripts/check_test_mapping.py` (agent: build) -- DONE

### Phase 3: Simplify CI
**Gate**: PASSED

- [x] T-3.1: Remove scope calculation from CI test jobs (agent: build) -- DONE
- [x] T-3.2: Add `paths-ignore` for docs-only changes (agent: build) -- DONE
- [x] T-3.3: Remove "Test mapping integrity" CI step (agent: build) -- DONE

### Phase 4: Delete source and verify
**Gate**: PASSED (11/11 ACs)

- [x] T-4.1: Delete `src/ai_engineering/policy/test_scope.py` (agent: build) -- DONE
- [x] T-4.2: Verify all acceptance criteria (agent: verify) -- DONE (1907 passed, 0 failed)

### Unplanned fix
- [x] T-FIX: Clean `test_scope` references from `test_test_confidence.py` -- DONE
  - Deleted `test_test_scope_fallback` test method (tested removed Source 3)
  - Simplified `test_no_data_fallback` (removed test_scope module mock)
  - Updated assertions from `in ("test_scope", "none")` to `== "none"`
