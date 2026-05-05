# Verify HX-05 T-2.1 State-Plane Contract Invariants

## Ordered Verification

1. `uv run pytest tests/unit/test_state_plane_contract.py -q`
   - `FAIL` (expected RED)

## Key Signals

- All four new contract tests fail for the same reason: the `StatePlaneArtifactClass` and `resolve_state_plane_contract(...)` exports do not exist yet in `ai_engineering.state.control_plane`.
- The failure is local and discriminating rather than noisy; no unrelated runtime breakage masks the missing state-plane seam.
- `T-2.2` now owns implementing the shared state-plane classification contract so durable-state membership, residue handling, and spec-local evidence relocation stop being inferred from scattered paths.