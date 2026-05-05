# Build Packet - HX-04 / T-2.1 / kernel-contract-invariants

## Task ID

HX-04-T-2.1-kernel-contract-invariants

## Objective

Write failing tests or invariant coverage for the first explicit HX-04 kernel contract: check registration, mode resolution, normalized findings envelope, residual-output compatibility, and publish ownership.

## Minimum Change

- add focused unit tests for a shared `resolve_kernel_contract(...)` API under `policy.orchestrator`
- cover regulated and prototyping local registration plus protected-branch escalation
- require the contract to declare `GateFindingsDocument` as the normalized findings envelope, `watch-residuals.json` compatibility, and an explicit publish owner for the Phase 2 first cut

## Verification

- `uv run pytest tests/unit/test_kernel_contract.py -q`