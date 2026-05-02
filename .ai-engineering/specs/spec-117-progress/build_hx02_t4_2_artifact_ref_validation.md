# Build Packet - HX-02 / T-4.2 / task-artifact-reference-validation

## Task ID

HX-02 / T-4.2 / task-artifact-reference-validation

## Objective

Add one manifest-coherence check that runs only when the active `task-ledger.json` is readable and fails if any declared `handoffs[*].path` or `evidence[*].path` does not resolve inside the active work-plane root. Passing means every declared ref resolves. Empty handoff/evidence lists remain legal. Preserve idle-spec and unreadable-ledger behavior exactly.

## Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

## Failing Tests First

- add a `TestManifestCoherence` case with a missing handoff ref and expect `task-artifact-reference-validation = FAIL`
- add a `TestManifestCoherence` case with a missing evidence ref and expect `task-artifact-reference-validation = FAIL`
- add a passing case where real files exist under the resolved active work plane and all declared refs pass
- add a passing case where `handoffs` and `evidence` are empty and the new check reports `OK`
- keep the existing placeholder and malformed-ledger tests green

## Minimum Production Change

- add a small helper such as `_record_task_artifact_reference_validation(target, ledger, report)` in `manifest_coherence.py`
- resolve the active work plane with `resolve_active_work_plane(target)` and normalize each declared artifact path against `work_plane.specs_dir`
- mark a ref invalid when its path is absolute, escapes `work_plane.specs_dir` after normalization, or resolves to a target that does not exist
- aggregate bad refs into one `FAIL` result named `task-artifact-reference-validation`; otherwise emit one `OK` result
- call the helper from `_record_task_ledger_activity(...)` only after `read_task_ledger(target)` succeeds
- do not change `state/models.py`, `state/work_plane.py`, or `file_existence.py`

## Verification

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Rollback

- remove the new helper and its call from `manifest_coherence.py`
- delete the new `TestManifestCoherence` cases from `test_validator.py`

## Done Condition

- readable ledgers produce a `task-artifact-reference-validation` result
- any missing or out-of-plane handoff/evidence ref fails `manifest-coherence`
- all valid refs, including empty ref lists, pass
- idle-spec placeholder behavior and unreadable-ledger warning behavior remain unchanged
- focused pytest and `ai-eng validate -c manifest-coherence` both pass

## Execution Evidence

### Change Summary

- Added readable-ledger `TestManifestCoherence` coverage for missing handoff refs, missing evidence refs, active-work-plane pointer resolution, empty artifact lists, and unchanged placeholder/unreadable-ledger short-circuits.
- Extended `manifest_coherence.py` with one local `task-artifact-reference-validation` helper that runs only after `read_task_ledger(target)` succeeds.
- The helper rejects absolute paths, out-of-plane paths, and missing targets, and emits one aggregated `FAIL` or `OK` result inside the existing `manifest-coherence` category.

### Failing Tests Executed First

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k "missing_handoff_ref or missing_evidence_ref" -q`
- Result before implementation: `2 failed` with `assert 0 == 1` because no `task-artifact-reference-validation = FAIL` result was emitted yet.

### Passing Checks Executed

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k "missing_handoff_ref or missing_evidence_ref" -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`
- `uv run ruff check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run ruff format --check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `get_errors` on `src/ai_engineering/validator/categories/manifest_coherence.py` and `tests/unit/test_validator.py` -> no errors

### Follow-up Evidence

- Added `TestManifestCoherence::test_task_with_absolute_artifact_ref_fails` to lock the absolute-path rejection branch and assert the failure message contains `is absolute`.
- Added `TestManifestCoherence::test_task_with_escaping_relative_artifact_ref_fails` to lock the out-of-plane traversal branch and assert the failure message contains `escapes the active work plane`.
- No production change was required; the existing readable-ledger validator already rejected both path forms.
- Follow-up verification passed: `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -k "absolute_artifact_ref or escaping_relative_artifact_ref" -q` -> `2 passed`.

### Result

- `task-artifact-reference-validation` now emits on every readable active task ledger.
- Missing handoff/evidence refs fail manifest coherence, empty handoff/evidence lists stay legal, and the pointed-work-plane test proves resolution uses the active work plane instead of a hard-coded legacy root.
- Idle-spec placeholder behavior and unreadable-ledger behavior remained unchanged.

### Residual Concerns

- This slice validates declared artifact references only; it does not make handoffs or evidence mandatory for any lifecycle state.
- Broader `HX-02 / T-4.2` policy work such as overlapping write-scope analysis or spec/plan semantic checks remains out of scope.