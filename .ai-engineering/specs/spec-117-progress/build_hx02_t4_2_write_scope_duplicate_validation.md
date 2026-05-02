# Build Packet - HX-02 / T-4.2 / task-write-scope-duplicate-validation

## Task ID

`HX-02-T-4.2-task-write-scope-duplicate-validation`

## Objective

On a readable active `task-ledger.json` only, emit one `manifest-coherence` result named `task-write-scope-duplicate-validation`. It must `FAIL` when the same exact `writeScope` string is declared by two different `in_progress` tasks, and `OK` otherwise. Preserve idle-spec placeholder and unreadable-ledger behavior exactly. Exact-string comparison only; do not add glob overlap or intersection semantics.

## Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`
- No schema, resolver, CLI, other validator categories, or templates.

## Failing Tests First

- Add a `TestManifestCoherence` case where two `IN_PROGRESS` tasks both declare `write_scope=["src/**"]` and expect one `task-write-scope-duplicate-validation = FAIL`.
- Add a passing case where `IN_PROGRESS` tasks use distinct `writeScope` strings and expect one `task-write-scope-duplicate-validation = OK`.
- Add a passing case where the duplicate string appears on fewer than two `IN_PROGRESS` tasks, for example one `IN_PROGRESS` task plus one `DONE` or `PLANNED` task, and expect `OK`.
- Extend the existing idle-spec placeholder and unreadable-ledger tests to assert the new result is not emitted on those paths.

## Minimum Production Change

- Add a small helper in `src/ai_engineering/validator/categories/manifest_coherence.py`, for example `_record_task_write_scope_duplicate_validation(ledger, report)`.
- Call it from the readable-ledger path in `_record_task_ledger_activity(...)` only after `read_task_ledger(target)` succeeds.
- Filter the ledger to tasks with `status == TaskLifecycleState.IN_PROGRESS`.
- Build a mapping of exact `writeScope` strings to distinct task ids that declare them.
- If any exact scope string is declared by more than one `IN_PROGRESS` task id, emit one aggregated `FAIL` result named `task-write-scope-duplicate-validation` that lists the duplicated scope string(s) and task id(s).
- Otherwise emit one `OK` result with the same name.
- Do not normalize strings, expand globs, compare overlaps, or add schema-level uniqueness checks.

## Verification

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Rollback

- Remove the new helper and its call from `src/ai_engineering/validator/categories/manifest_coherence.py`.
- Delete the new duplicate-write-scope tests and the placeholder/unreadable-ledger assertions from `tests/unit/test_validator.py`.

## Done Condition

- Readable active ledgers always emit exactly one `task-write-scope-duplicate-validation` result.
- Two different `IN_PROGRESS` tasks sharing the same exact `writeScope` string make `manifest-coherence` fail.
- Distinct `IN_PROGRESS` scopes, or duplicates that do not involve two `IN_PROGRESS` tasks, stay `OK`.
- Idle-spec placeholder and unreadable-ledger behavior remain unchanged, including no new result emitted on those paths.
- The focused pytest slice and `uv run ai-eng validate -c manifest-coherence` both pass.

## Execution Evidence

### Change Summary

- Added `task-write-scope-duplicate-validation` to the readable-ledger helper chain in `manifest_coherence.py`.
- Kept evaluation local to readable ledgers only by wiring the new helper inside `_record_task_ledger_activity(...)` after ledger read succeeds.
- Implemented exact-string duplicate detection across distinct `IN_PROGRESS` task ids only; no glob expansion, normalization, or schema-level uniqueness checks.
- Added focused unit coverage for duplicate fail, distinct ok, fewer-than-two-in-progress ok, and non-emission on placeholder/malformed-ledger paths.

### Failing Tests First

- Ran `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k 'write_scope or active_spec_placeholder or malformed_task_ledger_warns_and_skips_dependency_validation' -q` before the production edit.
- Result before code change: `3 failed, 2 passed`.
- Failure mode: readable-ledger cases emitted no `task-write-scope-duplicate-validation` result yet, while placeholder and malformed-ledger non-emission assertions already passed.

### Passing Checks

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k 'write_scope or active_spec_placeholder or malformed_task_ledger_warns_and_skips_dependency_validation' -q`
- `uv run ruff check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run ruff format --check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

### Result

- PASS: readable active task ledgers now emit exactly one `task-write-scope-duplicate-validation` result.
- PASS: exact duplicate `writeScope` strings across two `IN_PROGRESS` tasks fail `manifest-coherence`.
- PASS: distinct scopes and duplicates involving fewer than two `IN_PROGRESS` tasks remain ok.
- PASS: idle placeholder and unreadable-ledger paths still do not emit the new result.

### Follow-up Evidence

- Added `TestManifestCoherence::test_overlapping_but_non_identical_write_scope_strings_pass` to lock the exact-string-only contract and prove that overlapping but non-identical `writeScope` entries still pass.
- No production change was required; the existing readable-ledger validator already kept overlap semantics out of scope.
- Follow-up verification passed: `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q` -> `25 passed`.

### Residual Concerns

- Exact-string-only semantics are intentional here; overlapping or equivalent glob patterns are still treated as distinct unless the strings match exactly.