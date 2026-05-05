# Verify HX-03 T-5.1 Strict Root Entry Ownership Contract

## Ordered Verification

1. `uv run pytest tests/unit/test_state.py tests/unit/test_updater.py`
   - `PASS`

## Key Signals

- `default_ownership_map()` now treats governed root entry points as manifest-owned data instead of synthesizing them from historical defaults.
- The updater merge path inherits the same strict contract, so ownership repair no longer reintroduces root-entry fallback rules when metadata is absent.
- The repo snapshot test now compares `.ai-engineering/state/ownership-map.json` against the manifest-driven ownership contract, aligning unit coverage with `manifest-coherence` validation.