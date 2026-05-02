# HX-02 Task-Ledger Validation - Guard Review

## Slice Verdict

- Conditional approval.
- This is the correct next minimal HX-02 slice after `.ai-engineering/specs/spec-117-progress/explore_hx02_task_ledger_validation.md`.
- Keep the work local to `src/ai_engineering/validator/categories/manifest_coherence.py` and its existing active-ledger helper.
- No new validator architecture surface is justified for this step.

## Governance Constraints

- Constitution Article I: the implementation must stay traceable to the approved HX-02 slice above.
- Constitution Article II: the first change is a failing unit test; only the minimum production edit follows.
- Constitution Article III: guard remains advisory-only; only build may write production code.
- Idle specs and unreadable ledgers must preserve current compatibility behavior.

## Allowed Write Scope

- `tests/unit/test_validator.py`
- `src/ai_engineering/validator/categories/manifest_coherence.py`

Out of scope for this slice:

- `state/models.py`
- `state/work_plane.py`
- CLI flows
- new validator categories
- schema rewrites

## Required Tests And Evidence

- Add one failing unit test for a readable ledger with a missing dependency id, expecting `task-dependency-validation = FAIL`.
- Add one passing unit test for fully resolved dependencies, expecting `task-dependency-validation = OK`.
- Preserve existing placeholder and unreadable-ledger behavior.
- Evidence bar:
  - `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`

## Residual Risks

- This slice intentionally introduces a `FAIL` path into ledger semantics inside `manifest-coherence`.
- Do not widen into cycle detection, overlapping `writeScope`, or handoff/evidence validation in the same change.
- If unresolved dependency refs are later shown to be a valid forward-planning workflow, severity may need to drop from `FAIL` to `WARN` in a later slice.

## Go / No-Go

- Go if the change remains test-first and local.
- No-Go if it introduces a new architecture surface or changes idle/unreadable-ledger compatibility.