# Build Packet - HX-02 / T-4.2 / task-state-consistency

## Task ID

HX-02 / T-4.2 / task-state-consistency

## Objective

Add a manifest-coherence rule that fails when a task marked `done` depends on another task whose status is not `done`, and passes when every `done` task depends only on `done` tasks. Preserve idle-spec and unreadable-ledger behavior.

## Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

## Failing Tests First

- Add a failing test where `T-1` is `in_progress`, `T-2` is `done`, and `T-2` depends on `T-1`; expect `task-state-consistency = FAIL`.
- Add a passing test where both `T-1` and `T-2` are `done` and `T-2` depends on `T-1`; expect `task-state-consistency = OK`.
- Keep the existing idle-spec and unreadable-ledger tests green.

## Minimum Production Change

- Keep the idle-spec placeholder branch unchanged.
- Keep the unreadable-ledger early return unchanged.
- Add one local helper in `manifest_coherence.py` that builds a task-id to status map and checks only `done` tasks.
- Emit `task-state-consistency = FAIL` when a `done` task depends on a task whose resolved status is not `done`; otherwise emit `OK`.
- Gate the new helper behind successful dependency resolution so missing dependency refs stay owned by `task-dependency-validation`.

## Verification

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_done_task_with_incomplete_dependency_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_done_task_with_done_dependency_passes -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ai-eng validate -c manifest-coherence`

## Rollback

- Remove the new helper and call site from `manifest_coherence.py`.
- Remove the two new tests from `test_validator.py`.
- Rerun the focused manifest-coherence test class and validator command.

## Done Condition

The slice is done when manifest-coherence emits `task-state-consistency = FAIL` for any `done` to non-`done` dependency, emits `task-state-consistency = OK` when all `done` task dependencies resolve to `done`, preserves idle-spec and unreadable-ledger behavior, and the focused test class plus manifest-coherence validation pass.

## Execution Evidence

### Change Summary

- Added `task-state-consistency` to manifest coherence on the readable-ledger path only.
- Gated the new check behind successful `task-dependency-validation` so missing dependency ids remain owned by the existing dependency rule.
- Added one failing-first unit test for `done -> non-done` dependencies and one passing unit test for `done -> done` dependencies.

### Failing Test Executed First

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_done_task_with_incomplete_dependency_fails -q`
- Result before implementation: `FAIL` with `assert 0 == 1` because no `task-state-consistency` failure was emitted yet.

### Passing Checks Executed

- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_done_task_with_incomplete_dependency_fails -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_done_task_with_done_dependency_passes -q`
- `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
- `uv run ruff check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run ruff format --check src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- `uv run ai-eng validate -c manifest-coherence`

### Follow-up Evidence

- Added `TestManifestCoherence::test_done_task_with_missing_dependency_stays_in_dependency_validation` to lock the ownership boundary for unresolved dependency refs on `done` tasks.
- The regression asserts exactly one `task-dependency-validation = FAIL`, no `task-state-consistency` result, and a failing `manifest-coherence` category when a `done` task depends on a missing task id.
- Follow-up verification passed: `uv run pytest tests/unit/test_validator.py::TestManifestCoherence::test_done_task_with_missing_dependency_stays_in_dependency_validation -q`.

### Result

- `task-state-consistency = FAIL` now emits when a `done` task depends on a resolved task that is not `done`.
- `task-state-consistency = OK` now emits when resolved dependencies of `done` tasks are all `done`.
- Idle-spec placeholder behavior and unreadable-ledger short-circuit behavior remained unchanged.

### Residual Concerns

- This slice intentionally defines only the `done` terminal-state invariant; it does not introduce a wider lifecycle matrix for other task states.