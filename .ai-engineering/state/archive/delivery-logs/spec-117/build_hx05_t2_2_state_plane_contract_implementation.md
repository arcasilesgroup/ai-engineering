# Build Packet - HX-05 / T-2.2 / state-plane-contract-implementation

## Task ID

HX-05-T-2.2-state-plane-contract-implementation

## Objective

Implement the first executable `HX-05` state-plane contract so durable state, derived current projections, residue outputs, deferred learning-funnel residue, and globally parked spec-local evidence stop being classified implicitly from scattered path literals.

## Minimum Change

- implement `StatePlaneArtifactClass`, `StatePlaneContract`, and `resolve_state_plane_contract(...)` in `state.control_plane`
- classify the durable cross-spec core, generated current projections, residue families, deferred learning-funnel residue, and spec-local audit spillover behind one shared path contract
- update the `HX-05` plan and work-plane artifacts so the feature can move directly to `T-2.3` relocation work

## Verification

- `uv run pytest tests/unit/test_state_plane_contract.py -q`
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`