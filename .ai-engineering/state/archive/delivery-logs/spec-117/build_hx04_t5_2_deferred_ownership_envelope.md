# Build Packet - HX-04 / T-5.2 / deferred-ownership-envelope

## Task ID

HX-04-T-5.2-deferred-ownership-envelope

## Objective

Document the explicit deferred ownership that remains with `HX-05` and `HX-11` after the local kernel cutover.

## Minimum Change

- extend the `HX-04` spec with one explicit deferred-ownership section after the cutover slices are complete
- name the still-deferred `HX-05` state-plane concerns: event vocabulary, task traces, scorecards, and durable blocked-state projection
- name the still-deferred `HX-11` verification and eval concerns: check taxonomy, eval packs, CI-only aggregation, and benchmark-style measurement bundles
- keep the section declarative so it clarifies ownership without reopening implementation scope inside `HX-04`

## Verification

- `uv run ai-eng validate -c manifest-coherence`