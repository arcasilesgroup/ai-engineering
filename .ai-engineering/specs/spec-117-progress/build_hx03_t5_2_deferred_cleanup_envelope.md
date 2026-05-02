# Build Packet - HX-03 / T-5.2 / deferred-cleanup-envelope

## Task ID

HX-03-T-5.2-deferred-cleanup-envelope

## Objective

Document the cleanup that `HX-03` deliberately leaves for `HX-04`, `HX-06`, and `HX-12`, especially serialized root-overlay execution concerns, capability-level policy that still sits implicitly inside mirror helpers, and intentionally retained manual instruction families or compatibility affordances.

## Write Scope

- `.ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`
- `.ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts.md`
- `.ai-engineering/specs/spec-117-hx-12-engineering-standards-and-legacy-retirement.md`
- `.ai-engineering/specs/plan-117-hx-03-mirror-local-reference-model.md`
- `.ai-engineering/specs/current-summary.md`

## Minimum Change

- add one `Deferred Cleanup From HX-03` section to the `HX-03` spec that routes the remaining owned concerns explicitly
- add one matching deferred-cleanup section to each receiving spec (`HX-04`, `HX-06`, `HX-12`)
- update the `HX-03` plan and summary so `T-5.2` is recorded as complete and `T-5.3` becomes the active queue

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`

## Done Condition

- `HX-03` no longer hides deferred cleanup behind generic open questions or compatibility wording
- `HX-04`, `HX-06`, and `HX-12` each explicitly name the follow-on work they inherit from the mirror-contract cutover
- the work-plane remains internally consistent after the new routing references land