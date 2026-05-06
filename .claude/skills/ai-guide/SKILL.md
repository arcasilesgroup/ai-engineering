---
name: ai-guide
description: "Use when new to a project and need orientation, want to understand component relationships, need to find where something happens ('where does auth happen?'), or understand why a technology decision was made. Modes: tour (architecture overview), find (topic search), history (decision archaeology), onboard (structured human onboarding). Read-only. Not for agent session bootstrap — use /ai-start."
effort: high
argument-hint: "tour|find <topic>|history <decision>|onboard"
tags: [onboarding, architecture, teaching, archaeology]
---


# Guide

Project onboarding, architecture tours, and decision archaeology. Optimized for the human, not the code. Reads everything, modifies nothing. Teaches understanding, not artifacts.

## When to Use

- New to a project and need orientation.
- Want to understand component relationships and data flow.
- Asking "why was X chosen over Y?"
- NOT for writing code -- use `/ai-dispatch`.
- NOT for generating docs -- use `/ai-write`.

## Modes

### tour -- Architecture Overview

1. **Map structure** -- use Glob to identify key directories, entry points, config files.
2. **Identify stack** -- detect languages, frameworks, build tools.
3. **Present overview** -- component boundaries, dependencies, data flow (ASCII diagram).
4. **Explain key patterns** -- design patterns, idioms, conventions used.
5. **Highlight evolution** -- `git log --oneline` for major changes.
6. **Flag gotchas** -- non-obvious behavior, implicit assumptions, known debt.
7. **Suggest next** -- related components worth exploring.

### find -- Topic Search

1. **Search codebase** -- Grep/Glob for the topic across source, config, docs.
2. **Search decisions** -- check `.ai-engineering/state/state.db` `decisions` table for related decisions.
3. **Search specs** -- look in `.ai-engineering/specs/` for relevant specifications.
4. **Present results** -- files, functions, and context around the topic.
5. **Answer the question** -- "where does X happen?", "how do I add a Y?", "what tests cover Z?"

### history -- Decision Archaeology

1. **Search decision store** -- `.ai-engineering/state/state.db` `decisions` table for formal decisions.
2. **Search git history** -- `git log --all --grep` for related commits.
3. **Search specs** -- `.ai-engineering/specs/` for specs that introduced the decision.
4. **Reconstruct context** -- what was known, what constraints existed, what alternatives were considered.
5. **Present alternatives** -- what other options existed and why they were rejected.
6. **Assess relevance** -- has context changed? Are original constraints still valid?
7. **Do NOT recommend** -- present analysis, let developer decide.

### onboard -- Structured Onboarding

1. **Map structure** -- directories, entry points, config, dependencies.
2. **Identify stack** -- languages, frameworks, tools.
3. **Discover patterns** -- recurring code patterns, naming conventions.
4. **Find key files** -- main entry, config, models, tests.
5. **Review standards** -- `.ai-engineering/standards/` for project conventions.
6. **Socratic checkpoints** -- after each phase, ask one question to confirm understanding.
7. **Personalized path** -- based on what the developer wants to work on.

## Quick Reference

```
/ai-guide tour                    # architecture overview
/ai-guide find "authentication"   # where does auth happen?
/ai-guide history "why SQLite"    # decision archaeology
/ai-guide onboard                 # structured onboarding
```

## Common Mistakes

- Making decisions for the developer -- present tradeoffs, let them decide.
- Writing code during a tour -- guide is strictly read-only.
- Over-quizzing -- max 2 Socratic questions per interaction.
- Teaching below the developer's level -- match cues to Bloom's taxonomy.

## Integration

- Uses `/ai-explain` for 3-tier depth explanations.
- Reads `.ai-engineering/state/state.db` `decisions` table for decision context.
- Reads `.ai-engineering/state/framework-events.ndjson` for framework activity context (privacy by design).
- **NOT** `/ai-start` -- guide is for humans exploring a codebase; start bootstraps AI agent session context

## References

- `.claude/skills/ai-explain/SKILL.md` -- 3-tier depth model.
- `.ai-engineering/manifest.yml` -- governance structure.
- `.ai-engineering/state/state.db` `decisions` table -- decision records.
$ARGUMENTS
