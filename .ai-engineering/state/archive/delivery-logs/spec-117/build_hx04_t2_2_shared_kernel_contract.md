# Build Packet - HX-04 / T-2.2 / shared-kernel-contract

## Task ID

HX-04-T-2.2-shared-kernel-contract

## Objective

Implement the canonical HX-04 kernel contract over the owned orchestrator/gate path so registration, resolved mode, findings-envelope family, residual compatibility, and publish ownership stop being inferred from split surfaces.

## Minimum Change

- add `KernelContract` plus `resolve_kernel_contract(...)` to `ai_engineering.policy.orchestrator`
- make `run_gate(...)` consume that shared contract for resolved gate mode and default registration
- keep publish ownership explicit as adapter-owned for the Phase 2 first cut without widening into hook cutover or state/eval ownership

## Verification

- `uv run pytest tests/unit/test_kernel_contract.py -q`