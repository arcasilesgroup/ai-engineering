# Verify HX-01 T-3.2 Shared Control-Plane Resolver

## Ordered Verification

1. `uv run pytest tests/unit/test_state.py -k 'TestControlPlaneContract'`
   - `PASS`
2. `uv run pytest tests/unit/test_updater.py -k 'uses_manifest_root_entry_point_contract or missing_root_entry_point_metadata'`
   - `PASS`
3. `uv run pytest tests/unit/test_doctor_phases_state.py -k 'manifest_root_entry_point_contract_for_ownership_map'`
   - `PASS`
4. `uv run pytest tests/unit/test_state.py -k 'repo_ownership_map_snapshot_matches_default_contract'`
   - `PASS`

## Key Signals

- `default_ownership_paths(...)` and `default_ownership_map(...)` are now downstream renderings of the shared control-plane contract.
- Updater and doctor still honor manifest-root-entry metadata after the resolver cutover.
- The committed ownership-map snapshot remains identical to the shared resolver output, so the migration did not introduce drift.