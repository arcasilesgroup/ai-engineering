# Build Packet - HX-05 / T-2.1 / state-plane-contract-invariants

## Task ID

HX-05-T-2.1-state-plane-contract-invariants

## Objective

Write failing tests for the first explicit `HX-05` state-plane contract: durable global-state membership, derived current projections, residue membership, and spec-local evidence relocation requirements.

## Minimum Change

- add focused unit tests for a shared `resolve_state_plane_contract(...)` API under `state.control_plane`
- require the contract to classify durable cross-spec state, generated current-state projections, residue outputs, and globally parked spec-local audit artifacts with correctness and compatibility-shim semantics
- update the `HX-05` plan and work-plane artifacts so the feature can move directly to `T-2.2` implementation

## Verification

- `uv run pytest tests/unit/test_state_plane_contract.py -q`