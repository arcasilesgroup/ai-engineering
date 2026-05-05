# Build: HX-02 T-4.2 Lifecycle Coherence Validation

## Scope

Closed the remaining `T-4.2` validation gaps for task-ledger and active work-plane coherence.

## Changes

- Added active `spec.md` / `plan.md` identity mismatch validation when both files declare a work item identity.
- Replaced exact-only in-progress `writeScope` duplicate detection with overlap-aware scope detection for broad/nested glob patterns.
- Added lifecycle artifact requirements so `review`, `verify`, and `done` ledger states carry the expected handoff or evidence refs.
- Tightened `TaskLedgerTask` validation so `blockedReason` is only legal on `blocked` tasks.
- Normalized the existing live `HX-02-T-4.2-task-dependency-validation` handoff entry from `status` to `kind` so the active ledger remains schema-readable.

## Files

- `src/ai_engineering/state/models.py`
- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_task_ledger.py`
- `tests/unit/test_validator.py`
- `.ai-engineering/specs/task-ledger.json`