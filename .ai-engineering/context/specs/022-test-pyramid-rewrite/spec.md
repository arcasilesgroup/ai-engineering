---
id: "022"
slug: "test-pyramid-rewrite"
status: "in-progress"
created: "2026-02-25"
---

# Spec 022 — Test Pyramid Rewrite

## Problem

The test suite has an inverted pyramid: 16 of 29 files in `tests/unit/` use `subprocess`, `installed_project`, or real git operations — making them integration tests misclassified as unit tests. Consequences:

1. Pre-push gate runs all 615 tests with a 600s timeout because marker-based filtering (`-m "not e2e and not live"`) has no effect — zero tests use `@pytest.mark.*` decorators despite markers being defined in pyproject.toml.
2. No parallel execution: `pytest-xdist` is not installed.
3. CI runs 9 matrix combinations (3 OS × 3 Python) for the full suite including e2e, without staged execution.
4. Developer feedback loop is slow: every push waits for the full test suite.

## Solution

Implement a correct test pyramid with proper tier separation, parallel execution, and staged CI:

1. **Re-categorize**: Move 16 misplaced test files from `tests/unit/` to `tests/integration/`.
2. **Create mocked unit tests**: Write fast, mocked unit tests for the top 5 heaviest modules (gates, installer, doctor, readiness, skills_maintenance).
3. **Add pytest-xdist**: Enable parallel test execution with `-n auto --dist worksteal`.
4. **Apply markers**: Add `pytestmark` to all 34 test files (unit/integration/e2e).
5. **Optimize gates**: Pre-push runs only `unit` tier (target < 60s).
6. **Split CI**: Unit → Integration → E2E staged pipeline with reduced matrix.

## Scope

### In Scope

- Test file re-categorization (unit → integration).
- New mocked unit tests for top 5 modules.
- pytest-xdist integration.
- Marker application to all test files.
- gates.py stack-tests command update.
- CI workflow split (3 stages).
- Framework-smoke matrix reduction (9 → 3).
- Quality standard updates (performance targets).
- conftest.py fixture scope optimization.

### Out of Scope

- New mocked unit tests for remaining 5 modules (deferred to follow-up).
- Test logic rewriting (existing integration tests stay as-is, just moved).
- New test frameworks or runners.
- Live test tier implementation.

## Acceptance Criteria

1. All test files have `pytestmark` decorators matching their tier.
2. `tests/unit/` contains only pure unit tests (no subprocess, no `installed_project`).
3. Pre-push gate uses `-m unit` and completes in < 120s.
4. CI has 3 staged test jobs: unit (full matrix), integration (reduced), e2e (single).
5. Coverage ≥ 90% across full suite.
6. All existing tests pass with no behavioral changes.
7. Content integrity (`ai-eng validate`) passes.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D022-001 | Pre-push runs unit tier only | Unit tests are fast, mocked, and catch logic bugs. Integration/e2e run in CI. |
| D022-002 | Top 5 modules get mocked unit tests first | gates, installer, doctor, readiness, skills_maintenance have the most tests and heaviest fixtures. |
| D022-003 | Use `worksteal` distribution | Dynamic work stealing handles uneven test durations better than `loadscope`. |
| D022-004 | Framework-smoke reduced to 3 entries | OS-specific bugs are the target; Python version variance is low. |
