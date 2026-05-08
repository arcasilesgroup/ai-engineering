---
name: ai-brainstorm
description: "Forces rigorous design interrogation BEFORE any code: explores approaches, surfaces ambiguity, gathers evidence, produces an approved spec that becomes the contract for /ai-plan. Trigger for 'lets add X', 'how should we handle Y', 'whats the best approach', 'I am thinking about', 'what should we build for'. Not for existing approved specs; use /ai-plan instead. Not for execution; use /ai-dispatch instead."
effort: max
argument-hint: "[feature or problem description] [work item ID]"
---

# Brainstorm

## Purpose

Design interrogation skill. Forces rigorous thinking BEFORE any code is written. Produces an approved spec that becomes the contract for `/ai-plan`.

HARD GATE: this skill produces a spec. No implementation happens until the user explicitly approves it.

## When to Use

- User says "I want to build...", "how should we...", "let's design..."
- New feature, architecture change, or ambiguous requirement
- The spec depends on evidence scattered across multiple repo or governance surfaces
- Any work where jumping straight to code would be premature

## Process

0. **Spec lifecycle bootstrap** (before evidence sweep) — call
   `python .ai-engineering/scripts/spec_lifecycle.py start_new <slug> <title>`
   to mint (or no-op refresh) the DRAFT record under
   `.ai-engineering/state/specs/<slug>.json`. **Fail-open**: if the script
   exits non-zero (missing dependency, locked sidecar), log the failure and
   continue — interrogation must not be blocked by lifecycle plumbing.
1. **Work item context** (only when a work item ID is provided, e.g., `AB#100` or `#45`):
   a. Read `.ai-engineering/manifest.yml` `work_items` section for active provider and team config
   b. Fetch work item and its hierarchy from the provider: - **GitHub**: `gh issue view <number> --json title,body,labels,milestone,assignees` - **Azure DevOps**: `az boards work-item show --id <number> --expand relations -o json`
   c. Walk the hierarchy: Feature → User Story → Tasks (follow parent/child relations)
   d. Use all standard and custom fields the platform provides
   e. Pre-fill `refs` section in the generated spec frontmatter
   f. Invoke `/ai-board-sync refinement <work-item-ref>` to transition the work item to refinement state (fail-open: do not block brainstorm if this fails)
2. **Enhance input** -- follow `handlers/prompt-enhance.md` to evaluate and optimize user input for clarity and specificity before interrogation
3. **Evidence sweep** -- when the current state spans multiple repo or governance surfaces, dispatch parallel read-only `ai-explore` passes first, summarize the findings, and use that evidence to sharpen the next question or spec boundary
4. **Interrogate** -- follow `handlers/interrogate.md` for the questioning flow
5. **Scope check** -- if interrogation reveals the work is small enough to resolve
   without a spec (e.g., audit questions, maintenance fixes, < 3 file changes),
   present the resolution directly and STOP. No spec needed. Log the decision
   in the conversation. The HARD GATE only applies to implementation-grade work.
6. **Propose approaches** -- present 2-3 options with trade-offs (never just one)
7. **Draft spec** -- write spec to `.ai-engineering/specs/spec.md`. Validate spec against `.ai-engineering/contexts/spec-schema.md` -- all required sections must be present before marking the spec as approved.
8. **Board sync (ready)** -- if a work item ID was provided in step 1, invoke `/ai-board-sync ready <work-item-ref>` to transition the work item to ready state (fail-open: do not block brainstorm if this fails)
9. **Review spec** -- follow `handlers/spec-review.md` for the review loop (max 3 iterations)
10. **STOP** -- present approved spec. User runs `/ai-plan` to continue.

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
- **Calls**: `handlers/prompt-enhance.md`, `handlers/interrogate.md`, `handlers/spec-review.md`, `/ai-board-sync` (refinement + ready transitions), `.ai-engineering/scripts/spec_lifecycle.py start_new` (fail-open lifecycle bootstrap)
- **Transitions to**: `/ai-plan` (ONLY -- never directly to `ai-build` or `/ai-dispatch`)

## Examples

### Example 1 — design a new feature from a vague request

User: "lets add multi-tenant support"

```
/ai-brainstorm "multi-tenant support"
```

Interrogates: what's the isolation model? per-row, per-schema, per-database? What about data residency? Existing user migration? Produces an approved spec at `.ai-engineering/specs/spec.md` with decisions recorded.

### Example 2 — resolve ambiguity in a work item

User: "AB#456 says 'improve search performance' — what does that even mean?"

```
/ai-brainstorm AB#456
```

Pulls the work item, surfaces ambiguity, drives the user to specific measurable acceptance criteria, links the spec to the work item.

$ARGUMENTS
