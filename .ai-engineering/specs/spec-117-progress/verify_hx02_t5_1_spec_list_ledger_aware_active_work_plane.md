# Verify - HX-02 / T-5.1 / spec-list-ledger-aware-active-work-plane

## Commands

- `uv run pytest tests/unit/test_spec_cmd.py -k live_resolved_ledger -q`
- `uv run pytest tests/unit/test_spec_cmd.py -k placeholder_spec -q`
- `uv run pytest tests/unit/test_spec_cmd.py -q`
- `uv run ruff check src/ai_engineering/cli_commands/spec_cmd.py tests/unit/test_spec_cmd.py`
- `uv run ruff format --check src/ai_engineering/cli_commands/spec_cmd.py tests/unit/test_spec_cmd.py`

## Results

- The focused live-ledger regression passed after the production cutover.
- The placeholder-spec bundle passed with `4 passed`, covering both live-ledger activation and done-ledger idle behavior.
- The full `spec_cmd` unit file passed with `18 passed`.
- Ruff lint and format checks passed on both touched files after one import-order auto-fix.

## Conclusion

`ai-eng spec list` now respects the resolved ledger before treating a placeholder-backed spec-local work plane as idle, and the touched CLI slice is behaviorally covered and locally clean.
