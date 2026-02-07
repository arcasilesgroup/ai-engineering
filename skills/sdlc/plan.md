# /ai-plan — Implementation Planning Workflow

This skill defines the workflow for planning an implementation before writing code. It produces a structured plan with design options, trade-offs, implementation steps, and acceptance criteria. The output is an actionable document that can be saved as an Architecture Decision Record (ADR) in `.ai-engineering/knowledge/decisions/`.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Read `.ai-engineering/knowledge/decisions/` — existing ADRs for architectural context
5. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
6. Identify the current branch and working tree state

Do not report this step to the user. Internalize it as context for planning.

---

## Trigger

- User invokes `/ai-plan`
- User says "plan this", "design the approach", "how should we implement", "let's plan", or similar intent

---

## Step 1: Requirement Analysis

Understand what needs to be built before designing how.

### Actions

- Read the requirement, issue, or ticket provided by the user
- Identify ambiguities and unknowns
- Ask clarifying questions (maximum 3) — only ask what is essential to avoid blocking

### Output

```
Requirement Understanding:
  What: <concise description of what needs to be built>
  Why: <business motivation or technical need>
  Constraints: <known constraints — time, compatibility, performance, etc.>
  Unknowns: <things we don't know yet and how they affect the plan>
```

Wait for user confirmation before proceeding.

---

## Step 2: Codebase Exploration

Search the codebase to understand the landscape before designing.

### Exploration Checklist

- **Similar implementations:** Has something similar been built before? How?
- **Existing patterns:** What patterns does the codebase use for this type of work?
- **Affected files:** Which files will likely need changes?
- **Dependencies:** Are there existing libraries or utilities that help?
- **Test infrastructure:** How are similar features tested?
- **Configuration patterns:** How does the project handle configurable values?

### Commands

```bash
# Search for related code
grep -r "<related-terms>" src/
# Find similar implementations
find src/ -name "*<similar>*"
# Check dependencies
cat package.json | grep -i "<related>"
# Review existing patterns
cat src/<similar-module>/<similar-file>.ts
```

### Output

```
Codebase Analysis:
  Similar work: <what exists, if anything>
  Patterns to follow: <established patterns to reuse>
  Files affected: <list of files that will be created or modified>
  Available utilities: <existing helpers, libraries, or abstractions>
  Test approach: <how similar features are tested>
```

---

## Step 3: Design Options

Present 2-3 approaches with trade-offs. Always recommend one.

### For Each Option

```
Option A: <name>
  Approach: <how it works in 2-3 sentences>
  Pros: <advantages>
  Cons: <disadvantages>
  Risk: <what could go wrong>
  Effort: <relative effort — low/medium/high>
  Files: <estimated new files + modified files>
```

### Recommendation

```
Recommended: Option <X>
  Reason: <why this option is the best fit for THIS project, given its patterns and constraints>
```

### Rules

- Always present at least 2 options. Even if one is clearly better, showing an alternative validates the choice.
- If there is truly only one viable approach, explain why alternatives were considered and rejected.
- Be honest about trade-offs. Do not oversell the recommended option.

---

## Step 4: Implementation Plan

Break the recommended approach into atomic steps.

### Plan Structure

```
Implementation Plan
───────────────────
Approach: <chosen option>

Phase 1: <name> (foundation)
  1. <step> — <file> — <what and why>
  2. <step> — <file> — <what and why>

Phase 2: <name> (core logic)
  3. <step> — <file> — <what and why>
  4. <step> — <file> — <what and why>

Phase 3: <name> (integration + tests)
  5. <step> — <file> — <what and why>
  6. <step> — <file> — <what and why>

PARALLELIZABLE — these steps can run simultaneously:
  - Steps 1 and 2 (no dependencies between them)
  - Steps 5 and 6 (independent test files)

Dependencies:
  - Step 3 depends on Step 1 (types/interfaces)
  - Step 5 depends on Step 4 (core logic must exist before testing)

Files to create: <list>
Files to modify: <list>
Estimated scope: ~<N> lines of code, ~<M> lines of tests
```

### Rules

- If the plan involves more than 5 files in a single phase, break into smaller phases.
- Every step must have a stated purpose.
- Mark dependencies explicitly — which steps block which.
- Mark parallelizable steps with the parallel indicator.

---

## Step 5: Acceptance Criteria

Define what "done" looks like.

```
Acceptance Criteria:
  Functional:
    - [ ] <behavior 1> works as specified
    - [ ] <behavior 2> works as specified
    - [ ] Error case: <error scenario> returns expected response

  Technical:
    - [ ] All existing tests pass
    - [ ] New tests cover happy path and error cases
    - [ ] No lint warnings introduced
    - [ ] Build succeeds
    - [ ] No new `any` types (TypeScript)

  Edge Cases:
    - [ ] <edge case 1> is handled
    - [ ] <edge case 2> is handled
```

---

## Step 6: Save as ADR (optional)

Ask the user if they want to save the plan as an Architecture Decision Record:

```
Save this plan as an ADR in .ai-engineering/knowledge/decisions/?
  Filename: YYYY-MM-DD-<short-title>.md
  [y/N]
```

If yes, save in the standard ADR format:

```markdown
# ADR: <title>

**Date:** <date>
**Status:** Accepted
**Context:** <why this decision was needed>
**Decision:** <what we decided>
**Consequences:** <what this means for the project>

## Implementation Plan

<full plan from Step 4>

## Acceptance Criteria

<full criteria from Step 5>
```

---

## Error Recovery

| Failure                          | Action                                                                                   |
| -------------------------------- | ---------------------------------------------------------------------------------------- |
| Requirements unclear             | Ask up to 3 clarifying questions. If still unclear, state assumptions explicitly.        |
| No similar code in codebase      | Note the absence. Design from first principles following the project's general patterns. |
| User rejects all options         | Ask what constraints or preferences they have that the options missed. Redesign.         |
| Scope too large                  | Suggest splitting into multiple plans/PRs. Define the MVP scope.                         |
| Conflicting patterns in codebase | Note the conflict. Recommend the more recent/prevalent pattern.                          |

---

## Learning Capture (on completion)

If during planning you discovered something useful for the project:

1. **Architectural decision** → Saved as ADR in `knowledge/decisions/` (if user approves)
2. **New pattern** → Propose adding to `knowledge/patterns.md`
3. **Risk or anti-pattern** → Propose adding to `knowledge/anti-patterns.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not write code. Use `/ai-implement` after the plan is approved.
- It does not make decisions for the user. It presents options and recommends; the user decides.
- It does not replace architecture reviews. It is a pre-implementation planning tool.
- It does not estimate time. It estimates scope (files, lines) but not duration.
