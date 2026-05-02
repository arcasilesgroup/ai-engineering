# HX-02 Task-Ledger Validation - Exploration Handoff

Task: identify the next minimal approved unit inside spec-117 HX-02 after the already-landed work-plane slices, scoped to T-4.2 task-ledger and work-plane validation.

## Current Anchor

- File location: `src/ai_engineering/validator/categories/manifest_coherence.py`
- Current responsibility:
  - reads the active work-plane task ledger via `read_task_ledger(target)`
  - records `active-task-ledger` as `WARN` when the ledger is unreadable or all tasks are `done`
  - records `active-task-ledger` as `OK` when at least one task is not `done`
- Test anchor: `tests/unit/test_validator.py::TestManifestCoherence`

## Evidence Read

- `src/ai_engineering/state/models.py`
  - `TaskLifecycleState`: `planned`, `in_progress`, `blocked`, `review`, `verify`, `done`
  - `TaskLedgerTask` already enforces unique non-empty dependencies per task, non-empty `writeScope`, self-dependency rejection, and `blockedReason` when status is `blocked`
  - `TaskLedger` already enforces unique task ids
- `src/ai_engineering/validator/categories/manifest_coherence.py`
  - validates manifest/root snapshot coherence
  - now validates active spec presence plus the first ledger-aware `active-task-ledger` signal
- `tests/unit/test_validator.py::TestManifestCoherence`
  - already seeds full work-plane fixtures and asserts category-local `IntegrityCheckResult` behavior through `validate_content_integrity(...)`

## Local Hypothesis

The smallest falsifiable T-4.2 slice is task-dependency validation: every dependency id listed in a ledger task must resolve to another task id in the same ledger.

Why this slice:

- smaller than overlapping `writeScope` analysis
- smaller than handoff/evidence path validation
- smaller than spec/plan semantic mismatch checks
- direct runtime consequence of the task-ledger model
- cheapest failing-test-first seam inside existing validator code

## Smallest Next Change

Add a helper inside `manifest_coherence.py` that:

1. loads the readable ledger
2. collects the set of known task ids
3. iterates each task dependency
4. emits `task-dependency-validation` as `FAIL` when any dependency id is missing
5. emits `task-dependency-validation` as `OK` when all dependencies resolve

Scope expectation:

- one helper function
- one call site inside `_record_task_ledger_activity(...)`
- two focused tests in `TestManifestCoherence`

## Failing-Test-First Candidate

Primary failing test:

- `test_task_ledger_with_missing_dependency_fails`
  - seed one active task with dependency `T-2`
  - do not seed `T-2`
  - expect `task-dependency-validation` with `FAIL`

Companion passing test:

- `test_task_ledger_with_valid_dependencies_passes`
  - seed `T-1` and `T-2`
  - `T-2` depends on `T-1`
  - expect `task-dependency-validation` with `OK`

## Cheapest Validation Commands

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run pytest tests/unit/test_validator.py -q`
- `uv run ai-eng validate -c manifest-coherence`

## Risks / Compatibility Constraints

- main semantic choice: unresolved dependency should likely start as `FAIL`, but this assumes forward references are not an intended workflow
- keep the new check gated behind a readable ledger so idle or unreadable-ledger cases preserve current behavior
- cycle detection should follow, not precede, because it depends on valid dependency refs first
- handoff/evidence path validation and overlapping `writeScope` analysis remain separate later slices

## Recommended Next Slice

Implement `task-dependency-validation` in `manifest_coherence.py` with failing tests first, then rerun the manifest-coherence validator slice before widening to the full validator suite.