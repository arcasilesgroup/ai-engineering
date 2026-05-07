---
name: ai-sprint
description: "Use to manage sprint lifecycle: plan a new sprint from backlog, run a data-driven retrospective comparing planned vs shipped, check goal status mid-sprint, or generate sprint review presentations. Trigger for 'start sprint planning', 'kick off the sprint', 'let's do the retro', 'what did we deliver last sprint?', 'are we on track?', 'sprint goals check', 'generate the sprint review deck'. Works with GitHub Projects and Azure DevOps."
effort: high
argument-hint: "plan|retro|goals|review [--sprint <name>]"
mode: agent
requires:
  anyBins:
  - gh
  - az
  bins:
  - python3
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-sprint/SKILL.md
edit_policy: generated-do-not-edit
---



# Sprint

## Purpose

Sprint lifecycle management: plan new sprints from backlog, run data-driven retrospectives comparing planned vs shipped, and track sprint-level goals. Bridges the gap between spec-level planning and day-to-day delivery.

## Trigger

- Command: `/ai-sprint plan|retro|goals`
- Context: sprint boundary (start or end of sprint), goal tracking mid-sprint.

## Pre-conditions (MANDATORY)

1. Read `.ai-engineering/manifest.yml` — `work_items` section.
2. Determine active provider (`github` or `azure_devops`).
3. Read `.ai-engineering/contexts/gather-activity-data.md` for the canonical git log, PR query, and work item commands.
4. Use provider-specific config:
   - **Azure DevOps**: filter by `area_path`, auto-detect current `iteration_path`
   - **GitHub**: filter by `team_label`, use milestones for sprint boundaries
5. Use all standard and custom fields the platform provides.

## Modes

### plan -- New sprint planning

1. **Review backlog** -- read open specs, GitHub Issues/Projects, and prioritized items from the backlog (GitHub Issues with priority labels or manual ranking).
2. **Assess capacity** -- count working days in sprint, factor in known absences or blockers from decision-store.
3. **Select items** -- pull highest-priority items that fit capacity. Apply RICE scores from backlog prioritization.
4. **Estimate effort** -- use size labels (XS/S/M/L/XL) from issue standard. Flag items missing size estimates.
5. **Draft sprint board** -- output planned items grouped by priority:

```markdown
## Sprint: {name} ({start} - {end})

### Goals
1. {Goal 1 -- measurable outcome}
2. {Goal 2 -- measurable outcome}

### Planned Items
| # | Priority | Size | Item | Spec |
|---|----------|------|------|------|
| 1 | p1 | M | Fix hook installation on Windows | spec-054 |
| 2 | p2 | L | Add telemetry dashboard | spec-054 |
```

6. **Store** -- save sprint plan to `.ai-engineering/sprints/{name}.md`.

### retro -- Sprint retrospective

1. **Load sprint plan** -- read `.ai-engineering/sprints/{name}.md`.
2. **Collect actuals** -- use the commands from `.ai-engineering/contexts/gather-activity-data.md` to scan merged PRs, completed spec tasks, and commit history for the sprint period.
3. **Compare planned vs shipped**:
   - Items completed as planned
   - Items carried over (not finished)
   - Side quests (unplanned work that entered the sprint)
   - Items descoped or deprioritized
4. **Analyze patterns**:
   - Estimation accuracy: actual effort vs estimated size
   - Side quest ratio: unplanned / total items delivered
   - Velocity trend: items completed vs previous sprints
5. **Document learnings** -- what went well, what to change, action items.
6. **Output** -- retrospective report appended to `.ai-engineering/sprints/{name}.md`.

### goals -- Sprint goal tracking

1. **Load active sprint** -- find current sprint from `.ai-engineering/sprints/`.
2. **Check goal progress** -- for each goal, assess completion signals (merged PRs, closed issues, spec task status).
3. **Report** -- traffic-light status per goal: green (on track), yellow (at risk), red (blocked/behind).

### review -- Sprint review presentation

Generate a branded sprint review PowerPoint deck using python-pptx. Each invocation produces a NEW script tailored to current data — never reused from a static template.

1. **Determine sprint period** — resolve date range: `--sprint YYYY-MM` (calendar month), `--iteration <name>` (query provider for dates), or default to current month.
2. **Gather data** — use commands from `.ai-engineering/contexts/gather-activity-data.md` for work items and git activity. Collect quality metrics via `pytest --co -q` and `ruff check . --statistics`. Compare against thresholds in `manifest.yml`.
3. **Generate python-pptx script** — new script each time. Brand constants: `AI_BG_DARK=#0B1120`, `AI_ACCENT=#00D4AA`, `AI_PRIMARY=#1E3A5F`. Typography: `JetBrains Mono` (headings), `Inter` (body). Layout: 16:9, 13.333"×7.5".
4. **Slide structure (8-14 slides)**: Title → Sprint Overview (KPI cards) → Feature Deep-Dives (one per major spec) → Quality Metrics → Risks & Next Sprint → Q&A. Every slide requires `set_notes()` for presenter view.
5. **Execute** — write to `docs/presentations/generate_sprint_review.py`, run it, output `docs/presentations/sprint-review-YYYY-MM.pptx`.

**Common mistakes**: reusing old script verbatim, missing speaker notes, wrong color palette, skipping pre-conditions, hardcoding dates.

## Arguments

Modes (`plan`, `retro`, `goals`, `review`) per Modes above. Flags:
- `--sprint <name>` — sprint identifier (e.g., `2026-w12`) or month (`YYYY-MM`); defaults to current.
- `--iteration <name>` — iteration name (queries provider for dates, used with `review` mode).

## Quick Reference

```
/ai-sprint plan --sprint 2026-w12          # plan sprint for week 12
/ai-sprint retro --sprint 2026-w11         # retro on last sprint
/ai-sprint goals                           # check current sprint goals
/ai-sprint review --sprint 2026-03         # generate March 2026 review deck
/ai-sprint review --iteration "Sprint 12"  # named iteration review deck
```

## Storage

- Sprint files: `.ai-engineering/sprints/{name}.md`
- Naming convention: `YYYY-wNN` (ISO week) or custom names

## Integration

- **See also**: `/ai-standup` (daily activity detail)

$ARGUMENTS
