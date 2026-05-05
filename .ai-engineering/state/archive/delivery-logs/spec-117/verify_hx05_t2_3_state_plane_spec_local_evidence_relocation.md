# Verify HX-05 T-2.3 State-Plane Spec-Local Evidence Relocation

## Commands

- `uv run pytest tests/unit/test_state_plane_contract.py tests/unit/test_state_plane_artifact_paths.py tests/integration/test_spec_116_decision_store_lifecycle_red.py -q`
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`

## Results

- `tests/unit/test_state_plane_contract.py tests/unit/test_state_plane_artifact_paths.py tests/integration/test_spec_116_decision_store_lifecycle_red.py`: `PASS`
- `cross-reference`: `PASS`
- `file-existence`: `PASS`

## Outcome

- The canonical `spec-116` audit artifacts now live under `.ai-engineering/specs/evidence/spec-116/`, while the legacy `.ai-engineering/state/` copies remain readable compatibility shims.
- `state.control_plane` now resolves spec-local evidence reads through the canonical lane first, and `HX-05` can move safely into `T-3.1` event-contract RED coverage.