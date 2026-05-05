# Verify HX-04 T-2.3 Kernel Runtime Policy

## Ordered Verification

1. `uv run pytest tests/unit/test_kernel_contract_runtime_policy.py -q`
   - `PASS`

## Key Signals

- `KernelContract` now declares the first explicit runtime policy for HX-04: retry ceiling `3`, active loop cap `30 min`, passive loop cap `4h`, and a blocked disposition output that keeps `watch-residuals.json` plus exit code `90` explicit.
- The contract remains read-only and policy-scoped; no durable task-state mutation or broader state-plane ownership moved into HX-04.
- The next remaining Phase 2 step is the governance readout over the result envelope, risk-accept partitioning, and failure-output contract.