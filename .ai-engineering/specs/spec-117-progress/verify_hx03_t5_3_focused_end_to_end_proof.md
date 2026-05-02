# Verify HX-03 T-5.3 Focused End-To-End Proof

## Ordered Verification

1. `uv run pytest tests/unit/test_sync_mirrors.py tests/integration/test_installer_integration.py tests/unit/test_state.py tests/unit/test_updater.py tests/unit/updater/test_update_provider_filtering.py tests/unit/validator/test_validator_provider_resolution.py`
   - `PASS` (`225 passed`)
2. `uv run pytest tests/unit/test_validator.py -k 'non_source_repo_requires_manifest_contract'`
   - `PASS` (`1 passed`)
3. `uv run ai-eng sync --check`
   - `PASS`
4. `uv run ai-eng validate -c cross-reference`
   - `PASS`
5. `uv run ai-eng validate -c file-existence`
   - `PASS`

## Key Signals

- The strict Phase 5 mirror-contract cutover now holds across sync, installer, validator, state, and updater consumers in one proof bundle instead of isolated local slices.
- The proof bundle exercised the stale-test repairs needed for the new strict contract, including provider-resolution fixtures and cross-reference expectations that now include manifest-declared mirror paths.
- `HX-03` closes with the repository still structurally green on `sync --check`, cross-reference, and file-existence validation.