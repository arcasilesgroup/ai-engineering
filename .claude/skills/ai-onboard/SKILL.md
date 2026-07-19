---
name: ai-onboard
description: "Onboards humans to a project: architecture tours, topic search, decision archaeology, structured new-team-member orientation. Read-only — never modifies code. Trigger for 'where does auth happen', 'what is the architecture here', 'history of this decision', 'onboard me to this repo', 'tour the codebase'. Not for agent session bootstrap; use /ai-start instead. Not for code-level explanation; use /ai-explain instead."
effort: mid
argument-hint: "tour|find [topic]|history [decision]|onboard"
tags: [onboarding, architecture, teaching, archaeology]
---

# Onboard

Onboards humans to a project through architecture tours, topic search, decision archaeology, and structured new-team-member orientation. Read-only — never modifies code; use for questions like "where does auth happen" or "tour this codebase".

## Quick start

```
/ai-onboard tour                # architecture overview
/ai-onboard find auth           # find where auth happens
/ai-onboard history DEC-003     # decision archaeology
/ai-onboard onboard             # structured new-member onboarding
```

## Workflow

Dispatch the `ai-onboard` agent (`.claude/agents/ai-onboard.md`) for any
tour / find / history / onboard request touching >= 1 subsystem —
strictly read-only. Mode procedures (§10.7 Clean Code — clarity over
cleverness):

| Mode | Procedure |
|------|-----------|
| `tour` | Map dirs/entry points/config; detect stack; ASCII diagram (boundaries, deps, data flow); explain key patterns; `git log --oneline` for evolution; flag gotchas; suggest next paths. |
| `find [topic]` | Search source+config+docs; check `decision-store.json` + `.ai-engineering/specs/`; present `file:line` refs + context; answer "where does X happen?". |
| `history [decision]` | Search `decision-store.json`, `git log --all --grep`, `specs/`; reconstruct what was known + constraints + alternatives; assess current relevance; do NOT recommend — present analysis, let the developer decide. |
| `onboard` | Map structure; identify stack; discover patterns; find key files; review `.ai-engineering/standards/`; Socratic checkpoint per phase (max 2 questions); personalize to the developer's interest. |

Pitfalls: never decide for the developer (present tradeoffs); never write
code during a tour; cap Socratic questions at 2 per interaction; match
teaching to the developer's level (Bloom's cues).

## Examples

### Example — architecture tour for a new team member

User: "give me an architecture tour of this repo, I'm new"

```
/ai-onboard tour
```

High-level overview, module ownership map, key boundaries, ASCII data
flow, suggested deeper-dive paths. Read-only.

## Integration

Calls: `/ai-explain` (3-tier depth). Reads: `decision-store.json`,
`framework-events.ndjson`, `manifest.yml`. See also: `/ai-start` (agent
bootstrap), `/ai-explain` (code-level), `/ai-research` (external
evidence).

$ARGUMENTS
