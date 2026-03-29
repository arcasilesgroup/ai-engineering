---
id: sub-005
parent: spec-088
title: "Runbook: Work Item Consolidation"
status: planning
files:
  - .ai-engineering/runbooks/consolidate.md
depends_on: []
---

# Sub-Spec 005: Runbook: Work Item Consolidation

## Scope

Create a new runbook `consolidate.md` following the existing runbook pattern (YAML frontmatter + markdown procedure). Type: operational, cadence: weekly. The runbook: (1) reads all open work items from GitHub Issues or Azure DevOps, (2) groups related items by semantic analysis of title+description, (3) presents groupings for user confirmation, (4) creates 1 consolidated task per confirmed group with a structured draft description (problem statement, all requirements, affected areas, acceptance criteria draft -- ready as input for /ai-brainstorm), (5) links originals to the new task via provider references, (6) closes originals with a link comment. Safety: never deletes items, always shows before confirming, bounded mutations (15 per run). Decision D-088-05.

## Exploration
[EMPTY -- populated by Phase 2]
