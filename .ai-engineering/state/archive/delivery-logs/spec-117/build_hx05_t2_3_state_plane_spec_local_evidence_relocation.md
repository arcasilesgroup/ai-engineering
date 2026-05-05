# Build Packet - HX-05 / T-2.3 / state-plane-spec-local-evidence-relocation

## Task ID

HX-05-T-2.3-state-plane-spec-local-evidence-relocation

## Objective

Move the parked `spec-116` audit and classification artifacts out of the global state plane into the canonical spec-local evidence lane, while preserving readable compatibility shims for any readers that still probe `.ai-engineering/state/` directly.

## Minimum Change

- add canonical relocation mapping and shared path resolution to `state.control_plane`
- materialize canonical `spec-116` evidence under `.ai-engineering/specs/evidence/spec-116/`
- cut the `spec-116` decision-store lifecycle reader to the shared resolver and record the relocation in the `HX-05` work-plane artifacts

## Verification

- `uv run pytest tests/unit/test_state_plane_contract.py tests/unit/test_state_plane_artifact_paths.py tests/integration/test_spec_116_decision_store_lifecycle_red.py -q`
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`