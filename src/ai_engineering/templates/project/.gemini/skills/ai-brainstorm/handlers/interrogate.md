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
5. Read constitution (`CONSTITUTION.md`) for project boundaries and stakeholders. If it is absent, fall back to `.ai-engineering/CONSTITUTION.md` for legacy installs.

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

### Step 3.5 -- Escalate to Research When Evidence Is Required

Si la pregunta requiere evidencia externa que el modelo no puede confirmar (e.g., "qué patrones usa la industria", "qué dice el state of the art", "cómo lo hacen otros proyectos open source", "external evidence about library X"), invocar `/ai-research --depth=standard <subquery>` antes de seguir interrogando al usuario y consumir el artifact resultante.

**Heuristic for "evidence required"**:

- The user asks for "industry patterns" / "patrones usa la industria" / "what do other projects do".
- The user asks about "state of the art" / "best practices for X" where X is a library or pattern outside the agent's confident grasp.
- The model's training data is likely outdated for the topic (recent SDK releases, new pattern adoption).
- A multiple-choice answer would be a guess without external corroboration.

When invoked, `/ai-research` writes a Markdown artifact to `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md`. After consuming it:

1. Cite the artifact in the spec under `## References` with prefix `research:` -- e.g., `- research: .ai-engineering/research/state-of-the-art-retries-2026-04-28.md`.
2. Use the artifact's `## Findings` section verbatim (with `[N]` citations preserved) as the basis for the multiple-choice options in the next question.

Default to `--depth=standard` so brainstorm does not auto-trigger Tier 3 NotebookLM (which is reserved for explicit deep research). The user can pass `--depth=deep` manually when invoking research outside brainstorm.

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
