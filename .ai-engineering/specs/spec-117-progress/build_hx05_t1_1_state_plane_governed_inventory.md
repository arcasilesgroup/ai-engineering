# Build Packet - HX-05 / T-1.1 / state-plane-governed-inventory

## Task ID

HX-05-T-1.1-state-plane-governed-inventory

## Objective

Open `HX-05` by consolidating the exploration evidence into one governed inventory of durable state, residue, spec-local evidence, event emitters, and report surfaces.

## Minimum Change

- sync the umbrella Phase 2 queue so `HX-04` is recorded complete and `HX-05` becomes the active feature wave
- add one governed inventory section to the `HX-05` spec covering global durable truth, derived projections, runtime residue, learning-funnel residue, and spec-local evidence currently parked under `.ai-engineering/state`
- record the writer families and report surfaces that `HX-05` must normalize without absorbing kernel or learning-funnel ownership
- persist the slice in the work-plane so `HX-05` can move directly to the `T-1.2` governance review

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`
- `uv run ai-eng validate -c manifest-coherence`