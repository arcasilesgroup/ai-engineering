# Handler: Persist Artifact

## Purpose

Write `.ai-engineering/runtime/research/<topic-slug>-<YYYY-MM-DD>.md` with deterministic frontmatter and body sections so subsequent sessions short-circuit at Tier 0 over the persisted corpus. Auto-persist when Tier 3 was invoked; opt-in via `--persist` for quick/standard depth.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_persist_helper.py`) implements.

### Inputs (`PersistInputs`)

- `query` (string) -- verbatim user query.
- `depth` (string) -- `quick|standard|deep`.
- `tiers_invoked` (list[int]).
- `sources_used` (list[`Source`]) -- each with `title`, `url`, `accessed_at`.
- `notebook_id` (string|None) -- the NotebookLM notebook id. Persisted so a later
  `--reuse-notebook=<id>` run can re-attach and harvest the deep report (AC6).
- `findings` (string with `[N]` citations from the synthesizer).
- `created_at` (ISO 8601 UTC string).
- `report_markdown` (string, optional) -- the NotebookLM deep-research report. Set
  when the bounded harvest completed within the wait window; empty when the harvest
  timed out (the run degraded and persisted `notebook_id` for later reuse).

### Trigger Conditions (T-3.9)

`should_persist(*, tier3_invoked, persist_flag)`:

- Tier 3 invoked -> auto-persist.
- `--persist` flag -> persist regardless of tier.
- Otherwise -> do not persist.

### Output Path

`<repo_root>/.ai-engineering/runtime/research/<slug>-<YYYY-MM-DD>.md`

- `slug` = `topic_slug(query)` (re-uses the Tier 3 helper so the slug matches the NotebookLM title).
- `<YYYY-MM-DD>` = first 10 chars of `created_at`.
- The directory is created if missing; existing files at the same path are overwritten.

### File Format

The helper hand-formats the artifact so the produced bytes are stable for tests (no PyYAML import).

```markdown
---
query: "<verbatim user query>"
depth: <quick|standard|deep>
tiers_invoked: [0, 1, 2, 3]
sources_used:
  - title: <title>
    url: <url>
    accessed_at: <iso8601>
  - ...
notebook_id: <string|null>
created_at: <ISO 8601 UTC>
slug: <topic-slug>
---

## Question
<verbatim query>

## Findings
<findings string with inline [N]>

## Sources
1. <title> -- <url> (accessed <accessed_at>)
2. ...

## Notebook Reference
NotebookLM notebook: <notebook_id>      # or "_(none)_" when null

## Deep Research Report                 # OMITTED entirely when report_markdown is empty
<report_markdown verbatim>
```

The four body sections (`## Question`, `## Findings`, `## Sources`, `## Notebook Reference`) are ALWAYS present so Tier 0 readers can rely on a stable layout.

`## Deep Research Report` is OPTIONAL: it is appended (after the four mandatory sections) only when `report_markdown` is non-empty -- i.e. when the NotebookLM bounded harvest completed within the wait window. On harvest timeout the report is absent but `notebook_id` is still recorded (in frontmatter and `## Notebook Reference`) so a follow-up `--reuse-notebook=<id>` run retrieves the report (AC6).

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_persist_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow.

## Status

Phase 3 (T-3.10) implementation. Validator coupling with the synthesizer ships in Phase 4. Extended in spec notebooklm-async-tier3 Phase 5 (T-5.1) with the optional `## Deep Research Report` section and `notebook_id` reuse semantics (AC6).
