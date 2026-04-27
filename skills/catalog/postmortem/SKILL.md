---
name: postmortem
description: Use after an incident is resolved to capture the DERP analysis — Detection, Escalation, Remediation, Prevention. Trigger for "write a postmortem", "the incident is over, now what", "blameless review". Produces `.ai-engineering/postmortems/PM-<id>.md`.
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-postmortem

Blameless postmortem in **DERP** format: Detection, Escalation,
Remediation, Prevention. Produces a versioned document under
`.ai-engineering/postmortems/PM-<id>.md` and emits structured action
items into the backlog.

## When to use

- After every Sev-1 / Sev-2 incident (mandatory within 48h of `/ai-hotfix`)
- After a near-miss that would have been Sev-1
- After a release that triggered `/ai-release-gate --rollback`
- For chronic recurring issues — pattern postmortem covers multiple events

## DERP framework

### Detection

- How was the issue first noticed? (alert, customer report, internal probe?)
- Time-to-detect (incident start → first signal)
- Was the alert actionable and routed to the right team?

**Interview questions**:
- What signal would have caught this earlier?
- Did existing monitoring fail or did it not exist?
- Was the runbook accurate?

### Escalation

- Who was paged? At what time?
- Was the on-call rotation correct? Backup engaged?
- Were stakeholders informed (status page, customer comms, exec)?

**Interview questions**:
- Did the responder have the access and context they needed?
- Were communications clear and timely?
- Did anyone get paged who shouldn't have been?

### Remediation

- What was the timeline of fixes attempted?
- What worked? What made it worse?
- How was the fix verified before declaring resolved?

**Interview questions**:
- Was the fix applied via `/ai-hotfix` with audit trail?
- Were there any rollback considerations skipped?
- How long did it take from page → mitigation → full resolution?

### Prevention

- What action items prevent recurrence? (concrete, owned, dated)
- What systemic improvements are needed beyond this single class of bug?
- What documentation, runbooks, or tests are missing?

**Interview questions**:
- What change would have made this impossible?
- What change would have reduced the impact?
- What change would have shortened detection?

## Process

1. **Schedule within 48 hours** of incident resolution. Calendar invite
   includes responder, on-call, eng lead, product (optional).
2. **Pre-fill timeline** from `.ai-engineering/incidents/<id>.md` audit
   trail — telemetry events, hotfix commits, comms.
3. **Run blameless interview** — focus on systems, not individuals.
4. **Author DERP doc** in `.ai-engineering/postmortems/PM-<id>.md`
   from the template (Detection / Escalation / Remediation / Prevention).
5. **Action items** — every item has owner, target date, and tracking
   issue. Emit to board via `/ai-board sync`.
6. **Publish** — share doc with broader org; add to runbook index.

## Hard rules

- **Blameless** — no individual names attached to errors; use roles.
- **Timeline must be reconstructed from audit log**, not memory.
- Every action item must have an owner, target date, and tracker.
- Postmortems are append-only. Future learnings are added as updates.
- Sev-1 postmortem within 48 hours is mandatory.

## Common mistakes

- Naming and shaming — blameless means systemic
- Action items without owners or dates (they evaporate)
- Skipping the prevention phase — root cause is half the value
- Reconstructing timeline from memory instead of audit log
- Publishing only to the immediate team — losing org-wide learning
