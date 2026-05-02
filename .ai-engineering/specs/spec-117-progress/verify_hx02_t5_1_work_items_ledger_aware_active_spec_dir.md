# Verify - HX-02 / T-5.1 / work-items-ledger-aware-active-spec-dir

## Commands

- `uv run pytest tests/unit/test_work_items_service.py -k placeholder_active_spec_root_when_resolved_ledger_has_live_task -q`
- `uv run pytest tests/unit/test_work_items_service.py -k active_spec_root -q`
- `uv run pytest tests/unit/test_work_items_service.py -q`
- `uv run ruff check src/ai_engineering/work_items/service.py tests/unit/test_work_items_service.py`
- `uv run ruff format --check src/ai_engineering/work_items/service.py tests/unit/test_work_items_service.py`

## Results

- Focused live-ledger regression passed after the production cutover.
- The active-spec-root subset passed with `4 passed`.
- The full work-items service unit file passed with `31 passed`.
- Ruff lint passed on both touched files.
- Ruff format check passed after one local formatting repair in the touched test file.

## Conclusion

The completed slice is behaviorally covered and locally clean. Placeholder prose alone no longer suppresses work-item sync when the resolved spec-local work plane still has live ledger tasks.
