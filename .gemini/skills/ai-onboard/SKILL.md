---
name: ai-onboard
description: "Invoke this skill whenever a new coding session is beginning or resuming. Covers situations like: greeting Claude at the start of a work session, saying you're picking up from previous work, asking what the current project status is, wanting to orient yourself after opening a repo, or signaling you're ready to start fresh. This skill loads project context (spec, plan, decisions, LESSONS, manifest) and presents a status summary so the session starts grounded. Use it when the user's first message implies 'get me up to speed' or 'let's start working' rather than jumping directly into a task. Also invokable mid-session with /ai-onboard to re-bootstrap. Not for human developer onboarding — use /ai-guide for that."
effort: medium
argument-hint: 
---


# Onboard

## Purpose

Session bootstrap and enforcement. Run once at session start: detect available skills, load project context, activate instinct listening, present status, and enforce skill discipline for the session.

## Procedure

1. **Detect skills** — scan the active platform skill directory and build a capability map.

2. **Load project context**
   - Read `.ai-engineering/specs/spec.md`
   - Read `.ai-engineering/specs/plan.md`
   - Read `.ai-engineering/state/decision-store.json`
   - Read `.ai-engineering/LESSONS.md`
   - Read `.ai-engineering/manifest.yml`
   - Read `.ai-engineering/CONSTITUTION.md` if present
   - Read `.ai-engineering/contexts/session-governance.md`

3. **Activate instinct listening** — run `/ai-instinct` to enter passive observation mode.
   Consolidation is deferred to `/ai-instinct --review` (triggered by `/ai-commit` and `/ai-pr`).

4. **Present status** — report concisely:
   - Active spec (or `no active spec — run /ai-brainstorm`)
   - Plan progress (e.g., `3/7 tasks complete`) or `no active plan`
   - Skills loaded count
   - Decision count and any active risks
   - Instinct: `listening mode active`
   - Board: e.g., `GitHub Projects v2 #4, 5 states mapped` or `not configured (run /ai-board-discover)`

5. **Enforce skill discipline** — install this session rule:
   > If a skill applies to the current task, use it. No shortcuts.

## Scope

**Loads here (session start, once):** project state (spec, plan, decisions, LESSONS, manifest,
constitution), session governance, instinct listening mode, skill discipline enforcement.

**Loads on demand (per skill):** language, framework, and team coding standards — loaded by
execution skills (ai-code, ai-review, ai-test, ai-debug, ai-verify, ai-security, ai-schema,
ai-pipeline, ai-skill-evolve, ai-platform-audit) via `stack-context.md`.

**Does not:** execute product work, write instinct artifacts, or block the session if no active
spec exists.

## Integration

- **NOT** `/ai-guide` — onboard loads AI session state; guide orients human developers

$ARGUMENTS
