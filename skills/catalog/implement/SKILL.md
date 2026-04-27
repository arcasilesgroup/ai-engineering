---
name: implement
description: Use when an approved plan.md exists and execution should begin. Trigger for "go", "start building", "execute the plan", "implement it", "run the plan", "resume" or "continue" after interruption.
effort: high
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: false
---

# /ai-implement

Execute an approved plan via subagents per task with two-stage review,
progress tracking, and automated delivery.

> **PRECONDITION** — `.ai-engineering/specs/spec-NNN/plan.md` exists with
> tasks marked ready and explicit user approval.

## When to use

- Plan approved, ready to write code
- Resuming after interruption (`/ai-implement` re-reads the plan)

## Process

1. **Load `plan.md`** and walk the DAG.
2. **For each ready task**: dispatch the `builder` agent with task scope.
3. **TDD enforced**: builder writes failing test first, then code, then
   refactors. Each phase commit-ready.
4. **Quality gates per task**: format, lint, typecheck, test, secrets.
   Block until green or the task's gates allow warn/fail with logged
   risk acceptance.
5. **Two-stage review**: `verifier` deterministic, then `reviewer` for
   judgment.
6. **Mark task complete** in `plan.md` only when all gates green.
7. **Update telemetry** — emit `task.completed` with duration + verdict.

## Subagent boundary

The `builder` agent is the ONLY agent with write permissions (Cognition
principle: actions embed decisions). Other agents propose patches that
the builder applies.

## Common mistakes

- Editing without a plan task
- Skipping RED phase
- Marking task complete with failing tests
- Writing code that wasn't proposed in the spec
