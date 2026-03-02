---
name: triage
description: "Auto-prioritize work items using severity hierarchy rules — classify p1/p2/p3, detect stale items, enforce throttle limits."
metadata:
  version: 1.0.0
  tags: [triage, prioritization, work-items, automation, backlog]
  ai-engineering:
    scope: read-write
    token_estimate: 600
---

# Triage

## Purpose

Prioritization logic for work items. Scans pending items from Azure Boards and/or GitHub Issues, applies severity hierarchy rules, assigns priority labels (p1/p2/p3), detects stale items, and enforces throttle limits to prevent backlog overload.

## Trigger

- `ai:plan` pipeline step 1 (triage check before discovery).
- `ai:triage` agent invocation.
- Scheduled backlog grooming.
- New work item batch needs prioritization.

## Procedure

### Step 1 — Scan Work Items

Read open work items from configured sources (via `work-item` skill).
Collect: ID, title, description, labels, state, created date, last activity date, assignee.

### Step 2 — Classify Priority

Apply severity hierarchy rules:

**p1 (Critical)** — requires immediate action:
- Active security vulnerabilities (CVE, secret exposure)
- Core functionality blockers (app won't start, data loss)
- Production incidents
- Compliance violations with deadline

**p2 (High)** — next sprint priority:
- Performance regressions (>20% degradation)
- Critical test failures (CI red)
- Compliance gaps without immediate deadline
- Breaking API changes affecting consumers

**p3 (Normal)** — backlog:
- Refactoring and tech debt reduction
- Minor improvements and DX enhancements
- Documentation updates
- Coverage gap closure
- Architecture improvements

### Step 3 — Apply Category Ordering

Within the same priority tier, order by category:

1. **security** — vulnerabilities, secret exposure, compliance
2. **bugs** — functional defects, regressions
3. **features** — new capabilities, user-facing improvements
4. **performance** — optimization, scaling
5. **tests** — coverage, test infrastructure
6. **architecture** — structural improvements, tech debt
7. **dx** — developer experience, tooling, documentation

### Step 4 — Label

Assign priority labels to each work item:
- `p1` for critical items
- `p2` for high-priority items
- `p3` for normal backlog items

Preserve human-assigned labels — only add/upgrade priority, never downgrade human assignments.

### Step 5 — Throttle Check

Count open items per priority:
- **10+ open items total**: halt p3 creation, surface warning
- **20+ open items total**: halt all non-p1 creation, escalate
- Report: `{total: N, p1: N, p2: N, p3: N, throttle: active|inactive}`

### Step 6 — Detect Stale

Flag items with no activity for 14+ days:
- **stale-blocked**: has "blocked" label, needs dependency resolution
- **stale-abandoned**: no assignee, no recent comments
- **stale-deprioritized**: was p2/p3, no progress

Recommend action: reassign, close, or re-prioritize.

### Step 7 — Report

Produce triage summary:

```
## Triage Report — YYYY-MM-DD

### Counts
| Priority | Open | New | Stale |
|----------|------|-----|-------|
| p1       | N    | N   | N     |
| p2       | N    | N   | N     |
| p3       | N    | N   | N     |

### Throttle Status
- Open items: N — throttle: ACTIVE|INACTIVE

### Actions Taken
- [list of label assignments, stale flags]

### Recommendations
- [next actions for human review]
```

## Output Contract

- Priority labels assigned to all scanned work items.
- Triage report with counts, throttle status, and recommendations.
- Stale item list with recommended actions.

## Governance Notes

- Human-assigned priorities are never downgraded automatically.
- Throttle limits are advisory — human can override.
- Security items (p1) are never throttled.
- Triage runs are logged for audit trail.
