# Handler: Phase 2 -- ITEM DEEPENING AND MINI-PLANS

## Purpose

Produce headless per-item `spec.md` and `plan.md` artifacts inside the run state without touching the shared human working buffer.

## Procedure

### Step 1 -- Deepen only where needed

For each item in `needs_deepening` or `ready` with high ambiguity:

1. Dispatch scoped `ai-explore`.
2. Focus on the predicted write surface and boundary files only.
3. Record new findings back into the run manifest.

### Step 2 -- Mini-spec per item

Write `.ai-engineering/runs/<run-id>/items/<item-id>/spec.md` with:

- problem summary
- acceptance criteria
- assumptions and unknowns
- 2-3 implementation approaches
- selected approach and rationale
- explicit non-goals

Do not write to `.ai-engineering/specs/spec.md`.

### Step 3 -- Mini-plan per item

Write `.ai-engineering/runs/<run-id>/items/<item-id>/plan.md` with:

- ordered tasks
- file scope
- forbidden scope
- required checks
- close policy and work-item refs
- rollback notes

Do not write to `.ai-engineering/specs/plan.md`.

### Step 4 -- Classify execution mode

Every item plan must route the eventual `ai-build` packet to one primary mode:

- `code`
- `test`
- `debug`

Use the dominant task type, not the issue label alone.

### Step 5 -- Final item state

After planning, each item must be one of:

- `planned`
- `blocked`
- `deferred`

## Gate

Phase 2 passes when every non-blocked item has:

- `items/<item-id>/spec.md`
- `items/<item-id>/plan.md`
- explicit file boundaries
- explicit checks

## Behavioral Negatives

- Do not reuse the shared global spec buffer.
- Do not skip option analysis for ambiguous items.
- Do not keep an item in `ready` once planning is complete.
