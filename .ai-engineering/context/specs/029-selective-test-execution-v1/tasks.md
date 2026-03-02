---
spec: "029"
total: 32
completed: 32
last_session: "2026-03-02"
next_session: "Done — verification + commit + PR"
---

# Tasks — Selective Test Execution v1

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec-029 scaffold files
- [x] 0.2 Update `_active.md` to spec-029
- [x] 0.3 Update product-contract Active Spec pointer

## Phase 1: Scope Engine [L]

- [x] 1.1 Create `policy/test_scope.py` dataclasses/constants/rules
- [x] 1.2 Implement deterministic scope resolution algorithm
- [x] 1.3 Implement CLI `--format args|json`
- [x] 1.4 Add `FULL_TIER_TARGETS`, triggers, and high-risk handling
- [x] 1.5 Implement rename+delete handling safety fallbacks

## Phase 2: Git + Gate Integration [L]

- [x] 2.1 Add `get_merge_base()` in `git/operations.py`
- [x] 2.2 Add `get_changed_files()` in `git/operations.py`
- [x] 2.3 Integrate scope mode resolution in pre-push gate
- [x] 2.4 Add shadow/enforce/off behavior in `_run_pre_push_checks`
- [x] 2.5 Add `test-scope` GateCheckResult diagnostics
- [x] 2.6 Update gate CLI rendering for passed diagnostics

## Phase 3: CI Integration [L]

- [x] 3.1 Rename `docs-scope` job to `change-scope` and add `test-config` output
- [x] 3.2 Add scope computation and scoped args to unit job
- [x] 3.3 Add scope computation and scoped args to integration job
- [x] 3.4 Add scope computation and scoped args to e2e job
- [x] 3.5 Upload unit scope diagnostic artifact on PRs
- [x] 3.6 Add mapping integrity step to workflow-sanity

## Phase 4: Mapping + Tests [L]

- [x] 4.1 Create `scripts/check_test_mapping.py`
- [x] 4.2 Create `tests/unit/test_test_scope.py`
- [x] 4.3 Extend `tests/integration/test_git_operations.py`
- [x] 4.4 Extend `tests/unit/test_gates.py` for scope mode/fallback
- [x] 4.5 Extend `tests/integration/test_gates_integration.py` for scope behavior
- [x] 4.6 Add missing pytestmark to six test files

## Phase 5: Governance + Verify [M]

- [x] 5.1 Update quality core gate structure text
- [x] 5.2 Append decision entry to decision-store
- [x] 5.3 Append governance event to audit-log
- [x] 5.4 Run targeted test suite and mapping checker
- [x] 5.5 Update tasks progress metadata/checkboxes
