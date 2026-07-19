---
name: ai-research
description: "External evidence with citations via a 4-tier escalation (local → free MCPs → web/Exa → NotebookLM autonomous deep research, launched first / harvested last). Every claim sourced [N] or marked [unsourced]; output ends with 3 cited recommended directions. Trigger for 'what does the state of the art say about', 'compare options for', 'find sources on', 'investigate this question', 'research this'. Use for questions whose answer lives OUTSIDE the codebase. Not for codebase exploration; use /ai-explore instead. Not for refactors; use /ai-simplify instead. Not for business-logic debugging; use /ai-debug instead."
effort: mid
argument-hint: "[query] [--depth quick|standard|deep] [--reuse-notebook=id] [--persist]"
---


# Research

Multi-tier, multi-source, citation-first research with persistent artifact reuse. Replaces ad-hoc `WebSearch` with a disciplined escalation that launches slow NotebookLM deep research first, harvests it last, and sources every claim `[N]` or `[unsourced]`.

## Process

Order is the **execution timeline**, not a strict gate sequence — Tier 3 is *launched* first (step 2) and *harvested* last (step 6), running concurrently with fast Tiers 0-2.

1. **Classify query** — `handlers/classify-query.md`: decide which Tier 1 MCPs apply (library → Context7; Azure/Microsoft → MS Learn; real-world-code → `gh search`; explicit URL → mark for fetch). Tier 3 is NOT gated here — it is default-on when available.
2. **Tier 3 launch (T0, background, default-on)** — Launch half of `handlers/tier3-notebooklm.md`. The `notebooklm doctor` gate runs INSIDE the background subagent before any `create_notebook`/`add_research`; non-zero exit → subagent degrades at T0 (warning, no blocking banner) and the main agent proceeds on Tiers 0-2. When available, launch the deep-research job FIRST as ONE DETACHED CLI command: `notebooklm source add-research "<query>" -n <notebook> --from web --mode deep --import-all --timeout <N> --json`. `--import-all` imports discovered sources; the detached job outlives the run. No flag enables it (default-on); absent/unauthenticated → degraded, recorded, never raised.
3. **Tier 0 — local** — `handlers/tier0-local.md`: search prior research artifacts, `LESSONS.md`, and `framework-events.ndjson` for prior `/ai-research` invocations. On ≥3 relevant hits the agent MAY short-circuit the fast tiers and synthesize from local context (Tier 3 is still harvested in step 6).
4. **Tier 1 — free MCPs (parallel)** — `handlers/tier1-free-mcps.md`: invoke Context7, MS Learn, `gh search code/repos` IN PARALLEL when the classifier marks them applicable AND available. Dedup by URL/path; absent sources → `degraded_sources`.
5. **Tier 2 — web (concurrent fan-out)** — `handlers/tier2-web.md`: invoke web search + fetch in parallel when Tier 1 yields <5 high-quality hits, or the query has an explicit URL. EVERY available provider runs concurrently — Tavily (`mcp__tavily__tavily_search` / `tavily_extract`), Exa (`mcp__exa__web_search_exa` / `web_fetch_exa`), built-in `WebSearch`/`WebFetch` — merged and deduped by URL, tie-break Tavily > Exa > built-in (D-174-01/03). Each absent provider → `degraded_sources` (`"tavily"`, `"exa"`); a provider that raises or returns zero records its tool but never suppresses others (D-174-04 supersedes D-172-02 fall-through). Honor `--allowed-domains` / `--blocked-domains`.
6. **Tier 3 harvest (bounded wait)** — Harvest half of `handlers/tier3-notebooklm.md`. After Tiers 0-2 finish, do ONE blocking bounded wait on the detached job (the CLI's native wait, bounded by `AIENG_RESEARCH_NLM_WAIT_SEC`, default 300s, ceiling 900s — no poll loop). On `completed`: parse `--json` for `report_markdown` + discovered/imported sources. On `timeout`: the detached `--import-all` job keeps running — do NOT kill it; degrade and preserve `notebook_id`. On `failed`/`auth_required`: degrade gracefully. A later `--reuse-notebook=<id>` harvests the finished report. Detached deadline = `AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC` (default 1800s) mapped to CLI `--timeout`.
7. **Synthesize with citations + 3 directions** — `handlers/synthesize-with-citations.md`. Merge/dedup NotebookLM-discovered sources with Tier 0-2 sources; every external claim carries `[N]` or `[unsourced]`; end with EXACTLY 3 individually-cited directions. Validator regex `\[\d+\]|\[unsourced\]` must match ≥once per claim paragraph and per direction; on failure retry with a stricter system message (max 2 retries).
8. **Persist artifact** — `handlers/persist-artifact.md`. Write `.ai-engineering/runtime/research/<topic-slug>-<YYYY-MM-DD>.md` with frontmatter (`query`, `depth`, `tiers_invoked`, `sources_used`, `notebook_id`, `created_at`, `slug`), the Question/Findings/Sources/Notebook Reference sections, and an optional `## Deep Research Report` when the harvest completed. Auto-persist when Tier 3 was invoked; opt-in via `--persist` otherwise.

## CLI Flags

- **Tier 3 is default-on when available** — no flag enables it. It launches whenever `notebooklm doctor` exits 0 (D-175-04); the old source-count / comparative heuristics are gone (count is unknowable at T0).
- `--depth quick|standard|deep` (default `standard`). Controls **Tier 0-2** escalation only: `quick` = Tier 0+1; `standard` adds Tier 2; `deep` widens the fast tiers. Does NOT gate Tier 3.
- `--reuse-notebook=<id>` (opt-in). Re-attach to an existing notebook (CLI `-n <id>`) and harvest its report instead of creating one. Primary use: a prior run whose harvest timed out persisted `notebook_id` while the detached `--import-all` job kept running — this retrieves the now-finished report (AC6).
- `--persist` (opt-in). Forces persistence even when Tier 3 was not invoked (Tier-3 runs auto-persist).
- `--allowed-domains a.com,b.com` / `--blocked-domains x.com,y.com` — pass-through to every available provider (Tavily, Exa, built-in).

## Output Contract

Synthesized response in agent context PLUS, when persisted, a Markdown artifact at `.ai-engineering/runtime/research/<topic-slug>-<YYYY-MM-DD>.md`. The response ALWAYS ends with `## Recommended Directions` of EXACTLY 3 strategic directions, each cited `[N]` or `[unsourced]` (spec `notebooklm-async-tier3` D8/G7, AC5). Format:

```
## Question
<verbatim user query>

## Findings
<paragraphs with inline [N] citations or [unsourced] markers>

## Recommended Directions
1. **<title>** — <1-2 line rationale> [N]. Trade-off: <cost/risk>.
2. **<title>** — <rationale> [N]. Trade-off: <cost/risk>.
3. **<title>** — <rationale> [unsourced]. Trade-off: <cost/risk>.

## Sources
1. (title, url, accessed_at)
2. ...

## Notebook Reference
<NotebookLM notebook_id if Tier 3 was launched; "_(none)_" otherwise>

## Deep Research Report          # OPTIONAL — only when the NotebookLM
<verbatim deep-research report>  # bounded harvest completed within the wait window
```

All sections except `## Deep Research Report` are always present; it is appended only when the harvest completed (non-empty `report_markdown`). On timeout it is absent but `notebook_id` is recorded so a `--reuse-notebook=<id>` follow-up retrieves it.

## Common Mistakes

- Skipping Tier 0 and going straight to web search (defeats reuse).
- Claims without `[N]` / `[unsourced]` markers (defeats the citation hard-rule).
- Omitting `## Recommended Directions`, emitting other than EXACTLY 3, or leaving one uncited (violates AC5).
- Treating an absent tool as a hard failure — capability detection is fail-soft; a run MUST never error (D7).
- Running NotebookLM synchronously instead of launching it first in a background subagent (defeats the async overlap).
- Discarding `notebook_id` on harvest timeout (loses the `--reuse-notebook` follow-up path).
- Not deduping Tier 1 results, or failing to merge/dedup NotebookLM-discovered sources with Tier 0-2 sources at synthesis (Context7 / `gh search` / NotebookLM can return overlapping URLs).

## Examples

### Example — deep dive (NotebookLM default-on) persisted for reuse

User: "deep research on event-sourcing vs CQRS for fintech ledgers, save it for next time"

```
/ai-research "event sourcing vs CQRS for fintech ledgers" --depth deep --persist
```

NotebookLM launches at T0 (default-on) and overlaps Tiers 0-2 (Tavily ‖ Exa ‖ built-in WebSearch fan out concurrently). The harvested report + discovered sources fuse with tier sources; the artifact at `.ai-engineering/runtime/research/<slug>-<date>.md` carries `## Deep Research Report` and `notebook_id`, so future runs short-circuit at Tier 0. NotebookLM absent → run completes on Tiers 0-2, degraded source noted. Prior harvest timed out → `--reuse-notebook=<id>` retrieves the now-finished report (AC6).

## Integration

Called by: user directly, `/ai-brainstorm` (interrogate handler). Calls: tier0–tier3 handlers (Tier 3 launched first / harvested last), `synthesize-with-citations.md`, `persist-artifact.md`. Produces: `.ai-engineering/runtime/research/<slug>-<date>.md`. See also: `/ai-brainstorm` (consumes research as evidence).

$ARGUMENTS
