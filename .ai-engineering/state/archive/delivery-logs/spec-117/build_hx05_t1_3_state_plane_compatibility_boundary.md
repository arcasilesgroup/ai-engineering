# Build Packet - HX-05 / T-1.3 / state-plane-compatibility-boundary

## Task ID

HX-05-T-1.3-state-plane-compatibility-boundary

## Objective

Define the compatibility-first boundary that `HX-05` must preserve for quasi-authoritative current files, event-writer paths, and downstream report consumers before any state relocation begins.

## Minimum Change

- add one `Compatibility Boundary` section to the `HX-05` spec with a compatibility matrix covering generated projections, residue outputs, the durable audit append path, and spec-local audit spillover still parked under global state
- carry forward the `T-1.2` guard notes so downstream consumers stay tolerant of missing residue or regenerated projections and the ordered publish families remain unchanged
- update the `HX-05` plan and work-plane artifacts so the feature can move directly to `T-2.1` RED coverage

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`