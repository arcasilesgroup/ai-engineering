# Build Packet - HX-01 / T-3.2 / shared-control-plane-resolver

## Task ID

HX-01-T-3.2-shared-control-plane-resolver

## Objective

Implement the shared control-plane resolver and migrate state, updater, and doctor ownership enforcement to consume it before validator tightening.

## Minimum Change

- add `ai_engineering.state.control_plane` as the shared control-plane contract surface
- move default ownership rule generation behind that resolver
- keep updater and doctor on the existing public helpers while making those helpers downstream of the shared contract

## Verification

- `uv run pytest tests/unit/test_state.py -k 'TestControlPlaneContract'`
- `uv run pytest tests/unit/test_updater.py -k 'uses_manifest_root_entry_point_contract or missing_root_entry_point_metadata'`
- `uv run pytest tests/unit/test_doctor_phases_state.py -k 'manifest_root_entry_point_contract_for_ownership_map'`
- `uv run pytest tests/unit/test_state.py -k 'repo_ownership_map_snapshot_matches_default_contract'`