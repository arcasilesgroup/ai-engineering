---
name: ai-brainstorm
description: "Use when the user wants to think through a problem before coding: designing a feature, exploring approaches, defining requirements, or resolving ambiguity. Trigger for 'let's add X', 'how should we handle Y', 'what's the best approach', 'I'm thinking about', or any work item lacking an approved spec. Not for existing specs — use /ai-plan instead. Produces a reviewed spec; no code until user approves."
effort: max
argument-hint: "[feature or problem description] [optional: work item ID e.g. AB#100, #45]"
---


# Brainstorm

## Purpose

Design interrogation skill. Forces rigorous thinking BEFORE any code is written. Produces an approved spec that becomes the contract for `/ai-plan`.

HARD GATE: this skill produces a spec. No implementation happens until the user explicitly approves it.

## When to Use

- User says "I want to build...", "how should we...", "let's design..."
- New feature, architecture change, or ambiguous requirement
- Any work where jumping straight to code would be premature

## Process

1. **Work item context** (only when a work item ID is provided, e.g., `AB#100` or `#45`):
     a. Read `.ai-engineering/manifest.yml` `work_items` section for active provider and team config
     b. Fetch work item and its hierarchy from the provider:
        - **GitHub**: `gh issue view <number> --json title,body,labels,milestone,assignees`
        - **Azure DevOps**: `az boards work-item show --id <number> --expand relations -o json`
     c. Walk the hierarchy: Feature → User Story → Tasks (follow parent/child relations)
     d. Use all standard and custom fields the platform provides
     e. Pre-fill `refs` section in the generated spec frontmatter
     f. Invoke `/ai-board-sync refinement <work-item-ref>` to transition the work item to refinement state (fail-open: do not block brainstorm if this fails)
2. **Enhance input** -- follow `handlers/prompt-enhance.md` to evaluate and optimize user input for clarity and specificity before interrogation
3. **Interrogate** -- follow `handlers/interrogate.md` for the questioning flow
4. **Scope check** -- if interrogation reveals the work is small enough to resolve
   without a spec (e.g., audit questions, maintenance fixes, < 3 file changes),
   present the resolution directly and STOP. No spec needed. Log the decision
   in the conversation. The HARD GATE only applies to implementation-grade work.
5. **Propose approaches** -- present 2-3 options with trade-offs (never just one)
6. **Draft spec** -- write spec to `specs/spec.md`. Validate spec against `.ai-engineering/contexts/spec-schema.md` -- all required sections must be present before marking the spec as approved.
7. **Board sync (ready)** -- if a work item ID was provided in step 1, invoke `/ai-board-sync ready <work-item-ref>` to transition the work item to ready state (fail-open: do not block brainstorm if this fails)
8. **Review spec** -- follow `handlers/spec-review.md` for the review loop (max 3 iterations)
9. **STOP** -- present approved spec. User runs `/ai-plan` to continue.

## Quick Reference

| Step | Gate | Output |
|------|------|--------|
| Enhance input | Input quality checked | Optimized input (or original if already specific) |
| Interrogate | All UNKNOWNs resolved | Requirements map |
| Scope check | Scope justifies spec? | Resolution or continue to step 5 |
| Propose | User selects approach | Chosen design |
| Spec draft | Written to disk | spec.md |
| Spec review | Subagent approves | Reviewed spec |
| User approval | User says "approved" | HARD GATE passed |

## Questioning Rules

- ONE question at a time. Never batch.
- Prefer multiple choice (A/B/C) over open-ended.
- Challenge vague language: "improve", "optimize", "clean up" are not requirements.
- Push back on scope creep. Ask: "Is this in scope for v1?"
- Explore edge cases the user has not mentioned.
- Max 10 questions per session. If you need more, the problem is too big -- split it.
- When the user's input requires research to understand the current state (e.g.,
  audits, "is this working?", "how is X organized?"), gather data first, present
  findings, THEN interrogate. Research is not interrogation -- it precedes it.

## Common Mistakes

- Skipping interrogation and jumping to the spec.
- Proposing only one approach (always propose 2-3).
- Writing implementation details in the spec (specs describe WHAT, not HOW).
- Not challenging the user's assumptions.
- Producing a spec without the review loop.

## Integration

- **Called by**: user directly, or `/ai-plan` when requirements are unclear
- **Calls**: `handlers/prompt-enhance.md`, `handlers/interrogate.md`, `handlers/spec-review.md`, `/ai-board-sync` (refinement + ready transitions)
- **Transitions to**: `/ai-plan` (ONLY -- never directly to `ai-build` or `/ai-dispatch`)

$ARGUMENTS
