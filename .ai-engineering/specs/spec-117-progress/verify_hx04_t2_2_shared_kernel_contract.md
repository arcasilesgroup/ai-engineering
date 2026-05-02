# Verify HX-04 T-2.2 Shared Kernel Contract

## Ordered Verification

1. `uv run pytest tests/unit/test_kernel_contract.py -q`
   - `PASS`

## Key Signals

- `KernelContract` and `resolve_kernel_contract(...)` now exist in `ai_engineering.policy.orchestrator`.
- The shared contract makes local registration, resolved gate mode, findings-envelope family, residual compatibility, and publish ownership explicit in one place.
- `run_gate(...)` now consumes that contract for the owned orchestrator/gate path instead of resolving registration and gate mode through separate local branches.