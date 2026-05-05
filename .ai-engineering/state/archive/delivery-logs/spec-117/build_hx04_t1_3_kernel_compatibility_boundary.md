# Build Packet - HX-04 / T-1.3 / kernel-compatibility-boundary

## Task ID

HX-04-T-1.3-kernel-compatibility-boundary

## Objective

Define the parity-first compatibility boundary that `HX-04` must preserve while it converges the local execution kernel: legacy hook-gate behavior, findings publication, CI-facing semantics, and residual outputs.

## Minimum Change

- add one `Compatibility Boundary` section to the `HX-04` spec
- name the specific hook-dispatch, findings-publication, CI-facing, and residual-output seams that remain compatibility inputs during migration
- update the `HX-04` plan and work-plane so the next queue can move from boundary definition to failing coverage and implementation

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`