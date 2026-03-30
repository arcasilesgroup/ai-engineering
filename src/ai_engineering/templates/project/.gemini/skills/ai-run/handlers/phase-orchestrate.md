# Handler: Phase 3 -- DAG, WAVES, AND BUILD PACKETS

## Purpose

Convert item plans into a safe execution graph and bounded `ai-build` packets.

## Procedure

### Step 1 -- Build the overlap matrix

For every pair of planned items, compare:

- predicted write surface
- shared artifacts
- lockfiles
- root configs
- workflows
- migrations
- generated files
- producer/consumer dependencies

Record the matrix in the run manifest.

### Step 2 -- Construct the DAG

Create edges for:

- explicit logical dependencies
- producer -> consumer relationships
- overlapping governance surfaces
- serialize-on-uncertainty decisions

Default rule: if uncertainty is non-trivial, serialize.

### Step 3 -- Assign waves

Group items into waves only when all of the following are true:

- write surfaces are confidently disjoint
- no shared artifact requires serialization
- no dependency edge exists
- the baseline exploration does not indicate hidden coupling

### Step 4 -- Build `ai-build` packets

Each runnable item gets a packet with:

```yaml
task: "<item-id>"
description: "<selected approach>"
mode: code|test|debug
scope:
  files: ["..."]
  boundaries: ["..."]
constraints:
  - "..."
contexts:
  languages: ["..."]
  frameworks: ["..."]
  team: ["..."]
gate:
  local: ["targeted checks"]
  post: ["ai-review", "ai-verify platform"]
```

### Step 5 -- Prepare branch topology

Assign:

- `work/<run-id>/<item-id>/<slug>` for each active item
- `run/<run-id>` for multi-item integration

## Gate

Phase 3 passes when:

- the overlap matrix exists
- the DAG exists
- every runnable item has a packet
- the branch plan exists in the manifest

## Failure Modes

| Condition | Action |
|-----------|--------|
| All items blocked or deferred | Stop with a blocker report. |
| Overlap model is inconclusive | Serialize the queue instead of guessing. |
