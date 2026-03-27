---
name: ai-onboard
description: "Use at the start of any coding session to bootstrap framework context: loads active spec, plan, decisions, lessons, and instinct patterns. Run before anything else when starting a new session or resuming work. Trigger for 'let's get started', 'picking up where we left off', 'what's the current state?', 'catch me up'. Not for human project orientation — use /ai-guide onboard."
effort: medium
argument-hint: 
mode: agent
---



# Onboard

## Purpose

Framework bootstrap and enforcement. Detect available skills, load active project context, refresh instinct context only when needed, and install the session rule that skills are mandatory when they apply.

## Trigger

- Auto-triggered via session-start hooks when available
- Manual: `/ai-onboard`
- Context: beginning of any non-trivial session

## Procedure

1. **Detect skills**
   - Scan the active platform skill directory and build a capability map.

2. **Load active project context**
   - Read `.ai-engineering/specs/spec.md`
   - Read `.ai-engineering/specs/plan.md`
   - Read `.ai-engineering/state/decision-store.json`
   - Read `.ai-engineering/contexts/team/lessons.md`
   - Read `.ai-engineering/manifest.yml`
   - Read `.ai-engineering/contexts/project-identity.md` if present

3. **Refresh instinct context when needed**
   - Inspect `.ai-engineering/instincts/meta.json`
   - Inspect `.ai-engineering/instincts/context.md`
   - If refresh is pending, the context is stale, or enough new observations accumulated, run `/ai-instinct review`
   - Otherwise, load the existing bounded instinct context as-is

4. **Present quick status**
   - Report the active spec
   - Report plan progress if a plan exists
   - Report loaded skills count
   - Report decision count or notable active risks
   - Report instinct status: fresh, stale, or refreshed
   - Report board configuration if present

5. **Enforce skill discipline**
   - Install this rule for the session:

     > If a skill applies to the current task, you MUST use it. No shortcuts.

## Board Status Examples

- `Board: GitHub Projects v2 #4, 5 states mapped`
- `Board: GitHub Labels (status: labels), 5 states mapped`
- `Board: Azure DevOps (Agile), 5 states mapped`
- `Board: not configured (run /ai-board-discover)`

## Session Governance

Load `.ai-engineering/contexts/session-governance.md` for session governance rules and red flags.

## Quick Reference

```text
/ai-onboard
```

No arguments. Reads project state, refreshes instinct context when warranted, and configures the session.

## Boundaries

- `onboard` does not execute product work
- `onboard` should stay light; it loads context and refreshes instinct context only when the gate says it is worth doing
- `onboard` may update `.ai-engineering/instincts/{instincts.yml,context.md,meta.json}` as an explicit exception to the usual read-only bootstrap rule
- If no active spec exists, report it but do not block the session

## Integration

- **NOT** `/ai-guide` -- onboard loads AI session state; guide orients human developers

$ARGUMENTS
