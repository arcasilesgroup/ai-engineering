---
spec: spec-174
slug: ai-research-tier2-parallel-fanout
title: "ai-research Tier-2 parallel Tavily+Exa fan-out"
status: approved
audience: framework-dev
summary: >-
  Change /ai-research Tier-2 web from a sequential first-available cascade
  (Tavily -> Exa -> built-in, one bounded fall-through) to a concurrent
  fan-out: run every available provider (Tavily, Exa, built-in WebSearch) at
  once and merge+dedup by URL with Tavily > Exa > built-in tie-break.
  Supersedes the D-172-02 fall-through; skip heuristic and citation contract
  unchanged.
---

# ai-research Tier-2 parallel Tavily+Exa fan-out

## Summary

Today `/ai-research` Tier 2 (web) is a **sequential first-available cascade**:
Tavily (primary) → Exa (secondary) → built-in WebSearch (fallback). Only the
first available provider runs; Exa runs only when Tavily is absent, or when
Tavily raises / returns zero results (the D-172-02 bounded fall-through). In the
happy path **Exa never runs** (`tier2-web.md:57-99`, `SKILL.md:41`).

This spec changes Tier 2 to a **concurrent fan-out**: every available provider
runs at once (Tavily ‖ Exa ‖ built-in WebSearch), and their results are merged
and deduped by URL. On a duplicate URL the higher-priority provider's row wins
(**Tavily > Exa > built-in**). The bounded fall-through is superseded — running
all providers IS the resilience. Fan-out is **always-on** at `--depth standard`
and `deep` (owner accepts the extra paid API calls); the Tier-1 skip heuristic
and the citation / 3-directions output contract are unchanged.

## Goals

- Tier 2 runs **all available** web providers concurrently — Tavily
  (`mcp__tavily__tavily_search`/`tavily_extract`), Exa
  (`mcp__exa__web_search_exa`/`web_fetch_exa`), and built-in `WebSearch`/`WebFetch`
  — instead of selecting only the first available.
- Merge + **dedup by URL** across all providers; on a duplicate URL keep the
  higher-priority provider's metadata, priority **Tavily > Exa > built-in**.
- Always-on fan-out at `--depth standard` and `deep` (no new flag, no depth gate).
- Each provider that is absent, raises, or returns zero results is recorded in
  `degraded_sources` (fail-soft, never raises) — but no fall-through step.
- Explicit-URL fetch also fans out across available providers, deduped by the
  same tie-break.
- Keep the handler (`tier2-web.md`), the lockstep helper
  (`tests/integration/_ai_research_tier2_helper.py`), its tests, `SKILL.md`, and
  all mirror/template surfaces in sync.

## Non-Goals

- No change to Tier 0 (local), Tier 1 (Context7/MS Learn/`gh search`), or Tier 3
  (NotebookLM) behavior.
- No new web providers beyond the existing three.
- No change to the citation contract, the `## Recommended Directions` 3-direction
  output, or the synthesize handler's dedup/citation assignment.
- No change to `--allowed-domains` / `--blocked-domains` pass-through semantics.
- No new flag and no depth-gating of fan-out (rejected: always-on per D-174-02).
- No change to the Tier-1 skip heuristic (`tier1_hits >= 5` AND no explicit URL).

## Decisions

### D-174-01 — Concurrent fan-out replaces the first-available cascade

Tier 2 dispatches the search (and explicit-URL fetch) of **every available
provider** concurrently — Tavily, Exa, and built-in WebSearch — and collects all
their hits, rather than selecting only the first available provider.

**Rationale:** the owner wants Tavily and Exa results together, not
mutually-exclusive. Fan-out maximizes breadth/recency in one pass; parallel
dispatch keeps wall-clock at the slowest provider, not the sum.

### D-174-02 — Always-on at standard and deep (no depth gate, no flag)

Fan-out runs whenever Tier 2 runs (i.e. `--depth standard` and `deep`), for
every available provider. No new flag; depth still controls only tier escalation.

**Rationale:** owner explicitly accepted the cost of running all providers every
Tier-2 for maximum coverage; gating by depth or flag adds complexity the owner
rejected. The Tier-1 skip heuristic still short-circuits the well-covered path.

### D-174-03 — Merge + dedup by URL, tie-break Tavily > Exa > built-in

Results from all providers are merged and deduped by normalized URL. On a
duplicate URL, the row from the higher-priority provider is kept and the lower
ones dropped; priority order is **Tavily > Exa > built-in WebSearch**. Each hit
records its originating provider.

**Rationale:** deterministic and simple; Tavily is the established primary so its
metadata wins on collision, with Exa over the lower-quality built-in. Avoids the
extra merge-fields logic the owner did not request.

### D-174-04 — Supersede D-172-02 (bounded fall-through is removed)

The single bounded fall-through on raise-or-empty is removed. Running all
available providers concurrently is the resilience; a provider that raises or
returns zero simply contributes nothing and is recorded in `degraded_sources`.

**Rationale:** fall-through is meaningless when every provider already runs.
Keeping it would be dead logic. Hard supersede, no shim (CONSTITUTION.md §3).

### D-174-05 — Skip heuristic and Tier-2 entry conditions unchanged

Tier 2 still runs only when Tier 1 produced `< 5` high-quality hits OR the query
references an explicit URL; `tier1_hits >= 5` AND no explicit URL still skips
Tier 2 entirely. Explicit-URL fetch fans out across providers, deduped by the
D-174-03 tie-break.

**Rationale:** the entry heuristic is orthogonal to provider selection and works
today; changing it is out of scope and would dilute the cost control.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cost: 2-3 paid API calls per Tier-2 (was 1) | High | Medium | Skip heuristic still short-circuits when Tier 1 covers; owner accepted the cost (D-174-02). |
| More raw hits → duplicate/noise | Medium | Low | URL dedup (D-174-03); synthesizer handles citation assignment downstream. |
| Handler ↔ lockstep helper drift (the design contract) | Medium | Medium | Update `tier2-web.md` + `_ai_research_tier2_helper.py` + tests together; parity is the contract. |
| Built-in WebSearch always running adds lower-quality hits | Medium | Low | Dedup tie-break deprioritizes built-in; synthesizer cites the best source. |
| Latency from the slowest provider | Low | Low | Concurrent dispatch — wall-clock = max(provider), not sum. |
| Mirror/template surfaces miss the handler+SKILL change | Medium | Low | Propagate via `ai-eng dev sync`; verify template twins. |
