# Build Packet - HX-02 / T-4.2 / task-dependency-validation

## Task ID

HX-02 / T-4.2 / task-dependency-validation

## Objective

Add a manifest-coherence check that fails when a readable active task ledger contains a dependency id that does not resolve to another task in the same ledger, and passes when all dependency refs resolve. Preserve idle-spec and unreadable-ledger behavior.

## Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

## Dependencies

- `.ai-engineering/specs/spec-117-progress/explore_hx02_task_ledger_validation.md`
- `.ai-engineering/specs/spec-117-progress/review_hx02_task_ledger_validation_guard.md`
- Reuse existing task-ledger model invariants; do not change models or schema.
- Keep the work inside the existing readable-ledger path in `manifest_coherence.py`; no new validator category.

## Failing Tests First

- Add a failing test for a readable ledger where `T-1` depends on missing `T-2`; expect `task-dependency-validation = FAIL`.
- Add a passing test for a readable ledger containing both `T-1` and `T-2` with a valid dependency edge; expect `task-dependency-validation = OK`.

## Minimum Production Change

- In the existing ledger helper, collect known task ids from the readable ledger.
- Validate each task dependency against that set.
- Emit `task-dependency-validation = FAIL` on missing refs, otherwise emit one `OK` result once all refs resolve.
- Keep current `active-task-ledger` `OK` / `WARN` behavior unchanged.

## Verification

- Confirm the missing-dependency test fails before the production edit.
- Run `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`.
- Run `uv run ai-eng validate -c manifest-coherence`.

## Rollback

- Remove the two new tests.
- Remove the task-dependency-validation helper or call site.
- Leave the existing `active-task-ledger` behavior intact.

## Done Condition

Targeted manifest-coherence tests pass, the new `FAIL` and `OK` paths are covered, and placeholder or unreadable-ledger behavior remains unchanged.

## Execution Evidence

### Change Summary

- Added focused `TestManifestCoherence` coverage for missing and resolved task dependency refs.
- Extended the existing readable-ledger path in `manifest_coherence.py` to emit `task-dependency-validation` as `FAIL` for unknown task ids and `OK` when all refs resolve.
- Kept idle-spec placeholder behavior and unreadable-ledger `active-task-ledger` warning behavior unchanged.

### Failing Test Executed First

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_task_ledger_with_missing_dependency_fails -q`
- Failed before the production change with `assert 0 == 1` because no `task-dependency-validation = FAIL` result was emitted.

### Passing Checks Executed

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_task_ledger_with_missing_dependency_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`
- `uv run ruff check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run ruff format --check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`

### Follow-up Evidence

- Added `TestManifestCoherence::test_malformed_task_ledger_warns_and_skips_dependency_validation` to lock the unreadable-ledger compatibility contract.
- The regression asserts exactly one `active-task-ledger = WARN`, no `task-dependency-validation` result, and a passing `manifest-coherence` category when `task-ledger.json` is malformed.
- Follow-up verification passed: `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q` (`13 passed`).
- Follow-up Ruff checks passed: `uv run ruff check tests/unit/test_validator.py` and `uv run ruff format --check tests/unit/test_validator.py`.

### Result

- `task-dependency-validation` now fails when a readable ledger references a missing task id and passes when all dependency refs resolve.
- The slice remains inside the existing `manifest-coherence` validator category with no model, schema, CLI, or work-plane changes.

### Residual Concerns

- This slice intentionally does not cover cycle detection, overlapping `writeScope`, or handoff/evidence validation.
- If unresolved dependency refs are later accepted as a forward-planning workflow, severity may need to relax from `FAIL` in a later slice.