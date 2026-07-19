---
name: ai-sprint
description: "Manages sprint lifecycle: plans a new sprint from backlog, runs data-driven retros comparing planned vs shipped, checks mid-sprint goal status, generates sprint review presentations. Works with GitHub Projects and Azure DevOps. Trigger for 'start sprint planning', 'kick off the sprint', 'lets do the retro', 'what did we deliver last sprint', 'sprint goals check', 'generate the sprint review deck'. Not for daily standup; use /ai-standup instead. Not for solo PR retro; use /ai-learn instead."
effort: mid
argument-hint: "plan|retro|goals|review [--sprint name]"
requires:
  bins:
  - python3
  anyBins:
  - gh
  - az
---


# Sprint

Sprint lifecycle: plan from backlog, run data-driven retros (planned vs shipped), track goals, generate review decks. Bridges spec-level planning and day-to-day delivery, storing each sprint at `.ai-engineering/sprints/{name}.md` (naming `YYYY-wNN` ISO week, or custom).

```
/ai-sprint plan --sprint 2026-w12          # plan sprint for week 12
/ai-sprint retro --sprint 2026-w11         # retro on last sprint
/ai-sprint goals                           # check current sprint goals
/ai-sprint review --sprint 2026-03         # generate March 2026 review deck
/ai-sprint review --iteration "Sprint 12"  # named iteration review deck
```

## Pre-conditions (MANDATORY)

1. Read `manifest.yml` `work_items` section; determine active provider (`github` | `azure_devops`).
2. Read `.ai-engineering/reference/gather-activity-data.md` for canonical git log, PR query, and work-item commands.
3. Provider config: **Azure DevOps** filters by `area_path`, auto-detects current `iteration_path`; **GitHub** filters by `team_label`, uses milestones for sprint boundaries.
4. Use all standard and custom fields the platform provides.

## Workflow

Principles: §10.4 DRY (single `gather-activity-data.md` source for all activity queries); §10.1 KISS (each mode is one linear pass).

### plan — new sprint planning

1. **Review backlog** — open specs, GitHub Issues/Projects, prioritized items (priority labels or manual ranking).
2. **Assess capacity** — count working days; factor known absences/blockers from decision-store.
3. **Select items** — highest-priority items that fit capacity; apply RICE scores.
4. **Estimate effort** — size labels (XS/S/M/L/XL); flag items missing estimates.
5. **Draft board** — planned items grouped by priority:

```markdown
## Sprint: {name} ({start} - {end})

### Goals
1. {Goal 1 -- measurable outcome}

### Planned Items
| # | Priority | Size | Item | Spec |
|---|----------|------|------|------|
| 1 | p1 | M | Fix hook installation on Windows | spec-054 |
```

6. **Store** — save to `.ai-engineering/sprints/{name}.md`.

### retro — sprint retrospective

1. **Load plan** — read `.ai-engineering/sprints/{name}.md`.
2. **Collect actuals** — via `gather-activity-data.md` commands: merged PRs, completed spec tasks, commit history for the period.
3. **Compare planned vs shipped** — completed / carried-over / side quests (unplanned) / descoped.
4. **Analyze patterns** — estimation accuracy (actual vs size), side-quest ratio (unplanned/total), velocity trend vs prior sprints.
5. **Document learnings** — what went well, what to change, action items.
6. **Output** — append retro section to the sprint file.

### goals — goal tracking

1. **Load active sprint** from `.ai-engineering/sprints/`.
2. **Check progress** — per goal, assess signals (merged PRs, closed issues, spec-task status).
3. **Report** — traffic-light per goal: green (on track) / yellow (at risk) / red (blocked).

### review — review presentation

Branded PowerPoint via python-pptx. NEW script each invocation tailored to current data — never reuse a static template.

1. **Determine period** — `--sprint YYYY-MM` (calendar month), `--iteration <name>` (query provider for dates), or default to current month.
2. **Gather data** — `gather-activity-data.md` commands for work items + git activity; quality metrics via `pytest --co -q` and `ruff check . --statistics`; compare against `manifest.yml` thresholds.
3. **Generate script** — brand constants `AI_BG_DARK=#0B1120`, `AI_ACCENT=#00D4AA`, `AI_PRIMARY=#1E3A5F`; typography `JetBrains Mono` (headings), `Inter` (body); layout 16:9, 13.333"×7.5".
4. **Slide structure (8-14)** — Title → Sprint Overview (KPI cards) → Feature Deep-Dives (one per major spec) → Quality Metrics → Risks & Next Sprint → Q&A. Every slide requires `set_notes()`.
5. **Execute** — write `.ai-engineering/runtime/presentations/generate_sprint_review.py`, run it, output `sprint-review-YYYY-MM.pptx` alongside.

Review common mistakes: reusing an old script verbatim, missing speaker notes, wrong palette, skipping pre-conditions, hardcoding dates.

## Examples

User: "lets do the retro for the sprint that just ended"

```
/ai-sprint retro --sprint 2026-w18
```

Compares planned vs shipped, surfaces velocity trends, identifies blockers, writes the retro section into `.ai-engineering/sprints/2026-w18.md`.

## Integration

Called by: user directly. Calls: `gh project item-list`, `az boards query`, `/ai-slides` (for `review` mode). See also: `/ai-standup` (daily slice), `/ai-prose content sprint-review`, `/ai-board discover`.

$ARGUMENTS
