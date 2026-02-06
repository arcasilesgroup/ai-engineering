---
name: explain
description: Explain code, architecture, or concepts using the Feynman Technique with iterative refinement
---

## Context

Explains any aspect of the project — a file, feature, architectural pattern, data flow, or general concept — using the Feynman Technique: simple language, concrete analogies, iterative refinement, and verification through teaching. Adapts depth to the user's level and always grounds explanations in the actual codebase.

References: [context/architecture.md](context/architecture.md), [context/glossary.md](context/glossary.md), relevant `standards/*.md` files.

## Inputs

$ARGUMENTS - What to explain. Accepts multiple formats:

| Input | Example | Behavior |
|-------|---------|----------|
| File path | `src/Api/Controllers/OrderController.cs` | Explains that file's purpose, structure, and how it fits in the system |
| Feature name | `authentication` | Maps the feature across layers, explains the flow end-to-end |
| Architecture concept | `result pattern` | Explains the pattern with codebase examples |
| Code snippet reference | `ErrorMapper` | Finds and explains the component in context |
| General concept | `dependency injection` | Explains the concept, then shows how the project uses it |
| Scope keyword | `project` or `architecture` | High-level overview of the entire project or its architecture |
| No arguments | _(empty)_ | Asks what the user wants to understand |

Optional flags:
- `--level beginner|intermediate|advanced` — Set explanation depth (default: auto-detect from conversation)
- `--deep` — Include implementation details, edge cases, and trade-offs
- `--teach` — Jump directly to the teaching verification phase

## Steps

### 1. Understand the Request

Parse $ARGUMENTS to determine:
- **Target**: What to explain (file, feature, pattern, concept, or project overview)
- **Scope**: Narrow (single file/function) vs. broad (feature/architecture)
- **Level**: Beginner, intermediate, or advanced

If $ARGUMENTS is empty or ambiguous, ask:
> What would you like me to explain? You can ask about:
> - A specific file or function
> - A feature or data flow (e.g., "how authentication works")
> - An architectural pattern (e.g., "the Result pattern")
> - The project as a whole
>
> What's your current familiarity with this topic?

### 2. Reconnaissance

Before explaining, gather real context from the codebase:

- Read `context/architecture.md` for system structure.
- Read `context/glossary.md` for domain terminology.
- If the target is a file: read it and identify its layer (Controller/Provider/Service/Domain).
- If the target is a feature: search for related files across layers using Glob and Grep.
- If the target is a pattern: find 2+ concrete examples in the codebase.
- Read the relevant `standards/*.md` file to understand the conventions at play.
- Read the relevant `learnings/*.md` for known gotchas related to the topic.

### 3. Build the Simple Explanation (Feynman Pass 1)

Create an initial explanation following these rules:

**Language rules:**
- Use everyday language a bright 12-year-old could follow.
- Introduce technical terms only when necessary, and always define them with a simple comparison first.
- No jargon without an analogy.

**Structure:**
1. **One-sentence summary** — What is this thing and why does it exist?
2. **Analogy** — A concrete, everyday comparison that captures the essence.
3. **How it works** — Step-by-step walkthrough using the analogy as scaffold, with references to actual code paths.
4. **Where it lives** — File paths and architectural layer placement.
5. **How it connects** — What calls it, what it calls, where data flows.

**For project-level explanations:**
1. What the project does (purpose in one paragraph).
2. The "restaurant analogy" or similar: map each architectural layer to a real-world role.
3. Walk through a single request from entry to response.
4. Key patterns and conventions the project follows.
5. Map of the main directories and what lives where.

### 4. Identify Knowledge Gaps

After the initial explanation, proactively:

- Flag areas where the analogy might break down.
- Identify prerequisite concepts the user might not have.
- Surface common misconceptions about this topic.
- Ask 1-2 targeted questions to check understanding:

> To make sure I'm pitching this right:
> - [Specific question about the core concept]
> - [Question about a potential confusion point]

### 5. Iterative Refinement (Feynman Cycles)

Based on user responses, run up to 3 refinement cycles:

**Each cycle:**
1. Listen to what confused them or what they want deeper.
2. Find a better analogy or break the concept into smaller pieces.
3. Show the relevant code to ground the explanation in reality.
4. Re-explain with the improved analogy and concrete code references.
5. Ask a check question to verify the gap is closed.

**Refinement strategies:**
- If the analogy confused them → try a different domain entirely.
- If they need more depth → zoom into the specific component with code examples.
- If they need less depth → zoom out, remove details, strengthen the metaphor.
- If they have a misconception → name it explicitly, explain why it seems right, then show why it's not.

### 6. Teaching Verification

Once the user signals understanding, verify mastery:

> You now understand [topic]. Let's lock it in.
>
> **Challenge:** Imagine you're explaining this to a new team member on their first day. How would you explain [topic] in 2-3 sentences?

Evaluate their explanation for:
- Accuracy (no misconceptions)
- Completeness (key points covered)
- Clarity (could someone else understand it)

If gaps remain, do one more refinement cycle targeting the specific gap.

### 7. Generate Teaching Note

Create a concise reference card:

```
## Teaching Note: [Topic]

**In one sentence:** [What it is and why it exists]

**Think of it as:** [Best analogy from the session]

**Key mechanism:** [How it actually works, in simple terms]

**In this project:** [Where to find it — file paths and layers]

**Watch out for:** [Common misconception or gotcha]

**Remember:** [One memorable phrase or visual]
```

## Report

    ## Explanation: [Topic]

    ### Summary
    [2-3 sentence overview of what was explained]

    ### Level
    [Beginner/Intermediate/Advanced]

    ### Key Analogies Used
    - [Analogy 1] → [What it explained]
    - [Analogy 2] → [What it explained]

    ### Codebase References
    - [file:line] — [What this shows]
    - [file:line] — [What this shows]

    ### Teaching Note
    [The generated teaching note]

    ### Refinement Cycles
    [Number of cycles needed and what was refined]

## Verification

- Explanation is grounded in actual codebase files and patterns
- No jargon used without definition and analogy
- At least one concrete analogy per major concept
- Code references point to real files in the project
- User demonstrated understanding through teaching verification
- Teaching note is accurate and could be used as a quick reference
