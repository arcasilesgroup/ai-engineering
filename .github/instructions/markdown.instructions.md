---
applyTo: "**/*.md"
---

# Markdown Instructions

## Governance References

- `.ai-engineering/standards/framework/core.md` — governance structure, ownership model.
- `.ai-engineering/context/product/framework-contract.md` — framework identity and contract.

## Document Categories

### Framework-Managed (`.ai-engineering/standards/framework/**`)

- Owned by the framework — updated through governed update flows.
- Must include metadata block: `Version`, `Last Updated`, `Owner`.
- Changes require rationale, expected gain, and potential impact.

### Team-Managed (`.ai-engineering/standards/team/**`)

- Owned by the team — never overwritten by framework updates.
- Team decides format and content.

### Project-Managed (`.ai-engineering/context/**`)

- Owned by the project — living documents updated during active work.
- Includes product contracts, specs, learnings.

### Skills (`.ai-engineering/skills/**`)

- Structured procedure documents with clear step-by-step flows.
- Template: Identity → Trigger → Procedure → Output Contract → References.

### Agents (`.ai-engineering/agents/**`)

- Agent persona definitions.
- Template: Identity → Capabilities → Activation → Behavior → Referenced Skills → Referenced Standards → Output Contract → Boundaries.

## Formatting Conventions

- Use ATX-style headers (`#`, `##`, `###`).
- One blank line between sections.
- Use fenced code blocks with language tags (` ```python `, ` ```bash `, ` ```yaml `).
- Use bullet lists for enumeration, numbered lists for sequences/procedures.
- Use bold (`**text**`) for emphasis, backticks for code references.
- Tables: use pipe tables with header separator.
- Keep lines reasonable length — hard wraps not required for prose.

## Metadata Block

For governance documents, include at the top of the content section:

```
| Field        | Value            |
|-------------|------------------|
| Version     | v2               |
| Last Updated| YYYY-MM-DD       |
| Owner       | framework / team |
```

## Cross-Reference Style

- Reference other governance docs with relative paths from `.ai-engineering/`: `standards/framework/core.md`.
- Reference skills with: `skills/swe/debug.md`.
- Reference agents with: `agents/debugger.md`.
- Use markdown links for external references.

## Spec Documents

Specs follow the structure defined in `.ai-engineering/context/specs/`:

- `spec.md` — WHAT: problem, solution, scope, risks.
- `plan.md` — HOW: phases, session map, dependencies.
- `tasks.md` — DO: checkboxes, atomic commits, progress tracking.
- `done.md` — DONE: closure summary, quality gate result, decisions, learnings.
