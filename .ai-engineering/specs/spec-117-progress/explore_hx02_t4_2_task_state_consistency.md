# HX-02 T-4.2 Task State Consistency - Exploration Handoff

Task: identify the next minimal approved unit inside `HX-02 / T-4.2` after the completed `task-dependency-validation` slice.

## Current Anchor

- File location: `src/ai_engineering/validator/categories/manifest_coherence.py`
- Current responsibility:
  - reads the active work-plane task ledger via `read_task_ledger(target)`
  - records `active-task-ledger`
  - records `task-dependency-validation`
- Test anchor: `tests/unit/test_validator.py::TestManifestCoherence`

## Candidates Considered

- `illegal-terminal-states`
  - lowest complexity
  - same validator category and same readable-ledger path
  - one falsifiable rule and one cheap test seam
- `overlapping-writes`
  - local but higher complexity because it needs overlap semantics for globs/path scopes
- `missing-handoffs-evidence`
  - medium complexity and more policy-sensitive because existence vs. requirement rules are less settled
- `active-spec/plan-mismatch`
  - larger slice because it likely requires parsing and comparing spec/plan semantics instead of staying fully ledger-local

## Local Hypothesis

The smallest falsifiable next slice is `task-state-consistency`: a task marked `done` cannot depend on a task whose status is not `done`.

Why this slice:

- it builds directly on the completed dependency-resolution slice
- it stays inside the readable-ledger path already owned by `manifest_coherence.py`
- it needs no new validator category, schema change, or CLI surface
- it is cheaper and more deterministic than glob-overlap or spec/plan semantic comparison

## Recommended Next Slice

Add a helper inside `manifest_coherence.py` that:

1. reuses the readable ledger already loaded in `_record_task_ledger_activity(...)`
2. maps task ids to lifecycle states
3. flags any `done` task whose dependency target is present but not `done`
4. emits `task-state-consistency = FAIL` when such a case exists
5. emits `task-state-consistency = OK` when all `done` tasks depend only on `done` tasks

Scope expectation:

- one helper function
- one call site inside `_record_task_ledger_activity(...)`
- two focused tests in `TestManifestCoherence`

## Allowed Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

## Failing-Test-First Candidate

Primary failing test:

- `test_task_marked_done_with_incomplete_dependency_fails`
  - seed `T-1` as `in_progress`
  - seed `T-2` as `done` with dependency `T-1`
  - expect `task-state-consistency = FAIL`

Companion passing test:

- `test_done_task_with_done_dependency_passes`
  - seed `T-1` as `done`
  - seed `T-2` as `done` with dependency `T-1`
  - expect `task-state-consistency = OK`

## Cheapest Validation Commands

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_task_marked_done_with_incomplete_dependency_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Risks / Boundaries

- keep idle-spec placeholder and unreadable-ledger behavior unchanged
- do not widen into cycle detection, overlapping writes, or handoff/evidence requirements in the same slice
- this slice only checks the terminal-state dependency rule for `done`; it does not attempt to define a full state-machine for all statuses
- if later workflow policy allows `done` tasks to depend on non-`done` tasks, severity may need to relax from `FAIL` in a later slice