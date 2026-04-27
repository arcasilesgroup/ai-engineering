---
name: specify
description: Use when the user wants to think through a problem before coding — designing a feature, exploring approaches, defining requirements, or resolving ambiguity. HARD GATE — produces a reviewed spec; no implementation until approval.
effort: high
tier: core
capabilities: [tool_use]
governance:
  blocking: true
---

# /ai-specify

Design interrogation. Forces rigorous thinking BEFORE any code is written.
Produces an approved spec that becomes the contract for `/ai-plan`.

> **HARD GATE** — `/ai-implement` cannot run without a spec marked
> `state: approved`.

## When to use

- "I want to build…", "how should we…", "let's design…"
- New feature, architecture change, ambiguous requirement
- Any work where jumping to code would be premature

## Process

1. **Interrogate one question at a time.** Multiple choice (A/B/C) preferred over open-ended.
2. **Challenge vague language.** "improve" / "optimize" / "clean up" are not requirements.
3. **Push back on scope creep.** "Is this in scope for v1?"
4. **Explore unstated edge cases.**
5. **Cap at 10 questions.** If more are needed, the problem is too big — split it.
6. **Propose 2-3 approaches** with trade-offs. Never just one.
7. **Draft spec** to `.ai-engineering/specs/spec-NNN-<slug>.md` with: motivation, scope, non-goals, acceptance criteria, gates applicable.
8. **Self-review** against `contexts/spec-schema.md`. Max 3 iterations.
9. **STOP.** Present approved spec. User runs `/ai-plan` next.

## Scope check (fast-path)

If the task is < 3 files OR audit/maintenance, RESOLVE INLINE without producing
a spec. The HARD GATE is only for implementation-grade work.

## Common mistakes

- Skipping interrogation and jumping to spec
- Proposing only one approach
- Writing implementation details (specs describe WHAT, not HOW)
- Producing a spec without the review loop
