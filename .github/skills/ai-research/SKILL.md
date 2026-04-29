---
name: ai-research
description: "Use when the user needs evidence-backed research with verifiable citations: 'what does the state of the art say about X', 'what patterns does the industry use for Y', 'compare options for Z', 'find sources on...', 'investigate...'. Multi-tier escalation (local → free MCPs → web → NotebookLM persistent). Citation hard-rule: every external claim is sourced [N] or marked [unsourced]. Not for refactors, business-logic debugging, or general programming concepts."
effort: high
argument-hint: "<query> [--depth quick|standard|deep] [--reuse-notebook=<id>] [--persist] [--allowed-domains a,b] [--blocked-domains x,y]"
mode: agent
---



# Research

## Purpose

Multi-tier, multi-source research skill with citation-first synthesis and persistent artifact reuse. Replaces ad-hoc `WebSearch` invocations with a disciplined escalation: local context first (zero cost), then free MCPs (Context7, Microsoft Learn, `gh search`), then web search, then NotebookLM for deep persistent corpora. Every external claim carries a `[N]` citation or is marked `[unsourced]` so readers can audit grounding.

Outputs are designed for reuse: deep research is persisted to `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` so subsequent sessions short-circuit at Tier 0.

## When to Use

- User asks for evidence: "what does the industry do for X", "state of the art on Y", "compare A vs B", "find sources on Z".
- `/ai-brainstorm` interrogation flags a question requiring external evidence (handler `interrogate.md` invokes this skill).
- User wants a verifiable, cited answer rather than the model's training-data recall.
- Research worth archiving for the team (deep technical investigations, library comparisons, architecture decisions).

Do NOT use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Process

1. **Classify query** -- follow `handlers/classify-query.md` to decide which tiers apply (library mention → Context7; Azure/Microsoft → MS Learn; comparative or multi-source → mark for Tier 3 candidacy; explicit URL → mark for WebFetch).
2. **Tier 0 -- local** -- follow `handlers/tier0-local.md`. Search prior research artifacts, `LESSONS.md`, and `framework-events.ndjson` for prior `/ai-research` invocations. If ≥3 relevant hits, agent MAY short-circuit and synthesize from local context alone.
3. **Tier 1 -- free MCPs (parallel)** -- follow `handlers/tier1-free-mcps.md`. Invoke Context7, Microsoft Learn, and `gh search code/repos` IN PARALLEL when the classifier marks them applicable. Dedup by URL/path.
4. **Tier 2 -- web** -- follow `handlers/tier2-web.md`. Invoke `WebSearch` and `WebFetch` in parallel when Tier 1 produced fewer than 5 high-quality hits, or the query explicitly references a URL. Honor `--allowed-domains` and `--blocked-domains`.
5. **Tier 3 -- NotebookLM persistent** -- follow `handlers/tier3-notebooklm.md`. Triggered when `--depth=deep`, when the query is comparative (`vs|versus|compare|alternatives`), or when Tier 1+2 collected ≥10 sources. Probe `server_info` first; degrade to Tier 2 only if auth expired.
6. **Synthesize with citations** -- follow `handlers/synthesize-with-citations.md`. Produce output where every external claim carries `[N]` or `[unsourced]`. Validator regex `\[\d+\]|\[unsourced\]` must match at least once per claim paragraph; on failure, retry with stricter system message (max 2 retries).
7. **Persist artifact** -- follow `handlers/persist-artifact.md`. Write `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` with frontmatter (`query`, `depth`, `tiers_invoked`, `sources_used`, `notebook_id`, `created_at`, `slug`) and Question/Findings/Sources/Notebook Reference sections. Auto-persist when Tier 3 invoked; opt-in via `--persist` for quick/standard.

## CLI Flags

- `--depth quick|standard|deep` (default: `standard`). Controls escalation: `quick` runs Tier 0+1 only; `standard` adds Tier 2; `deep` always invokes Tier 3.
- `--reuse-notebook=<id>` (opt-in). Skips `notebook_create` and reuses an existing NotebookLM notebook for follow-up queries.
- `--persist` (opt-in for `quick`/`standard`). Forces artifact persistence even when Tier 3 was not invoked.
- `--allowed-domains a.com,b.com` (pass-through to WebSearch).
- `--blocked-domains x.com,y.com` (pass-through to WebSearch).

## Output Contract

Synthesized response in agent context PLUS, when persisted, a Markdown artifact at `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md`. Output format:

```
## Question
<verbatim user query>

## Findings
<paragraphs with inline [N] citations or [unsourced] markers>

## Sources
1. (title, url, accessed_at)
2. ...

## Notebook Reference
<NotebookLM URL if Tier 3 was invoked>
```

## Common Mistakes

- Skipping Tier 0 and going straight to web search (defeats the reuse goal).
- Producing claims without `[N]` or `[unsourced]` markers (defeats the citation hard-rule).
- Creating a NotebookLM notebook for a quick lookup (overuse of Tier 3 inflates the user's notebook list).
- Not deduplicating Tier 1 results (Context7 and `gh search` can return overlapping URLs).
- Forgetting to probe `server_info` before Tier 3 (silent failures when auth expires).

## Integration

- **Called by**: user directly, or `/ai-brainstorm`'s `handlers/interrogate.md` when a question requires external evidence.
- **Calls**: `handlers/classify-query.md`, `handlers/tier0-local.md`, `handlers/tier1-free-mcps.md`, `handlers/tier2-web.md`, `handlers/tier3-notebooklm.md`, `handlers/synthesize-with-citations.md`, `handlers/persist-artifact.md`.
- **Produces**: `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` (when Tier 3 invoked or `--persist`).

$ARGUMENTS
