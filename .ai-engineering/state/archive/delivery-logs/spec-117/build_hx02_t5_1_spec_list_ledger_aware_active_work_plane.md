# Build Packet - HX-02 / T-5.1 / spec-list-ledger-aware-active-work-plane

## Task ID

HX-02-T-5.1-spec-list-ledger-aware-active-work-plane

## Objective

Cut `ai-eng spec list` over from placeholder-only active-spec detection to resolved-ledger activity detection. When the resolved active work plane is a spec-local root with placeholder `spec.md`, the CLI must stop reporting `No active spec.` if the readable resolved `task-ledger.json` still contains any non-done task. Preserve idle behavior for fully-done ledgers.

## Write Scope

- `src/ai_engineering/cli_commands/spec_cmd.py`
- `tests/unit/test_spec_cmd.py`

## Failing Tests First

- add a focused `TestSpecListCli` regression where the active work plane points at a spec-local root with placeholder `spec.md` and one live ledger task; expect `spec_list()` to stop printing `No active spec.` and instead print the work-plane directory name
- add a done-ledger guardrail where the same placeholder-backed resolved work plane must stay idle

## Minimum Production Change

- keep the cutover local to `spec_list()` in `spec_cmd.py`
- keep the existing placeholder fast path for truly idle work planes
- consult `read_task_ledger(root)` only when the resolved `spec.md` is the placeholder
- treat placeholder specs as active only when the readable resolved ledger contains at least one task whose status is not `DONE`
- when a placeholder-backed work plane is still active, fall back to the resolved work-plane directory name for display instead of the placeholder heading

## Verification

- `uv run pytest tests/unit/test_spec_cmd.py -k live_resolved_ledger -q`
- `uv run pytest tests/unit/test_spec_cmd.py -k placeholder_spec -q`
- `uv run pytest tests/unit/test_spec_cmd.py -q`
- `uv run ruff check src/ai_engineering/cli_commands/spec_cmd.py tests/unit/test_spec_cmd.py`
- `uv run ruff format --check src/ai_engineering/cli_commands/spec_cmd.py tests/unit/test_spec_cmd.py`

## Done Condition

- `spec_list()` no longer treats placeholder prose alone as authoritative idle state for a spec-local work plane with live ledger tasks
- placeholder plus fully-done resolved ledger still reports `No active spec.`
- focused and full `spec_cmd` unit coverage pass
- local Ruff lint and format checks pass on the touched files

## Execution Evidence

### Change Summary

- Added live-ledger and done-ledger placeholder-work-plane regressions to `tests/unit/test_spec_cmd.py`.
- Updated `spec_list()` to consult `read_task_ledger(root)` before treating a placeholder-backed resolved work plane as idle.
- Added a display fallback so active placeholder-backed work planes show the resolved directory name instead of the placeholder heading.

### Failing Test Executed First

- `uv run pytest tests/unit/test_spec_cmd.py -k live_resolved_ledger -q`
- Result before implementation: `1 failed` because `spec_list()` still printed `No active spec.` while the resolved placeholder-backed work plane had a live ledger task.

### Passing Checks Executed

- `uv run pytest tests/unit/test_spec_cmd.py -k live_resolved_ledger -q` -> `1 passed`
- `uv run pytest tests/unit/test_spec_cmd.py -k placeholder_spec -q` -> `4 passed`
- `uv run pytest tests/unit/test_spec_cmd.py -q` -> `18 passed`
- `uv run ruff check src/ai_engineering/cli_commands/spec_cmd.py tests/unit/test_spec_cmd.py` -> `All checks passed!`
- `uv run ruff format --check src/ai_engineering/cli_commands/spec_cmd.py tests/unit/test_spec_cmd.py` -> `2 files already formatted`

### Result

- `ai-eng spec list` now treats live placeholder-backed spec-local work planes as active instead of printing a false idle message.
- The done-ledger idle path remains intact.
- The cutover stayed local to `spec_list()` and its unit coverage.

### Residual Concerns

- Remaining `T-5.1` readers still include identifier-driven consumers such as `state.audit` and `vcs.pr_description`, which need an explicit fallback identifier policy when the compatibility `spec.md` buffer is still placeholder text.
