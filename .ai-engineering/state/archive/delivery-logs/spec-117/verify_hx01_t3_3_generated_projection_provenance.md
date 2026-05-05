# Verify HX-01 T-3.3 Generated Projection Provenance

## Ordered Verification

1. `uv run pytest tests/unit/test_state.py -k 'TestGeneratedProjectionMetadata'`
   - `PASS`
2. `uv run pytest tests/unit/test_state.py -k 'repo_ownership_map_snapshot_matches_default_contract'`
   - `PASS`
3. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`

## Key Signals

- Both committed state snapshots now advertise themselves as generated projections rather than silent authorities.
- The ownership snapshot still matches the shared control-plane contract after regeneration.
- The framework-capabilities snapshot still matches the computed capability catalog after its provenance metadata was added.