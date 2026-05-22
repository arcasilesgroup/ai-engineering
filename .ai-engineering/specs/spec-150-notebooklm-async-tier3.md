---
spec: spec-150
slug: notebooklm-async-tier3
title: Async-first NotebookLM autonomous deep research (Tier 3 redesign)
status: approved
summary: "Async-first /ai-research Tier 3: NotebookLM autonomous deep research launched first (background) and harvested last, overlapping Tiers 0-2. Backend swapped to claude-world/notebooklm-skill (nlm_* tools); Exa wired into Tier 2; capability fail-soft; output ends with exactly 3 cited recommended directions."
---

# Async-first NotebookLM autonomous deep research — /ai-research Tier 3 redesign

## Summary

Redesign `/ai-research` so NotebookLM (Tier 3) runs an **autonomous deep-research
job launched FIRST** (in a background subagent) and **harvested LAST**, overlapping
with Tiers 0–2 — instead of running last and consuming Tier 1+2 URLs. Swap the
NotebookLM backend from `pleaseprompto/notebooklm-mcp` to
`claude-world/notebooklm-skill` (`uvx --from notebooklm-skill notebooklm-mcp`, 13
`nlm_*` tools; MCP config already aligned in Claude user-scope + Codex
`mcp_servers`). Wire **Exa** into Tier 2 web search (currently unused — Tier 2 uses
the built-in `WebSearch`). Make all external tiers (NotebookLM, Context7, Exa)
**capability-detected and fail-soft**: absent tools are skipped, never error. Extend
the output contract to return the cited research narrative **PLUS exactly 3
recommended strategic directions** ("rumbo").

## Goals

- **G1** — Launch NotebookLM deep research at T0 in a background subagent,
  overlapping Tiers 0–2; harvest at the end with a bounded wait.
- **G2** — NotebookLM autonomous deep research is the DEFAULT (no flag) whenever the
  tool is available — the simplest path.
- **G3** — Swap backend to `claude-world/notebooklm-skill`: replace the tool surface
  (`server_info`/`notebook_create`/`source_add`/`notebook_query` →
  `nlm_list`/`nlm_create_notebook`/`nlm_add_source`/`nlm_research`/`nlm_ask`) and the
  auth probe (`nlm login --check` / `~/.notebooklm/storage_state.json`). Handler +
  lockstep helper + tests stay in sync.
- **G4** — Wire Exa (`mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`) as the
  Tier 2 web provider.
- **G5** — Capability detection + fail-soft for NotebookLM, Context7, Exa: a missing
  or unauthenticated tool is skipped silently (recorded as degraded), never fails the
  run.
- **G6** — Merge NotebookLM-discovered sources with Tier 0–2 sources at synthesis
  (dedup); on harvest timeout, degrade gracefully and persist `notebook_id` for a
  later `--reuse-notebook` harvest.
- **G7** — Output returns the research synthesis (with `[N]` citations) PLUS exactly
  3 recommended directions, each with rationale + trade-off + cited evidence.

## Non-Goals

- Not changing Tier 0 (local) or Tier 1 routing beyond capability-detection + dedup
  with NotebookLM.
- Not implementing notebook auto-cleanup/GC — a new notebook per run is acceptable;
  `--reuse-notebook` stays opt-in.
- Not building a generic async-job framework; the background-subagent pattern is
  scoped to NotebookLM Tier 3.
- Not adding artifact generation (`nlm_generate`/`nlm_download`: podcast/slides/quiz)
  in v1.
- Not performing interactive Google auth (`uvx notebooklm login`) — a one-time
  operator step.
- Not migrating other skills off the built-in `WebSearch`.

## Decisions

- **D1 (async mechanism)** — Background subagent (`Agent` `run_in_background`) blocks
  on `nlm_research(mode=deep)` at T0; main runs Tiers 0–2; harvest at end.
  *Rejected:* Python client `start`/`poll` bypassing MCP (out-of-MCP dependency +
  dual code path); synchronous research-last (no time saved).
- **D2 (source model)** — Merge at synthesis: NotebookLM discovers its own sources;
  Tiers 0–2 run independently; synthesizer fuses + dedups. *Rejected:*
  augment-then-reask (reintroduces dependency, kills parallelism); autonomous-isolated
  (wastes Tier 1–2 sources).
- **D3 (trigger)** — NotebookLM deep research runs BY DEFAULT when available; no
  `--depth=deep`/comparative gating. Drops the `≥10-sources` signal (unknowable at
  T0). *Rejected:* deep|comparative-only; deep-only-explicit (both less simple).
- **D4 (harvest wait)** — Bounded wait (default ≈5 min, env-tunable) after Tiers 0–2;
  on timeout, synthesize without NotebookLM + persist `notebook_id` so a later
  `--reuse-notebook` harvests the report. *Rejected:* block-until-done (unbounded
  hang); no-wait (current run lacks the deep report).
- **D5 (backend)** — `claude-world/notebooklm-skill` via `uvx --from notebooklm-skill
  notebooklm-mcp` (config already aligned: Claude user-scope + Codex `mcp_servers`).
  Auth via `~/.notebooklm/storage_state.json`; probe `nlm_list` / `login --check`,
  replacing `server_info` / `nlm login`.
- **D6 (Exa)** — Tier 2 uses Exa (`web_search_exa` + `web_fetch_exa`) as the web
  provider; built-in `WebSearch`/`WebFetch` becomes the fallback when Exa is absent.
- **D7 (fail-soft)** — Every external tool (NotebookLM, Context7, Exa, MS Learn) is
  capability-detected; absent/unauthed → skipped + appended to `degraded_sources`,
  never raised. Reuses the existing degraded pattern.
- **D8 (output)** — Append a `## Recommended Directions` section with EXACTLY 3
  options, each: title, 1–2 line rationale, trade-off, and `[N]`-cited evidence.

## Acceptance Criteria

- **AC1** — With NotebookLM available, a run launches the deep-research subagent
  before Tier 1 begins (observable ordering) and includes the deep report in the
  final synthesis when it completes within the wait window.
- **AC2** — With NotebookLM absent/unauthed, the run completes using Tiers 0–2 only,
  emits a visible degraded note, and exits 0.
- **AC3** — Tier 2 issues `web_search_exa` when Exa is available; falls back to
  built-in `WebSearch` when not.
- **AC4** — With Context7 / Exa absent, those tiers are skipped silently
  (`degraded_sources` records them); the run still returns output.
- **AC5** — Output always ends with exactly 3 recommended directions, each carrying
  ≥1 `[N]` citation or `[unsourced]`.
- **AC6** — On harvest timeout, output notes NotebookLM is still running and the
  artifact persists `notebook_id`; a follow-up `--reuse-notebook=<id>` retrieves the
  report.
- **AC7** — `handlers/tier3-notebooklm.md` and
  `tests/integration/_ai_research_tier3_helper.py` describe the SAME algorithm
  (lockstep), validated by tests; tier2 + synthesize tests updated.

## Affected Surfaces

- `.claude/skills/ai-research/SKILL.md` (process, tiers, flags, output contract,
  examples, common mistakes) + mirror regen (`.codex/`, `.gemini/`, `.github/` via
  `scripts/sync_mirrors`).
- `handlers/tier2-web.md` (Exa), `tier3-notebooklm.md` (rewrite),
  `synthesize-with-citations.md` (merge + 3 directions), `classify-query.md`
  (default-deep), `persist-artifact.md` (`notebook_id`).
- `tests/integration/_ai_research_tier3_helper.py` (lockstep rewrite) +
  tier2/tier3/synthesize tests.
- New env tunable for the harvest timeout (e.g., `AIENG_RESEARCH_NLM_WAIT_SEC`).

## Risks

- **R1** — NotebookLM backends are unofficial browser automation → fragile / auth
  expiry. *Mitigation:* capability probe + fail-soft + bounded wait.
- **R2** — The background subagent must have the `notebooklm` MCP loaded in its
  context; if it cannot access it, the async launch fails. *Mitigation:* verify MCP
  availability in the subagent; degrade.
- **R3** — Default-on deep research → notebook proliferation + cost/latency per run.
  *Mitigation:* `--reuse-notebook`; documented; cleanup is a non-goal.
- **R4** — The lockstep helper now models async/background → harder to test
  deterministically. *Mitigation:* inject clock + job-status callable; test
  timeout/degrade branches with mocks.
- **R5** — Exa quota/cost/rate limits. *Mitigation:* fallback to built-in
  `WebSearch`; honor allowed/blocked domains.
- **R6** — Branch collision: the current branch is `spec-147-wave-1` (active). This
  spec MUST be planned/built on its own branch off `main`; do not mix with spec-147.

## Open Questions

- **OQ1** — Exact bounded-wait default (5 min?) and env var name.
- **OQ2** — Does MCP `nlm_research` block until done or return a job handle? If it
  returns early, the subagent wait model simplifies. Verify during `/ai-plan` against
  the live tool.
- **OQ3** — Are the 3 directions derived by the synthesizer LLM from merged evidence,
  or partly from NotebookLM's report? (Lean: synthesizer-derived, evidence-cited.)
