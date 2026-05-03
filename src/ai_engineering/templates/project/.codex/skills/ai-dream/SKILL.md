---
name: ai-dream
description: "Consolidate memory: apply exponential decay (importance times 0.97^days), cluster duplicates with HDBSCAN, propose high-importance lessons for promotion (human review), retire stale entries. Run nightly or before major releases. Trigger for 'consolidate memory', 'run dream cycle', 'memory housekeeping', 'promote lessons', 'consolidar memoria'. NEVER auto-mutates LESSONS.md (D-118-04); writes proposals to memory-proposals.md."
model: sonnet
effort: medium
color: purple
argument-hint: "[--dry-run] [--decay-only]"
tags: [meta, memory, consolidation, housekeeping]
tools: Bash, Read
---


# Dream

## Purpose

Consolidation pass over the spec-118 memory layer. Applies exponential decay to knowledge object importance, clusters near-duplicates with HDBSCAN, marks supersedence chains, archives entries below the importance threshold (0.1), and proposes high-importance clusters for promotion to LESSONS.md (human review).

## When to Use

- Periodic maintenance (weekly, before releases).
- After ingesting a large batch of new lessons or decisions.
- When ai-eng memory status reports many unembedded or stale entries.

## Process

1. Run: uv run ai-eng memory dream --dry-run first. Inspect proposed promotions, supersedences, retirements.
2. Present the diff to the user. Ask for explicit approval.
3. On approval, run: uv run ai-eng memory dream (no --dry-run).
4. Show the path to memory-proposals.md and remind user to review before promoting any entries to canonical LESSONS.md.

## Hard Rules

- NEVER auto-mutate LESSONS.md (D-118-04). The dream loop only writes to .ai-engineering/instincts/memory-proposals.md.
- Small corpus early-exit: if active KO count < 30, dreaming applies decay only and emits dream_run with clusters_found=0 and outcome noop_small_corpus.
- Refuse-to-start on dim mismatch: if vector_map.embedding_model != active embedder, dreaming aborts. Tell user to run ai-eng memory repair --rebuild-vectors.

## Output Format

dream outcome (durationms)
  decayed=n      # entries the decay pass evaluated
  clusters=n     # HDBSCAN clusters found (>= min_cluster_size)
  promoted=n     # candidates added to memory-proposals.md
  retired=n      # archived (importance times decay < 0.1)
  proposals: .ai-engineering/instincts/memory-proposals.md

## Integration

- Calls: ai-eng memory dream (canonical CLI).
- Writes: .ai-engineering/state/memory.db (supersede / archive flags), .ai-engineering/instincts/memory-proposals.md (proposals).
- Audit: emits one memory_event/dream_run per call.
