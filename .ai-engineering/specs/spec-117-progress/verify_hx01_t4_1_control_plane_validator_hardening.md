# Verify HX-01 T-4.1 Control-Plane Validator Hardening

## Ordered Verification

1. `uv run pytest tests/unit/test_validator.py -k 'control_plane_paths_present_pass or missing_project_constitution_template_fails or control_plane_authority_contract_passes or control_plane_authority_contract_drift_fails'`
   - `PASS`
2. `uv run ai-eng validate -c manifest-coherence`
   - `PASS`
3. `uv run ai-eng validate -c file-existence`
   - `PASS`
4. `uv run ai-eng validate -c mirror-sync`
   - `PASS`
5. `uv run ai-eng validate -c cross-reference`
   - `PASS`

## Key Signals

- The normalized control-plane contract is now checked directly in `manifest_coherence` instead of surfacing only through snapshot drift.
- Source-repo file existence now protects the canonical constitution/template paths added in Phase 2.
- The named Phase 4 validator categories remain green together after the hardening slice landed.