# HX-02 T-4.2 Task Write-Scope Duplicate Validation - Exploration Handoff

## Current Anchor

- Owning helper chain: `src/ai_engineering/validator/categories/manifest_coherence.py`
- Current readable-ledger path already owns:
  - `active-task-ledger`
  - `task-artifact-reference-validation`
  - `task-dependency-validation`
  - `task-state-consistency`
- Ledger fields already available without schema changes:
  - `status`
  - `writeScope`
- Nearest test anchor: `tests/unit/test_validator.py::TestManifestCoherence`

## Candidates Considered

- Exact duplicate active `writeScope` entries
  - stays fully inside the readable-ledger validator seam
  - uses existing fields only
  - avoids introducing glob-overlap semantics in the first step
- Active spec/plan mismatch
  - still local to `manifest_coherence`, but the smallest safe rule is less stable because a real spec can exist before a real plan
- Broader lifecycle-matrix rules
  - not settled enough in `HX-02` and handoff sufficiency is addressed later

## Local Hypothesis

If a readable active task ledger contains two `in_progress` tasks with the same exact `writeScope` entry, `manifest-coherence` should fail.

This is the smallest unambiguous sub-slice of duplicate overlapping writes.

## Recommended Next Slice

Name the slice `task-write-scope-duplicate-validation` and frame it as the first overlapping-writes sub-slice.

Implementation boundary:

1. Extend `manifest_coherence.py` with one helper that walks readable-ledger tasks.
2. Consider only `in_progress` tasks in this first slice.
3. Group exact `writeScope` strings across those tasks.
4. Emit `task-write-scope-duplicate-validation = FAIL` when any exact duplicate scope string is claimed by more than one `in_progress` task.
5. Emit `task-write-scope-duplicate-validation = OK` when no exact duplicates exist.
6. Keep the rule readable-ledger only.

## Allowed Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

Out of scope:

- `src/ai_engineering/state/models.py`
- `src/ai_engineering/state/work_plane.py`
- `src/ai_engineering/validator/categories/file_existence.py`
- CLI changes
- resolver changes
- generic glob-intersection semantics such as `src/**` vs `src/foo.py`
- active spec/plan semantic comparison
- lifecycle rules that require handoffs or evidence

## Failing-Test-First Candidate

Primary failing test:

- add one readable-ledger case with two `in_progress` tasks both declaring `src/**` and expect `task-write-scope-duplicate-validation = FAIL`

Companion passing tests:

- one case where duplicate scope exists only across `done` and `in_progress` tasks and the new check reports `OK`
- one case where `in_progress` tasks have distinct `writeScope` values and the new check reports `OK`

## Cheapest Validation Commands

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k duplicate_write_scope -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Risks / Boundaries

- Do not widen this slice into generic overlap semantics for glob containment or intersection.
- Do not fail planned or blocked tasks in this first slice unless a nearby contract tightens active-state semantics.
- Do not mix this slice with active spec/plan mismatch.
- Do not turn this into handoff or evidence sufficiency policy.
- If later phases need broader collision detection, that can extend this helper after the exact-duplicate case is green.