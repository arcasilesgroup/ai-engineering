---
name: plan
description: Use when an approved spec exists and needs a phased execution plan — task decomposition, agent assignments, gate criteria. HARD GATE — produces a plan that becomes the contract for `/ai-implement`.
effort: high
tier: core
capabilities: [tool_use]
governance:
  blocking: true
---

# /ai-plan

Decompose an approved spec into atomic, TDD-first tasks with explicit
dependencies, agent assignments, and gate criteria.

> **HARD GATE** — `/ai-implement` requires `plan.md` with all tasks marked
> ready and the user's explicit approval.

## When to use

- Approved spec exists in `.ai-engineering/specs/spec-NNN-<slug>.md`
- "break this down", "create a plan", "what tasks do we need"
- Re-planning when scope changed or plan failed

## Process

1. **Read the approved spec.** Refuse to plan against drafts.
2. **Decompose into atomic tasks.** Each task is half-day to two days.
3. **Order by dependency** (DAG). Mark parallelizable tasks explicitly.
4. **Pair RED + GREEN** (TDD). Failing test first; the GREEN task lists
   exactly which test to make pass.
5. **Assign agents.** Most tasks → `builder`. Verification → `verifier`.
   Heavy code review → `reviewer`. Read-only research → `explorer`.
6. **Declare gates per task.** ruff + gitleaks staged are always-on; tests
   may be task-specific.
7. **Write to `.ai-engineering/specs/spec-NNN/plan.md`** with checkable
   items.
8. **Self-review** for: missing tests, missing gates, hidden cross-task
   dependencies, scope creep.

## Trivial pipeline

Comment-only / typo / single-line: skip discovery, architecture, risk —
go straight to spec → implement (2 phases vs 6).

## Common mistakes

- Planning before spec is approved
- Tasks too large (>3 days)
- Missing RED/GREEN pairing
- No explicit gate criteria
