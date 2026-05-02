# Build Packet - HX-03 / T-5.3 / focused-end-to-end-proof

## Task ID

HX-03-T-5.3-focused-end-to-end-proof

## Objective

Run the smallest proof bundle that still covers the strict Phase 5 mirror-contract cutover end to end: sync helper strictness, installer helper strictness, state and updater strictness, validator/provider resolution, mirror parity, and the required structural validations.

## Proof Bundle

- `uv run pytest tests/unit/test_sync_mirrors.py tests/integration/test_installer_integration.py tests/unit/test_state.py tests/unit/test_updater.py tests/unit/updater/test_update_provider_filtering.py tests/unit/validator/test_validator_provider_resolution.py`
- `uv run pytest tests/unit/test_validator.py -k 'non_source_repo_requires_manifest_contract'`
- `uv run ai-eng sync --check`
- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`

## Done Condition

- The strict Phase 5 contracts for sync, installer, validator, state, and updater all pass in one focused proof bundle.
- `HX-03` no longer has an open queue in its Phase 5 plan.