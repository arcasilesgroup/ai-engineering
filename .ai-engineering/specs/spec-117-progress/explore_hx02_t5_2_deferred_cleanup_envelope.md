# Explore - HX-02 / T-5.2 / deferred-cleanup-envelope

## Slice Goal

Make the deferred follow-on work left intentionally outside `HX-02` explicit in the specs that own it so the work-plane migration no longer hides compatibility shims or event-model limitations behind implicit boundaries.

## Local Anchor

- `spec-117-hx-02-work-plane-and-task-ledger.md`
- `spec-117-hx-04-harness-kernel-unification.md`
- `spec-117-hx-05-state-plane-and-observability-normalization.md`
- `spec-117-hx-06-multi-agent-capability-contracts.md`

## Existing Gap

- `HX-02` already declares non-goals and open questions, but it does not enumerate the exact cleanup still owed by `HX-04`, `HX-05`, and `HX-06` after the resolver-and-ledger cutover.
- The target specs already describe their ownership boundaries, but they do not explicitly call out the compatibility views and state/event limitations left in place by `HX-02`.

## Falsifiable Hypothesis

If `HX-02` gains one short routing section that names the deferred cleanup now handed to `HX-04`, `HX-05`, and `HX-06`, and each owning spec gains one matching `Deferred Cleanup From HX-02` section, then the cleanup envelope becomes explicit without widening `HX-02` into those later features.

## Cheapest Discriminating Checks

- add one `Deferred Cleanup` section to each target spec and one routing section to `HX-02`
- rerun `uv run ai-eng validate -c cross-reference`
- rerun `uv run ai-eng validate -c file-existence`

## Proposed Write Scope

- `.ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md`
- `.ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts.md`