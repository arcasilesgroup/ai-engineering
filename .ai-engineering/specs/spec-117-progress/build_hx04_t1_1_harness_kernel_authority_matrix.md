# Build Packet - HX-04 / T-1.1 / harness-kernel-authority-matrix

## Task ID

HX-04-T-1.1-harness-kernel-authority-matrix

## Objective

Consolidate the `HX-04` exploration evidence into one governed feature artifact that names the current local gate authorities, adapter layers, result models, serialized artifact families, and the explicit cut line with `HX-05` and `HX-11`.

## Minimum Change

- add one `Authority Matrix And Cut Line` section to the `HX-04` spec
- classify the local gate engines, adapter layers, result models, and serialized artifact families the feature must converge or defer
- record the opening `T-1.1` artifact in the work-plane and move the queue to the `HX-04` guard review once structural validation is green

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`