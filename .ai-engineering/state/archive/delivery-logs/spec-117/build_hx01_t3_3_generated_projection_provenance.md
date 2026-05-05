# Build Packet - HX-01 / T-3.3 / generated-projection-provenance

## Task ID

HX-01-T-3.3-generated-projection-provenance

## Objective

Make `ownership-map.json` and `framework-capabilities.json` explicit generated projections of the normalized control-plane contracts rather than implicit peer authorities.

## Minimum Change

- add generated-projection provenance metadata to ownership and capability snapshot models
- regenerate the committed `ownership-map.json` and `framework-capabilities.json` from code instead of hand-editing them
- keep repo-level parity checks green after the provenance metadata lands

## Verification

- `uv run pytest tests/unit/test_state.py -k 'TestGeneratedProjectionMetadata'`
- `uv run pytest tests/unit/test_state.py -k 'repo_ownership_map_snapshot_matches_default_contract'`
- `uv run ai-eng validate -c manifest-coherence`