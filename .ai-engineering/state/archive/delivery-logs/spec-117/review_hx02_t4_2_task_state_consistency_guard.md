# HX-02 T-4.2 Task State Consistency - Guard Review

## Slice Verdict

- `PASS with one concern`.
- This is the correct next minimal `HX-02 / T-4.2` slice after `task-dependency-validation`.
- Frame it explicitly as the first `illegal terminal states` sub-slice to avoid resume drift.

## Allowed Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

Out of scope for this slice:

- schema changes
- CLI changes
- work-plane resolver changes
- new validator categories
- cycle detection
- overlapping write-scope analysis
- missing handoff/evidence enforcement
- active spec/plan semantic comparison

## Required Tests And Evidence

- Add one failing unit test where a `done` task depends on a non-`done` task and expect `task-state-consistency = FAIL`.
- Add one passing unit test where a `done` task depends only on `done` tasks and expect `task-state-consistency = OK`.
- Preserve idle-spec placeholder and unreadable-ledger behavior.
- Evidence bar:
  - `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
  - `uv run ai-eng validate -c manifest-coherence`

## Residual Risks

- The new rule must stay on the readable-ledger path only.
- This slice defines one terminal-state invariant for `done`; it does not define a full lifecycle matrix.

## Go / No-Go

- `GO` if the change remains local to the existing `manifest-coherence` validator seam and preserves current idle/unreadable-ledger behavior.