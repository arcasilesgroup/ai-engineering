# Handler: Persist Artifact

## Purpose

Write `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` with deterministic frontmatter and body sections. Auto-persist when Tier 3 was invoked; opt-in via `--persist` for quick/standard depth.

## Procedure

Phase 1 ships this handler as a placeholder; full persistence logic is implemented in Phase 3 (T-3.8 through T-3.11).

### Inputs

- `query` (string).
- `slug` (string) -- topic slug from Tier 3 generator.
- `depth` (string) -- `quick|standard|deep`.
- `tiers_invoked` (list of int).
- `sources_used` (list of `{title, url, accessed_at}`).
- `notebook_id` (string|None).
- `findings` (string with citations from synthesizer).

### Output File

Path: `.ai-engineering/research/<slug>-<YYYY-MM-DD>.md`

Format:

```markdown
---
query: "<verbatim user query>"
depth: <quick|standard|deep>
tiers_invoked: [0, 1, 2, 3]
sources_used:
  - title: ...
    url: ...
    accessed_at: ...
notebook_id: <string|null>
created_at: <ISO 8601 UTC>
slug: <topic-slug>
---

## Question
<verbatim query>

## Findings
<findings with [N] inline>

## Sources
1. <title> -- <url> (accessed <date>)
2. ...

## Notebook Reference
<NotebookLM URL if applicable>
```

### Trigger Conditions

- Tier 3 invoked -> auto-persist.
- `--persist` flag -> persist regardless of tier.
- Otherwise -> do not persist.

## Status

Phase 1 placeholder. Logic implemented in Phase 3 (T-3.10).
