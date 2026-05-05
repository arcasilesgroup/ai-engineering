# Verify HX-04 T-2.1 Kernel Contract Invariants

## Ordered Verification

1. `uv run pytest tests/unit/test_kernel_contract.py -q`
   - `FAIL` (expected RED)

## Key Signals

- All five new contract tests fail for the same reason: `ai_engineering.policy.orchestrator.resolve_kernel_contract` is not implemented yet.
- The failure is local and discriminating rather than noisy; no unrelated runtime breakage masked the result.
- `T-2.2` now owns implementing the canonical kernel contract over the orchestrator/gate path so registration, mode resolution, findings-envelope parity, residual compatibility, and publish ownership stop being inferred from split layers.