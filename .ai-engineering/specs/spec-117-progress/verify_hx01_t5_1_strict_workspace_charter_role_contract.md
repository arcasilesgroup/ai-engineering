# Verify HX-01 T-5.1 Strict Workspace Charter Role Contract

## Ordered Verification

1. `uv run pytest tests/unit/test_validator.py -k 'control_plane_authority_contract or workspace_charter_role_contract'`
   - `PASS`
2. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`

## Key Signals

- `manifest_coherence` now fails if the live or template workspace charter drifts away from the normalized subordinate-role language.
- The real repository passes the stricter `workspace-charter-role` check alongside the existing authority-table and projection-snapshot checks.
- The only non-failing note in the category remains the expected active-task-ledger warning for the current spec buffer.