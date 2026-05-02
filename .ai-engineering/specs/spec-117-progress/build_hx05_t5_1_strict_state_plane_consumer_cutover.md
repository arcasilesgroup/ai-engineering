# Build Packet - HX-05 / T-5.1 / strict-state-plane-consumer-cutover

## Task ID

HX-05-T-5.1-strict-state-plane-consumer-cutover

## Objective

Flip strict runtime and validation consumers to the normalized state-plane contract once compatibility shims and derived-view proofs are green.

## Minimum Change

- make the shared state-plane resolver return the canonical spec-local evidence path even when only the legacy shim is still on disk, so runtime readers no longer treat the shim as an authoritative fallback
- extend validator path parsing to include state-plane JSON references and fail legacy shim references with an explicit canonical replacement path
- keep the compatibility shim files readable for repository archaeology and transition safety, but remove them from the set of acceptable runtime or validation inputs
- pin the cutover with focused tests over the resolver contract and `file-existence` validation behavior

## Verification

- `uv run pytest tests/unit/test_state_plane_artifact_paths.py tests/unit/test_validator.py -k 'state_plane or legacy_state_plane_reference' -q`
- `uv run pytest tests/unit/test_state_plane_contract.py tests/unit/test_state_plane_artifact_paths.py tests/unit/validator/test_validator_provider_resolution.py tests/integration/test_spec_116_decision_store_lifecycle_red.py tests/unit/test_validator.py::TestFileExistence -q`