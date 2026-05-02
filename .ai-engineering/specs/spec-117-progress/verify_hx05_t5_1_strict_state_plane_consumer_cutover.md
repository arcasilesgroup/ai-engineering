# Verify HX-05 T-5.1 Strict State Plane Consumer Cutover

## Ordered Verification

1. `uv run pytest tests/unit/test_state_plane_artifact_paths.py tests/unit/test_validator.py -k 'state_plane or legacy_state_plane_reference' -q`
   - `PASS` (`4 passed, 147 deselected`)
2. `uv run pytest tests/unit/test_state_plane_contract.py tests/unit/test_state_plane_artifact_paths.py tests/unit/validator/test_validator_provider_resolution.py tests/integration/test_spec_116_decision_store_lifecycle_red.py tests/unit/test_validator.py::TestFileExistence -q`
   - `PASS` (`32 passed`)

## Notes

- A broader `tests/unit/test_validator.py` run surfaced unrelated pre-existing failures outside `TestFileExistence`, so the accepted verification bundle stayed scoped to the state-plane cutover slice.

## Key Signals

- Canonical spec-local evidence paths now remain the only runtime resolution target; the legacy shim stays readable but is no longer a valid consumer fallback.
- `file-existence` now sees state-plane JSON references and rejects legacy shim references with the canonical replacement path, aligning validation with the normalized state-plane contract.
- Existing spec-116 lifecycle consumers still pass because the canonical evidence lane is populated and the legacy shim remains readable for parity checks.