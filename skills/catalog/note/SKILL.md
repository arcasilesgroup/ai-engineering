---
name: note
description: Use to save a single discovery, gotcha, or insight, or to search past notes. Different from /ai-learn (which aggregates from PR history) — /ai-note is single-shot, user-driven. Subcommands save and find. Trigger for "save this", "remember this", "note that", "find that thing about X", "what did we discover about Y".
effort: medium
tier: core
capabilities: [tool_use]
---

# /ai-note

Single-shot, user-driven knowledge capture. Two subcommands —
`save <slug> <text> [--tag t]` and `find <query>`. Stores under
`.ai-engineering/notes/<slug>.md`.

> **Different from `/ai-learn`** — `learn` mines PR history for
> patterns. `note` captures a single insight on demand. Use `note` for
> "I just discovered something"; use `learn` for "what have we been
> consistently missing".

## When to use

- "Save this insight before I forget"
- "Remember the workaround for the flaky test"
- "Find that thing about postgres locking we discovered last month"
- During debug — capture the surprise that led to root cause
- During exploration — record a non-obvious decision path

## Subcommands

### `save <slug> <text> [--tag t]`

Persists a note under `.ai-engineering/notes/<slug>.md`:

```
---
slug: postgres-deadlock-on-update-lock-order
created: 2026-04-27
tags: [postgres, deadlock, locking]
spec-ref: spec-073
---

# postgres deadlock on update lock order

UPDATE statements within a single transaction must touch rows in a
deterministic order (e.g. ORDER BY id) or postgres can deadlock when
two concurrent transactions touch the same rows in different orders.

Discovered while debugging spec-073.
```

Tags allow cross-cutting search. Spec-ref auto-detected from the
active spec when not supplied.

### `find <query>`

Full-text search across `.ai-engineering/notes/`:

- Matches in slug, title, body, tags
- Returns ranked snippets with file path
- `--tag t` filters to a single tag

## Process

1. **Resolve subcommand** — `save | find`.
2. **For `save`** — slug must be kebab-case; reject if exists unless
   `--update` passed. Write file with frontmatter + body.
3. **For `find`** — index is rebuilt on-demand (notes are small);
   return top 5 hits with snippets.
4. **Cross-link** — if a note matches an existing LESSON, suggest
   promoting it via `/ai-learn` for cross-PR aggregation.
5. **Emit telemetry** — `note.saved`, `note.searched`.

## Hard rules

- NEVER overwrite an existing slug without `--update`. Notes are
  history, not scratchpad.
- Slugs MUST be kebab-case and unique within `.ai-engineering/notes/`.
- Notes are markdown with frontmatter — never plain text dumps.
- A note belongs to exactly one slug; for cross-cutting concerns, use
  multiple tags.
- The active spec (if any) is auto-recorded as `spec-ref` for
  traceability.

## Common mistakes

- Writing notes as plain text without frontmatter (loses metadata)
- Reusing slugs and clobbering history
- Saving prose where one sentence would do — a note is not a doc
- Forgetting tags — search later requires them
- Treating `note` as a substitute for `LESSONS.md` — promote recurring
  notes via `/ai-learn`
