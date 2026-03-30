---
id: sub-004
parent: spec-090
title: "Improvement Funnel - Proposals + Work Items"
status: planned
files: [".ai-engineering/instincts/proposals.md", ".claude/skills/ai-instinct/SKILL.md"]
depends_on: [sub-002, sub-003]
---

# Sub-Spec 004: Improvement Funnel - Proposals + Work Items

## Scope

Implements D-090-11 (improvement funnel). Defines proposals.md format and --review steps 4-5: evaluate instincts cross-referenced with LESSONS.md + project context, generate proposals for skills/agents/hooks, create work items via GitHub/Azure DevOps.

## Exploration

### Existing Files
- `ai-board-sync/SKILL.md` — Pattern for work item creation. Step 1: reads manifest work_items. Step 3: GitHub Projects v2 via `gh project item-edit`, Azure DevOps via `az boards work-item update`. Reuse this pattern.
- `manifest.yml` work_items section — Lines 27-76. Provider: github. github_project number: 4. Custom fields: Priority, Size, Estimate, Start/Target dates. hierarchy: feature→never_close, task/bug→close_on_pr.
- `proposals.md` — NEW file, does not exist yet.

### Patterns to Follow
- ai-board-sync work item creation pattern: read provider, create via CLI (gh/az), link back.
- Duplicate detection: `gh issue list --label "ai-engineering,instinct" --state open --json title` before creating.

### Dependencies Map
- Requires instincts.yml v2 schema (sub-002) for filtering by confidence/evidenceCount.
- Requires --review procedure (sub-003) for integration as steps 4-5.
- Requires LESSONS.md at new path (sub-001) for cross-reference.

### Risks
- Work item creation requires `gh` CLI authenticated. Fail-open if not available.
- Duplicate detection by title match may miss renamed proposals.
