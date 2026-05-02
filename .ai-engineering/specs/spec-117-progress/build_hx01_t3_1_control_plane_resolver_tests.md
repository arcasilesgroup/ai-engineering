# Build Packet - HX-01 / T-3.1 / control-plane-resolver-tests

## Task ID

HX-01-T-3.1-control-plane-resolver-tests

## Objective

Write failing tests for a shared ownership/provenance resolver that covers constitutional aliases, manifest root-entry metadata, and default ownership-path derivation.

## Minimum Change

- add focused state tests for a shared `resolve_control_plane_contract(...)` API
- cover the constitutional primary path plus the workspace-charter compatibility alias
- assert that `default_ownership_paths(...)` is downstream of the shared resolver rather than a separate rule table

## Verification

- `uv run pytest tests/unit/test_state.py -k 'TestControlPlaneContract'`