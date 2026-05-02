# HX-02 T-4.2 Task Artifact Reference Validation - Exploration Handoff

## Current Anchor

- Owning helper chain: `src/ai_engineering/validator/categories/manifest_coherence.py`
- Current readable-ledger path already owns:
  - `active-task-ledger`
  - `task-dependency-validation`
  - `task-state-consistency`
- Ledger fields already available without schema changes:
  - `handoffs[*].path`
  - `evidence[*].path`
- Nearest test anchor: `tests/unit/test_validator.py::TestManifestCoherence`

## Candidates Considered

- Missing handoffs/evidence refs
  - smallest remaining extension of the current readable-ledger seam
  - can stay local to `manifest_coherence.py` and `TestManifestCoherence`
- Overlapping writes
  - still ledger-local but needs glob-overlap semantics that are not modeled yet
- Active spec/plan mismatch
  - broader semantic comparison across spec/plan content and not just ledger state
- Broader lifecycle-matrix rules
  - less local and less settled than the current helper chain

## Local Hypothesis

If a readable task ledger declares handoff or evidence refs, manifest coherence should fail when any declared ref path does not resolve inside the active work plane and should pass when all declared refs resolve.

Empty `handoffs` and `evidence` lists stay legal in this slice.

## Recommended Next Slice

Name the slice `task-artifact-reference-validation` and frame it as the first missing handoffs/evidence sub-slice.

Implementation boundary:

1. extend `manifest_coherence.py` with one helper that walks `task.handoffs` and `task.evidence`
2. resolve each declared path against the active work-plane root
3. emit `task-artifact-reference-validation = FAIL` when any declared ref is missing or out of plane
4. emit `task-artifact-reference-validation = OK` when all declared refs resolve
5. keep the rule readable-ledger only

## Allowed Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

Out of scope:

- `src/ai_engineering/state/models.py`
- `src/ai_engineering/state/work_plane.py`
- `src/ai_engineering/validator/categories/file_existence.py`
- schema changes
- resolver changes
- CLI changes
- new validator categories

## Failing-Test-First Candidate

Primary failing tests:

- one readable-ledger case with a missing handoff ref and `task-artifact-reference-validation = FAIL`
- one readable-ledger case with a missing evidence ref and `task-artifact-reference-validation = FAIL`

Companion passing tests:

- one case where declared handoff/evidence files exist inside the resolved active work plane and `task-artifact-reference-validation = OK`
- one case where `handoffs` and `evidence` are empty and `task-artifact-reference-validation = OK`

## Cheapest Validation Commands

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_task_with_missing_handoff_ref_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Risks / Boundaries

- keep `file_existence.py` as the owner of directory-presence checks; this slice validates task-declared refs only
- do not turn this into a sufficiency policy for when handoffs or evidence become mandatory by lifecycle state
- do not widen into write-scope overlap, full lifecycle-matrix rules, or spec/plan semantic comparison
- if later workflow policy requires non-empty refs for `review`, `verify`, or `done`, that should be a separate lifecycle-policy slice