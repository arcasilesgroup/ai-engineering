# Build Packet - HX-01 / T-1.3 / control-plane-compatibility-boundary

## Task ID

HX-01-T-1.3-control-plane-compatibility-boundary

## Objective

Define the compatibility boundary that `HX-01` must preserve during migration: constitution path aliases, ownership/provenance field semantics, and root-entry-point anchors that need dual-read support before strict cutover.

## Minimum Change

- add one `Compatibility Boundary` section to the `HX-01` spec
- name the specific constitution-path, ownership/provenance, and root-entry anchor aliases that remain compatibility inputs during the migration window
- update the `HX-01` plan and work-plane so the next queue can move from boundary definition to failing coverage and implementation

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`