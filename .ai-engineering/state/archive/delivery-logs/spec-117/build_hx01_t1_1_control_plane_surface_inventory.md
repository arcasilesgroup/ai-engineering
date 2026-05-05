# Build Packet - HX-01 / T-1.1 / control-plane-surface-inventory

## Task ID

HX-01-T-1.1-control-plane-surface-inventory

## Objective

Consolidate the `HX-01` exploration evidence into one governed feature artifact that names the exact constitutional, canonical, generated, and descriptive control-plane surfaces across the live repo and template workspace.

## Minimum Change

- add one `Control-Plane Surface Inventory` section to the `HX-01` spec
- enumerate the exact constitutional, canonical, generated, and descriptive surfaces relevant to the feature
- record `T-1.1` completion in the work-plane and move the queue to the next HX-01 build task while keeping guard/review tasks deferred for the current autonomous execution mode

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`