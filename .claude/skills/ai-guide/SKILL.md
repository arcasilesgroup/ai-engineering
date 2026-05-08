---
name: ai-guide
description: "Onboards humans to a project: architecture tours, topic search, decision archaeology, structured new-team-member orientation. Read-only — never modifies code. Trigger for 'where does auth happen', 'what is the architecture here', 'history of this decision', 'onboard me to this repo', 'tour the codebase'. Not for agent session bootstrap; use /ai-start instead. Not for code-level explanation; use /ai-explain instead."
effort: high
argument-hint: "tour|find [topic]|history [decision]|onboard"
tags: [onboarding, architecture, teaching, archaeology]
---


# Guide

## Quick start

```
/ai-guide tour                # architecture overview
/ai-guide find auth           # find where auth happens
/ai-guide history DEC-003     # decision archaeology
/ai-guide onboard             # structured new-member onboarding
```

## Workflow

Project onboarding, architecture tours, and decision archaeology. Optimized for the human, not the code. Reads everything, modifies nothing. Teaches understanding, not artifacts.

1. **`tour`** — Glob/identify directories, entry points, config; detect stack; present overview with ASCII diagram (component boundaries, dependencies, data flow); explain key patterns; `git log --oneline` for evolution; flag gotchas; suggest next paths.
2. **`find [topic]`** — Grep/Glob across source/config/docs; check `state.db.decisions` and `.ai-engineering/specs/`; present file:line refs and context; answer "where does X happen?".
3. **`history [decision]`** — search `state.db.decisions`, `git log --all --grep`, and `specs/`; reconstruct what was known, constraints, alternatives considered; assess current relevance; **do NOT recommend** — present analysis, let developer decide.
4. **`onboard`** — map structure; identify stack; discover patterns; find key files; review `.ai-engineering/standards/`; Socratic checkpoint per phase; personalize path to developer's interest.

## Dispatch threshold

Dispatch the `ai-guide` agent for any human-onboarding, archaeology, or codebase-tour request. Strictly read-only. The agent file (`.claude/agents/ai-guide.md`) is the dispatch handle; mode procedures and pedagogical principles live here.

## When to Use

- New to a project and need orientation.
- Want to understand component relationships and data flow.
- Asking "why was X chosen over Y?".
- NOT for writing code — use `/ai-dispatch`.
- NOT for generating docs — use `/ai-write`.

## Common Mistakes

- Making decisions for the developer — present tradeoffs, let them decide.
- Writing code during a tour — guide is strictly read-only.
- Over-quizzing — max 2 Socratic questions per interaction.
- Teaching below the developer's level — match cues to Bloom's taxonomy.

## Examples

### Example 1 — onboard a new team member

User: "give me an architecture tour of this repo, I'm new"

```
/ai-guide tour
```

High-level overview, module ownership map, key boundaries, suggested deeper-dive paths. Read-only.

### Example 2 — decision archaeology

User: "why did we choose hexagonal architecture for this codebase?"

```
/ai-guide history hexagonal-architecture
```

Reads `state.db.decisions` for the matching record, surfaces the original tradeoffs, links to the spec or commit that ratified it.

## Integration

Calls: `/ai-explain` (3-tier depth). Reads: `state.db.decisions`, `framework-events.ndjson`, `manifest.yml`. See also: `/ai-start` (agent session bootstrap), `/ai-explain` (code-level), `/ai-research` (external evidence).

## References

- `.claude/skills/ai-explain/SKILL.md` -- 3-tier depth model.
- `.ai-engineering/manifest.yml` -- governance structure.
- `.ai-engineering/state/state.db` `decisions` table -- decision records.

$ARGUMENTS
