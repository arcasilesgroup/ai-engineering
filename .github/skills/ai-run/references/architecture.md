# AI Run Architecture

## Topology

```text
user
  -> ai-run
      -> ai-run-orchestrator
          -> intake provider
          -> ai-explore (baseline, then scoped deepening)
          -> ai-build (only writer)
          -> ai-review
          -> ai-verify
          -> ai-board-sync
          -> ai-pr
          -> ai-resolve-conflicts
```

## Core Boundaries

- `ai-run` owns sequencing, run state, branch topology, and resume.
- `ai-run-orchestrator` is read-heavy and coordination-heavy. It does not become a second implementation stack.
- `ai-build` remains the only write-capable implementation agent.
- `ai-review` and `ai-verify` are mandatory gates, not optional post-processing.
- `ai-pr` owns final remote delivery and CI watch/fix.

## Consolidation Model

### Single-item mode

```text
work/<item-id>/<slug> -> PR -> protected default branch
```

### Multi-item mode

```text
work/<run-id>/<item-id>/<slug>
  -> local promotion
  -> run/<run-id>
  -> PR
  -> protected default branch
```

Local consolidation exists to reduce CI churn. Remote PR delivery exists to preserve protected-branch governance.

## Gate Layers

1. Item-level gate
   - targeted checks
   - `ai-review`
   - `ai-verify platform`
2. Integration-level gate
   - affected local checks
   - `ai-review`
   - `ai-verify platform`
3. Final delivery gate
   - final local checks
   - `ai-review`
   - `ai-verify platform`
   - remote CI via `ai-pr`

## Provider Split

- `work_items/*` behavior:
  - intake
  - normalization
  - hierarchy and close policy
  - lifecycle sync
- `delivery/*` behavior:
  - PR creation/update
  - auto-complete
  - remote status polling
  - merge/provider-specific completion

`manifest.yml` supplies policy and selected providers. Handlers implement behavior.
