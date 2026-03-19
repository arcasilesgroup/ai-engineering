---
name: ai-brainstorm
description: "Use when the user wants to design, architect, or explore a feature before building it. HARD GATE: no implementation until the user approves the spec."
argument-hint: "[feature or problem description]"
mode: agent
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

1. **Load context** -- read `specs/spec.md`, `decision-store.json`, and `docs/solution-intent.md` section 7 (roadmap)
2. **Interrogate** -- follow `handlers/interrogate.md` for the questioning flow
3. **Propose approaches** -- present 2-3 options with trade-offs (never just one)
4. **Draft spec** -- write spec to `specs/spec.md`
5. **Review spec** -- follow `handlers/spec-review.md` for the review loop (max 3 iterations)
6. **STOP** -- present approved spec. User runs `/ai-plan` to continue.

## Quick Reference

| Step | Gate | Output |
|------|------|--------|
| Interrogate | All UNKNOWNs resolved | Requirements map |
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

## Common Mistakes

- Skipping interrogation and jumping to the spec.
- Proposing only one approach (always propose 2-3).
- Writing implementation details in the spec (specs describe WHAT, not HOW).
- Not challenging the user's assumptions.
- Producing a spec without the review loop.

## Integration

- **Called by**: user directly, or `/ai-plan` when requirements are unclear
- **Calls**: `handlers/interrogate.md`, `handlers/spec-review.md`
- **Transitions to**: `/ai-plan` (ONLY -- never directly to `ai-build` or `/ai-dispatch`)

$ARGUMENTS

---

# Handler: Interrogate

## Purpose

Structured questioning flow to extract complete requirements from the user. Every piece of information is classified as KNOWN, ASSUMED, or UNKNOWN.

## Procedure

### Step 1 -- Explore First

Before asking questions, gather context silently:

1. Read codebase structure (Glob for relevant files)
2. Read existing patterns (Grep for conventions)
3. Read related specs (check `specs/` for prior work)
4. Read decision store for relevant architectural decisions

Do NOT ask the user what you can learn from the code.

### Step 2 -- Classify What You Know

After exploration, build a requirements map:

```
KNOWN:    [facts confirmed by code, docs, or user statement]
ASSUMED:  [inferred but not confirmed -- document as "ASSUMPTION: ..."]
UNKNOWN:  [need user input -- these drive the questions]
```

### Step 3 -- Ask Questions (One at a Time)

For each UNKNOWN, formulate a question:

**Format**: prefer multiple choice with a recommended option.

```
Q: How should we handle authentication for this endpoint?

A) JWT tokens (recommended -- consistent with existing auth pattern in src/auth/)
B) API keys (simpler, but breaks consistency)
C) OAuth2 (most flexible, but higher complexity for this use case)
D) Something else -- describe
```

**Rules**:
- ONE question per message. Wait for the answer.
- Start with the highest-impact unknowns (architecture > behavior > naming).
- Challenge vague answers: "Can you be more specific about what 'fast' means? Under 100ms? Under 1s?"
- Push back when appropriate: "That adds significant complexity. Is it worth it for v1?"
- Explore what the user has NOT mentioned: "What happens when X fails?"

### Step 4 -- Track Progress

After each answer, update the map:

- Move UNKNOWN to KNOWN (user confirmed)
- Move ASSUMED to KNOWN (user validated) or flag as wrong
- Surface new UNKNOWNs discovered from the answer

### Step 5 -- Propose Approaches

When all UNKNOWNs are resolved (or max 10 questions reached):

Present 2-3 approaches with this structure:

```markdown
## Approach A: [Name]
- **How**: [1-2 sentences]
- **Pros**: [bullet list]
- **Cons**: [bullet list]
- **Effort**: [S/M/L]
- **Risk**: [low/medium/high]

## Approach B: [Name]
...

## Recommendation: [A/B/C] because [1 sentence]
```

### Exit Criteria

- Zero UNKNOWN items remain
- User has selected an approach
- All ASSUMED items are documented
- Edge cases have been discussed

Hand off to spec drafting (main SKILL.md step 4).
# Handler: Spec Review

## Purpose

Dispatch a spec-reviewer subagent to challenge the draft spec. The reviewer argues AGAINST the spec to find weaknesses. Max 3 iterations before presenting to the user.

## Procedure

### Step 1 -- Write the Spec

Create `specs/spec.md` with this structure:

```markdown
# Spec NNN: [Title]

## Problem
[What is broken or missing. 2-3 sentences.]

## Solution
[What we will build. Describe the WHAT, not the HOW.]

## Scope
### In Scope
- [Explicit list of what is included]

### Out of Scope
- [Explicit list of what is excluded]

## Acceptance Criteria
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]

## Assumptions
- [ASSUMPTION: ...] (carried from interrogation)

## Risks
- [Risk 1]: [mitigation]

## Dependencies
- [What must exist before this can start]
```

### Step 2 -- Self-Review (Subagent Role)

Adopt the spec-reviewer role. Your job is to CHALLENGE the spec:

**Checklist** (evaluate each):

1. **Completeness**: Are there missing acceptance criteria? Untested edge cases?
2. **Testability**: Can every acceptance criterion be verified with a command or assertion?
3. **Ambiguity**: Are there words like "should", "might", "ideally"? Replace with "must" or remove.
4. **Scope creep**: Does the scope include work that could be a separate spec?
5. **Missing negatives**: What should the system explicitly NOT do?
6. **Dependency gaps**: Are all prerequisites identified?
7. **Second-order effects**: What else changes when this ships? Tests? Docs? Mirrors?

**Output**: list of concerns, each with a proposed fix.

### Step 3 -- Iterate (Max 3 Rounds)

For each concern:
1. Apply the fix to the spec
2. Re-check: did the fix introduce new issues?
3. If new issues found, fix those (counts toward the 3-round limit)

After 3 rounds, or when no concerns remain: STOP.

### Step 4 -- Present to User

Present the reviewed spec with a summary:

```markdown
## Spec Review Summary

- Iterations: N/3
- Concerns found: N
- Concerns resolved: N
- Remaining open items: [list, if any]

[Full spec text follows]
```

The user must explicitly approve before proceeding to `/ai-plan`.

### Anti-Patterns

- Rubber-stamping your own spec (always find at least one real concern)
- Softening acceptance criteria during review
- Adding implementation details to the spec
- Exceeding 3 iterations (if 3 rounds cannot resolve it, the spec needs human input)
