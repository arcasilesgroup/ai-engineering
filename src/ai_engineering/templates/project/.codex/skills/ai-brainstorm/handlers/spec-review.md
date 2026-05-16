# Handler: Spec Review

## Purpose

Dispatch a spec-reviewer subagent to challenge the draft spec. The reviewer argues AGAINST the spec to find weaknesses. Max 3 iterations before presenting to the user.

## Procedure

### Step 1 -- Write the Spec

Create `.ai-engineering/specs/spec.md` with a structure that conforms to `.ai-engineering/contexts/spec-schema.md`:

```markdown
---
spec: spec-NNN
title: [Title]
status: draft
effort: [trivial|small|medium|large]
refs:
  - [Optional work item or related reference]
---

# Spec NNN - [Title]

## Summary
[One paragraph covering the problem, why it matters, and the chosen direction at a high level.]

## Goals
- [Goal 1 - specific and verifiable]
- [Goal 2 - specific and verifiable]

## Non-Goals
- [Explicit scope exclusion]

## Decisions

### D-NNN-01: [Decision title]
[Decision statement]

**Rationale**: [Why this choice was made, including tradeoffs where relevant.]

## Risks
- [Risk 1]: [mitigation]

## References
- [Related work item, prior spec, or document]

## Open Questions
- [Optional unresolved item]
```

### Step 2 -- Self-Review (Subagent Role)

Adopt the spec-reviewer role. Your job is to CHALLENGE the spec:

**Checklist** (evaluate each):

1. **Schema compliance**: Are the required frontmatter fields and required sections present?
2. **Verifiability**: Are the goals concrete enough to prove success with commands, tests, or observable outcomes?
3. **Decision quality**: Does every decision include a rationale instead of only the choice?
4. **Ambiguity**: Are there words like "should", "might", or "ideally"? Replace with concrete language or remove.
5. **Scope creep**: Do the goals include work that should be split into a separate spec?
6. **Missing negatives**: Do the non-goals clearly state what this work will not do?
7. **Second-order effects**: What else changes when this ships? Tests? Docs? Mirrors? Risks? References?

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
- Softening goals until they are no longer testable
- Adding implementation details to the spec
- Exceeding 3 iterations (if 3 rounds cannot resolve it, the spec needs human input)
