---
name: ai-postmortem
description: "Documents production incidents, outages, degradations, and near-misses using the DERP format (Detection, Escalation, Recovery, Prevention) with targeted interview questions per phase. Trigger for 'we had an incident', 'write up the outage', 'something went wrong in prod', 'postmortem', 'near-miss analysis', 'incident report'. Not for customer support investigations; use /ai-support instead. Not for internal dev bugs; use /ai-debug instead."
effort: mid
argument-hint: "start|continue [id]|find [query]|generate"
---


# Postmortem

Use this to document a production incident, outage, degradation, or near-miss as a structured, blameless postmortem using the DERP model (Detection, Escalation, Recovery, Prevention). Postmortems are stored at `.ai-engineering/postmortems/{id}.md` (ID `PM-YYYY-NNN`) and move `draft` → `in-review` (all DERP sections complete) → `complete` (action items assigned).

```
/ai-postmortem start                  # begin new postmortem
/ai-postmortem continue PM-2026-001   # resume in-progress postmortem
/ai-postmortem find database          # search past postmortems
/ai-postmortem generate               # generate from existing context
```

## Workflow

Principles: §10.4 DRY (one DERP template + interview script, no per-incident ad-hoc format).

Interview rule: ask ONE DERP section at a time; wait for answers before advancing. If the user pastes a timeline covering multiple phases, extract into each section rather than re-asking. Only interview for sections that remain incomplete.

### start — new postmortem

1. **Assign ID** `PM-YYYY-NNN`; set status `draft`.
2. **Scaffold** `.ai-engineering/postmortems/{id}.md` from the DERP template.
3. **Detection** — when first detected? how (monitoring / user report / manual)? time from start to detection? what monitoring should have caught it earlier?
4. **Escalation** — who was notified and when? was the escalation path appropriate? were the right people involved at the right time?
5. **Recovery** — what actions restored service? total downtime/impact duration? was there a rollback, and what was the procedure?
6. **Prevention** — root cause (5-Whys if needed); what changes prevent recurrence; action items with owners + deadlines.

### continue <id> — resume

1. **Load** `.ai-engineering/postmortems/{id}.md`.
2. **Find gap** — first incomplete DERP section.
3. **Resume interview** from that section.

### generate — from existing notes

1. **Collect** incident-related commits, PRs, pasted Slack threads, and context notes.
2. **Draft** DERP sections from available data; mark gaps `[NEEDS INPUT]`.
3. **Review** — present the draft for validation before saving.

### find [query] — search

1. **Search** `.ai-engineering/postmortems/*.md` for matching content.
2. **List** ID, title, date, status, root-cause summary.

## Document Template

```markdown
# {id}: {title}

**Date**: YYYY-MM-DD
**Status**: draft | in-review | complete
**Severity**: SEV-1 | SEV-2 | SEV-3
**Duration**: {total impact time}

## Detection
{How and when the incident was discovered}

## Escalation
{Notification chain and response timeline}

## Recovery
{Steps taken to restore service}

## Prevention
### Root Cause
{5-Whys analysis}

### Action Items
| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|

## Timeline
| Time | Event |
|------|-------|
```

## Examples

User: "we had an outage in checkout this morning, write it up"

```
/ai-postmortem start
```

Scaffolds `PM-2026-001.md`, asks Detection-phase questions (when/how detected, time-to-page, alert quality), advances to Escalation once answered.

## Integration

Called by: user directly. Reads: alerts, runbooks, `/ai-debug` outputs, recent commits. Writes: `.ai-engineering/postmortems/PM-YYYY-NNN.md`. See also: `/ai-debug` (root cause), `/ai-support` (customer-facing), `/ai-learn` (post-incident lessons).

$ARGUMENTS
