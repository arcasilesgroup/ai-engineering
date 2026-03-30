# Handler: Phase 4 -- EXECUTE, REVIEW, VERIFY, PROMOTE

## Purpose

Execute waves through `ai-build`, converge each item with review and verify, and promote passing changes into the integration surface.

## Procedure

### Step 1 -- Dispatch `ai-build`

For each runnable item in wave order:

1. Dispatch `ai-build` with the item packet from Phase 3.
2. Keep file boundaries explicit.
3. Require targeted local checks before the item can advance.

`ai-run` never becomes a second writer.

### Step 2 -- Item-level gate

After `ai-build` completes:

1. Run deterministic checks from the item packet.
2. Run `ai-review`.
3. Run `ai-verify platform`.

If blocker or critical findings remain, fix and retry. Max 2 remediation rounds per item.

### Step 3 -- Local promotion

Promotion rules:

- `single-item` mode -> keep the item branch as the delivery branch
- `multi-item` mode -> promote the passing item branch into `run/<run-id>`

Every promotion updates:

- promotion history
- changed files
- integration status
- remaining queue

### Step 4 -- Integration-level gate

After each promotion into `run/<run-id>`:

1. Run affected local checks.
2. Run `ai-review` on the integrated diff.
3. Run `ai-verify platform` on the integrated diff.

If promotion destabilizes the run branch:

- fix on the integration surface if safe
- otherwise roll back the promotion and mark the item blocked

### Step 5 -- Re-plan between waves

Recompute:

- remaining overlap risks
- dependency edges
- wave assignments

The run manifest is the source of truth.

## Gate

Phase 4 passes when:

- every promoted item has a report
- the integration surface is green enough to deliver
- blocked items are explicitly recorded

## Reports

Each item writes `.ai-engineering/runs/<run-id>/items/<item-id>/report.md` with:

- changed files
- checks run
- review findings and fixes
- verify findings and fixes
- residual risks
