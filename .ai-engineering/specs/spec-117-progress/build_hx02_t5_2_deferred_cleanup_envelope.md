# Build Packet - HX-02 / T-5.2 / deferred-cleanup-envelope

## Task ID

HX-02-T-5.2-deferred-cleanup-envelope

## Objective

Document the cleanup that `HX-02` deliberately leaves for `HX-04`, `HX-05`, and `HX-06`, including temporary compatibility views, task-state versus kernel-state boundaries, event-model limitations, and capability-enforcement gaps that remain intentionally unresolved after the work-plane cutover.

## Write Scope

- `.ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md`
- `.ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts.md`
- `.ai-engineering/specs/plan-117-hx-02-work-plane-and-task-ledger.md`
- `.ai-engineering/specs/current-summary.md`

## Minimum Change

- add one routing section to the `HX-02` spec that names the specific deferred cleanup handed to `HX-04`, `HX-05`, and `HX-06`
- add one `Deferred Cleanup From HX-02` section to each owning spec
- update the `HX-02` plan and summary so `T-5.2` is recorded as complete and `T-5.3` becomes the active queue

## Verification

- `uv run ai-eng validate -c cross-reference`
- `uv run ai-eng validate -c file-existence`

## Done Condition

- `HX-02` no longer hides deferred cleanup behind generic non-goals or open questions
- `HX-04`, `HX-05`, and `HX-06` each explicitly state the follow-on work inherited from the `HX-02` cutover
- work-plane documentation stays internally consistent after the new references land

## Execution Evidence

### Change Summary

- Added one deferred-cleanup routing section to the `HX-02` spec.
- Added matching `Deferred Cleanup From HX-02` sections to `HX-04`, `HX-05`, and `HX-06`.
- Recorded `T-5.2` as the completed cleanup-envelope slice in the work-plane artifacts.