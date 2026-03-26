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

### Step 1.5 -- Work Item Context (if provided)

If a work item was fetched during context loading:

1. Read the work item title, description, and acceptance criteria
2. Read child items (tasks under a user story, stories under a feature)
3. Read all standard and custom fields from the platform (status, priority, effort, etc.)
4. Add to the **KNOWN** map: confirmed requirements from the work item fields
5. Add to the **ASSUMED** map: inferences from the work item description
6. Pre-fill the spec `refs` from the work item hierarchy
7. Use the work item context to reduce the number of questions needed

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
