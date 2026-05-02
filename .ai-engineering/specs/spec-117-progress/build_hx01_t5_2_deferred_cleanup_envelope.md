# Build Packet - HX-01 / T-5.2 / deferred-cleanup-envelope

## Task ID

HX-01-T-5.2-deferred-cleanup-envelope

## Objective

Document the remaining compatibility aliases and follow-on ownership that `HX-01` deliberately leaves to `HX-03`, `HX-05`, and `HX-06` so the control-plane normalization slice can close without absorbing mirror, state-plane, or capability-contract work.

## Write Scope

- `.ai-engineering/specs/spec-117-hx-01-control-plane-normalization.md`
- `.ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md`
- `.ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts.md`
- `.ai-engineering/specs/plan-117-hx-01-control-plane-normalization.md`
- `.ai-engineering/specs/current-summary.md`

## Minimum Change

- add one `Deferred Cleanup From HX-01` section to the `HX-01` spec that routes the remaining owned concerns explicitly
- add matching deferred-cleanup routing to the receiving specs for mirror-local alias guidance, state-plane alias-aware readers, and transitional capability projections
- update the `HX-01` plan and summary so `T-5.2` is recorded as complete and `T-5.3` becomes the active queue

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`

## Done Condition

- `HX-01` no longer hides alias retirement or follow-on ownership behind generic open questions
- `HX-03`, `HX-05`, and `HX-06` each explicitly name the control-plane cleanup they inherit from `HX-01`
- the work-plane remains internally consistent after the new routing references land