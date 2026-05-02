# Build Packet - HX-02 / T-5.1 / work-items-ledger-aware-active-spec-dir

## Task ID

HX-02-T-5.1-work-items-ledger-aware-active-spec-dir

## Objective

Cut work-item sync over from placeholder-only spec activity detection to resolved-ledger activity detection. When the resolved active work plane is itself a spec-local root, placeholder `spec.md` must stay syncable if the readable `task-ledger.json` still contains any non-done task. Preserve idle behavior for fully-done or unreadable ledgers.

## Write Scope

- `src/ai_engineering/work_items/service.py`
- `tests/unit/test_work_items_service.py`

## Failing Tests First

- add a pointer-aware regression where the resolved work plane is a spec-local root, `spec.md` is the placeholder, and the readable ledger still contains one `in_progress` task; expect sync target selection to treat the directory as active
- keep or add guardrail coverage where the same placeholder root stays idle when the resolved ledger is fully done
- keep or add guardrail coverage where the same placeholder root stays idle when the ledger is unreadable

## Minimum Production Change

- keep the cutover local to `_iter_sync_targets(...)` and `_is_active_spec_dir(...)` in `work_items/service.py`
- pass `project_root` into the active-spec-dir predicate so it can read the resolved ledger through `read_task_ledger(project_root)`
- keep the existing fast path for non-placeholder spec files
- treat placeholder specs as active only when the readable resolved ledger still has at least one task whose status is not `DONE`
- do not widen into validator, PR description, reset, or resolver changes

## Verification

- `uv run pytest tests/unit/test_work_items_service.py -k placeholder_active_spec_root_when_resolved_ledger_has_live_task -q`
- `uv run pytest tests/unit/test_work_items_service.py -k active_spec_root -q`
- `uv run pytest tests/unit/test_work_items_service.py -q`
- `uv run ruff check src/ai_engineering/work_items/service.py tests/unit/test_work_items_service.py`
- `uv run ruff format --check src/ai_engineering/work_items/service.py tests/unit/test_work_items_service.py`

## Done Condition

- placeholder `spec.md` plus readable resolved ledger with live tasks is treated as an active spec-local root for sync
- placeholder `spec.md` plus fully-done or unreadable resolved ledger remains idle
- focused and full work-items unit coverage pass
- local Ruff lint and format checks pass on the touched files

## Execution Evidence

### Change Summary

- Added live-ledger, done-ledger, and unreadable-ledger regressions to `tests/unit/test_work_items_service.py` for placeholder spec-local work-plane roots.
- Updated `work_items/service.py` so `_iter_sync_targets(...)` forwards `project_root` into `_is_active_spec_dir(...)`.
- Made `_is_active_spec_dir(...)` mirror the existing Wave 1 cutover semantics: non-placeholder specs stay active immediately, while placeholder specs remain active only when `read_task_ledger(project_root)` returns a readable ledger with at least one non-done task.

### Failing Test Executed First

- `uv run pytest tests/unit/test_work_items_service.py -k placeholder_active_spec_root_when_resolved_ledger_has_live_task -q`
- Result before implementation: `1 failed` because `sync_spec_issues(...)` returned no sync targets while the resolved placeholder-backed work plane still had an `in_progress` ledger task.

### Passing Checks Executed

- `uv run pytest tests/unit/test_work_items_service.py -k placeholder_active_spec_root_when_resolved_ledger_has_live_task -q` -> `1 passed`
- `uv run pytest tests/unit/test_work_items_service.py -k active_spec_root -q` -> `4 passed`
- `uv run pytest tests/unit/test_work_items_service.py -q` -> `31 passed`
- `uv run ruff check src/ai_engineering/work_items/service.py tests/unit/test_work_items_service.py` -> `All checks passed!`
- `uv run ruff format --check src/ai_engineering/work_items/service.py tests/unit/test_work_items_service.py` -> `2 files already formatted`

### Result

- Work-item sync no longer treats placeholder prose alone as the authoritative idle state when the resolved spec-local work plane still has live ledger tasks.
- The cutover stayed local to the work-items service and its unit coverage.
- Done-ledger and unreadable-ledger compatibility behavior remained unchanged.

### Residual Concerns

- Remaining `T-5.1` scope still includes other runtime or CLI readers that trust placeholder spec text instead of the resolved ledger.
