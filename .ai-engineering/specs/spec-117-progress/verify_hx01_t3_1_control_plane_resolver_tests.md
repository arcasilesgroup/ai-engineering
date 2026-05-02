# Verify HX-01 T-3.1 Control-Plane Resolver Tests

## Ordered Verification

1. `uv run pytest tests/unit/test_state.py -k 'TestControlPlaneContract'`
   - `PASS`

## Key Signals

- The shared resolver contract is now defined by executable unit tests rather than inferred from duplicated rule tables.
- Constitutional alias handling and manifest-root-entry ownership mapping are covered at the contract boundary.