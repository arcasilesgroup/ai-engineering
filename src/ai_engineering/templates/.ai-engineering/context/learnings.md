# Learnings

## Update Metadata

- Rationale: preserve institutional learning with compact, reusable entries.
- Expected gain: faster adaptation and lower context overhead.
- Potential impact: previous long-form narratives are condensed.

Living record of high-signal lessons from implementation and usage.

## Entry Template

```text
Date:
Category: architecture | security | devex | testing | process
Observation:
Impact:
Action taken:
Updated files:
```

## Current Learnings

### 2026-02-08 - Context-first reduced ambiguity

- Category: process.
- Observation: architecture-first planning reduced implementation uncertainty.
- Impact: positive planning speed and fewer contradictions.
- Action taken: canonicalized ownership model and state contracts.
- Updated files: architecture, planning, manifest.

### 2026-02-08 - Explicit ownership prevents updater risk

- Category: architecture.
- Observation: path-level ownership contracts are required to avoid accidental overwrites.
- Impact: high governance safety gain.
- Action taken: added ownership map as system-managed contract.
- Updated files: state/ownership-map.json and related docs.
