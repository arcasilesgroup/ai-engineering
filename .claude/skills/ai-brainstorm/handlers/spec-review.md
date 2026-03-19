# Handler: Spec Review

## Purpose

Dispatch a spec-reviewer subagent to challenge the draft spec. The reviewer argues AGAINST the spec to find weaknesses. Max 3 iterations before presenting to the user.

## Procedure

### Step 1 -- Write the Spec

Create `context/specs/NNN-<slug>/spec.md` with this structure:

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
