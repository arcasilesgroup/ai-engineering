---
name: ai-research
description: "External evidence with citations via a 4-tier escalation (local → free MCPs → web/Exa → NotebookLM autonomous deep research, launched first / harvested last). Every claim sourced [N] or marked [unsourced]; output ends with 3 cited recommended directions. Trigger for 'what does the state of the art say about', 'compare options for', 'find sources on', 'investigate this question', 'research this'. Use for questions whose answer lives OUTSIDE the codebase. Not for codebase exploration; use /ai-explore instead. Not for refactors; use /ai-simplify instead. Not for business-logic debugging; use /ai-debug instead."
effort: mid
model_tier: sonnet
argument-hint: "[query] [--depth quick|standard|deep] [--reuse-notebook=id] [--persist]"
---


# Research

## Purpose

Multi-tier, multi-source research skill with citation-first synthesis and persistent artifact reuse. Replaces ad-hoc `WebSearch` invocations with a disciplined escalation, but with NotebookLM's autonomous deep research running **async-first**: when NotebookLM is available it is launched FIRST (at T0, in a background subagent) so its slow autonomous deep-research job overlaps the fast tiers, then it is harvested LAST with a bounded wait. The fast tiers run meanwhile -- local context first (zero cost), then free MCPs (Context7, Microsoft Learn, `gh search`), then web search as a concurrent fan-out of every available provider (Tavily, Exa, and the built-in `WebSearch`), merged and deduped by URL. Every external claim carries a `[N]` citation or is marked `[unsourced]` so readers can audit grounding, and the output always ends with exactly 3 recommended strategic directions.

Every external tier (NotebookLM, Context7, Exa, MS Learn) is capability-detected and fail-soft: an absent or unauthenticated tool is skipped silently (recorded as degraded) and never errors the run. NotebookLM (Tier 3) runs through the `notebooklm-py` CLI and is gated by `notebooklm doctor` (exit 0 = available).

Outputs are designed for reuse: research is persisted to `.ai-engineering/runtime/research/<topic-slug>-<YYYY-MM-DD>.md` -- including the NotebookLM deep-research report and `notebook_id` -- so subsequent sessions short-circuit at Tier 0 or harvest a still-running notebook via `--reuse-notebook`.

## When to Use

- User asks for evidence: "what does the industry do for X", "state of the art on Y", "compare A vs B", "find sources on Z".
- `/ai-brainstorm` interrogation flags a question requiring external evidence (handler `interrogate.md` invokes this skill).
- User wants a verifiable, cited answer rather than the model's training-data recall.
- Research worth archiving for the team (deep technical investigations, library comparisons, architecture decisions).

### Off-ramp -- when to use `/ai-explore` instead

`/ai-research` answers questions whose source-of-truth lives **outside** this repository (web, docs portals, third-party APIs, academic papers). For questions whose answer lives **inside** this repo's files (architecture, dependency graph, pattern usage), dispatch `/ai-explore` instead -- it's read-only, codebase-only, and produces a structured architecture map rather than a cited narrative.

Do NOT use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Process

The order below is the **execution timeline**, not a strict gate sequence: Tier 3 is *launched* first and *harvested* last, so its autonomous deep-research job runs concurrently with the fast Tiers 0-2.

1. **Classify query** -- follow `handlers/classify-query.md` to decide which Tier 1 MCPs apply (library mention → Context7; Azure/Microsoft → MS Learn; real-world-code question → `gh search`; explicit URL → mark for fetch). NotebookLM (Tier 3) is NOT gated here -- it is default-on whenever available (see step 2).
2. **Tier 3 launch (T0, background, default-on)** -- follow the Launch half of `handlers/tier3-notebooklm.md`. The `notebooklm doctor` capability/auth gate runs INSIDE the background subagent -- before any `create_notebook`/`add_research`; on a non-zero exit the subagent degrades at T0 (a warning, no blocking banner) and the main agent proceeds on Tiers 0-2 (fail-soft). When NotebookLM is available, launch its autonomous deep-research job FIRST in a background subagent as ONE DETACHED CLI command (`notebooklm source add-research "<query>" -n <notebook> --from web --mode deep --import-all --timeout <N> --json`) so it overlaps the fast tiers. `--import-all` imports the discovered sources; the detached job keeps running regardless of the run's lifetime. This runs **by default with no flag**; when NotebookLM is absent/unauthenticated the launch short-circuits to degraded (recorded, never raised) and the run proceeds on Tiers 0-2.
3. **Tier 0 -- local** -- follow `handlers/tier0-local.md`. Search prior research artifacts, `LESSONS.md`, and `framework-events.ndjson` for prior `/ai-research` invocations. If ≥3 relevant hits, the agent MAY short-circuit the fast tiers and synthesize from local context (the Tier 3 job is still harvested in step 6).
4. **Tier 1 -- free MCPs (parallel)** -- follow `handlers/tier1-free-mcps.md`. Invoke Context7, Microsoft Learn, and `gh search code/repos` IN PARALLEL when the classifier marks them applicable AND each is available (per-source capability detection). Dedup by URL/path; absent sources are recorded in `degraded_sources`.
5. **Tier 2 -- web (concurrent fan-out: Tavily ‖ Exa ‖ built-in)** -- follow `handlers/tier2-web.md`. Invoke web search + fetch in parallel when Tier 1 produced fewer than 5 high-quality hits, or the query references an explicit URL. EVERY available provider runs concurrently -- Tavily (`mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`), Exa (`mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`), and the built-in `WebSearch` / `WebFetch` -- and their hits are merged and deduped by URL with the tie-break Tavily > Exa > built-in (spec-174 D-174-01/03). Each absent provider is recorded in `degraded_sources` (`"tavily"`, `"exa"`); a provider that raises or returns zero records its tool but never suppresses the others (D-174-04 supersedes the D-172-02 fall-through). Honor `--allowed-domains` and `--blocked-domains`.
6. **Tier 3 harvest (bounded wait)** -- follow the Harvest half of `handlers/tier3-notebooklm.md`. After Tiers 0-2 finish, do ONE blocking bounded wait on the detached job (the CLI's native wait, bounded by `AIENG_RESEARCH_NLM_WAIT_SEC`, default 300s, ceiling 900s -- no poll loop). On `completed`, parse the `--json` result for the deep report (`report_markdown`) and the sources NotebookLM discovered + imported. On `timeout`, the detached `--import-all` job keeps running -- do NOT kill it; degrade and preserve `notebook_id`. On `failed`/`auth_required`, degrade gracefully. Either way a later `--reuse-notebook=<id>` harvests the finished, imported report. The detached job's own deadline is `AIENG_RESEARCH_NLM_DEEP_TIMEOUT_SEC` (default 1800s) mapped to the CLI `--timeout`.
7. **Synthesize with citations + 3 directions** -- follow `handlers/synthesize-with-citations.md`. Merge (dedup) the NotebookLM-discovered sources with the Tier 0-2 sources, then produce output where every external claim carries `[N]` or `[unsourced]` and which ends with EXACTLY 3 recommended directions (each individually cited). Validator regex `\[\d+\]|\[unsourced\]` must match at least once per claim paragraph and per direction; on failure, retry with a stricter system message (max 2 retries).
8. **Persist artifact** -- follow `handlers/persist-artifact.md`. Write `.ai-engineering/runtime/research/<topic-slug>-<YYYY-MM-DD>.md` with frontmatter (`query`, `depth`, `tiers_invoked`, `sources_used`, `notebook_id`, `created_at`, `slug`), the Question/Findings/Sources/Notebook Reference sections, and -- when the harvest completed -- an optional `## Deep Research Report`. Auto-persist when Tier 3 was invoked; opt-in via `--persist` otherwise.

## CLI Flags

- **NotebookLM deep research is default-on when available** -- there is NO flag to enable it. It launches whenever the `notebooklm doctor` capability/auth gate exits 0 (spec-175 D-175-04); the source-count / comparative heuristics that used to gate it are gone (the count is unknowable at T0, when the background launch happens).
- `--depth quick|standard|deep` (default: `standard`). Controls **Tier 0-2** escalation only -- `quick` runs Tier 0+1; `standard` adds Tier 2; `deep` widens the fast tiers. It does NOT gate Tier 3 (which is independently default-on when available).
- `--reuse-notebook=<id>` (opt-in). Re-attach to an existing NotebookLM notebook (the CLI `-n <id>`) instead of creating one, and harvest its deep-research report. The primary use is following up a prior run whose harvest timed out: the earlier run persisted `notebook_id` in its artifact while the detached `--import-all` job kept running, and `--reuse-notebook=<id>` retrieves the now-finished, imported report (AC6).
- `--persist` (opt-in). Forces artifact persistence even when Tier 3 was not invoked (Tier-3 runs auto-persist).
- `--allowed-domains a.com,b.com` (pass-through to every available provider's web search call -- Tavily, Exa, and built-in).
- `--blocked-domains x.com,y.com` (pass-through to every available provider's web search call -- Tavily, Exa, and built-in).

## Output Contract

Synthesized response in agent context PLUS, when persisted, a Markdown artifact at `.ai-engineering/runtime/research/<topic-slug>-<YYYY-MM-DD>.md`. The response ALWAYS ends with a `## Recommended Directions` block of EXACTLY 3 strategic directions ("rumbo"), each individually cited with `[N]` or `[unsourced]` (spec `notebooklm-async-tier3` D8/G7, AC5). Output format:

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

## Deep Research Report          # OPTIONAL — present only when the NotebookLM
<verbatim deep-research report>  # bounded harvest completed within the wait window
```

`## Recommended Directions`, `## Question`, `## Findings`, `## Sources`, and `## Notebook Reference` are always present. `## Deep Research Report` is appended only when the NotebookLM harvest completed (non-empty `report_markdown`); on harvest timeout it is absent but `notebook_id` is still recorded so a `--reuse-notebook=<id>` follow-up can retrieve it.

## Common Mistakes

- Skipping Tier 0 and going straight to web search (defeats the reuse goal).
- Producing claims without `[N]` or `[unsourced]` markers (defeats the citation hard-rule).
- Omitting the `## Recommended Directions` block, or emitting other than EXACTLY 3 directions, or leaving a direction uncited (violates the output contract / AC5).
- Treating an absent tool as a hard failure. Capability detection is fail-soft: a missing or unauthenticated NotebookLM / Context7 / Exa / MS Learn is skipped silently, recorded in `degraded_sources`, and the run still returns output -- it MUST never error (D7).
- Running the NotebookLM deep research synchronously instead of launching it first in a background subagent (defeats the async overlap -- the slow Tier 3 job should run while Tiers 0-2 execute, then be harvested with a bounded wait).
- Discarding `notebook_id` on harvest timeout (loses the `--reuse-notebook` follow-up path; the report finishes later but cannot be retrieved).
- Not deduplicating Tier 1 results, or failing to merge/dedup NotebookLM-discovered sources with the Tier 0-2 sources at synthesis (Context7 / `gh search` / NotebookLM can return overlapping URLs).

## Examples

### Example 1 — quick state-of-the-art lookup

User: "what's the current best practice for OAuth refresh-token rotation?"

```
/ai-research "OAuth refresh-token rotation best practices" --depth quick
```

If NotebookLM is available, an autonomous deep-research job launches first in the background; meanwhile Tier 0 checks local artifacts and Tier 1 queries Context7 / Microsoft Learn. The deep job is harvested with a bounded wait, sources are merged, and the answer ends with a Findings block (inline `[N]`) plus 3 cited recommended directions. If NotebookLM is absent, the run completes on Tiers 0-1 and notes the degraded source.

### Example 2 — deep dive (NotebookLM default-on) persisted for reuse

User: "deep research on event-sourcing vs CQRS for fintech ledgers, save it for next time"

```
/ai-research "event sourcing vs CQRS for fintech ledgers" --depth deep --persist
```

NotebookLM deep research launches at T0 (no flag needed -- default-on when available) and overlaps Tiers 0-2 (Tier 2 fans out Tavily, Exa, and the built-in WebSearch concurrently). The harvest's deep report and discovered sources fuse with the tier sources; the artifact at `.ai-engineering/runtime/research/<slug>-<date>.md` carries the `## Deep Research Report` and `notebook_id` so future invocations short-circuit at Tier 0.

### Example 3 — harvest a notebook that finished after a prior timeout (AC6)

User: a prior run timed out waiting on the deep job; its artifact recorded `notebook_id: nlm-abc123`.

```
/ai-research "event sourcing vs CQRS for fintech ledgers" --reuse-notebook=nlm-abc123
```

Re-attaches to the existing notebook (the CLI `-n <id>`, no `create_notebook`), harvests the now-finished, imported deep-research report, and re-synthesizes with the report included.

## Integration

Called by: user directly, `/ai-brainstorm` (interrogate handler). Calls: tier0–tier3 handlers (Tier 3 launched first / harvested last), `synthesize-with-citations.md`, `persist-artifact.md`. Produces: `.ai-engineering/runtime/research/<slug>-<date>.md`. See also: `/ai-brainstorm` (consumes research as evidence).

$ARGUMENTS
