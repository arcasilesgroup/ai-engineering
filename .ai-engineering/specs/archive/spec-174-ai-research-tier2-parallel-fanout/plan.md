---
title: "Plan — spec-174 ai-research Tier-2 parallel Tavily+Exa fan-out"
spec: spec-174
slug: ai-research-tier2-parallel-fanout
status: approved
pipeline: full
execution_route:
  version: 1
  spec: spec-174
  executor: build
  automation: build
  concern_count: 1
  estimated_files: 5
  reason: "Single cohesive concern (Tier-2 provider model: cascade -> fan-out) but a behavior change with a substantial lockstep test rewrite + handler/SKILL docs + mirror propagation. Judgment-heavy (no mechanical patches) so mid-tier dispatch."
  safe_next_command: "/ai-build"
safe_next_command: "/ai-build"
---

# Plan — spec-174: Tier-2 parallel Tavily+Exa fan-out

## Architecture

Pattern: `ad-hoc` rewrite of one pure function and its lockstep tests. No new
modules; the `tier2_web` public signature is UNCHANGED (same keyword-only
params), so callers and the `_call_tier2` test wrapper stay intact — only the
internal algorithm and the test assertions change.

New `tier2_web` algorithm (replaces the cascade in
`tests/integration/_ai_research_tier2_helper.py`):

1. `explicit_url = detect_explicit_url(query)`.
2. **Skip heuristic UNCHANGED** (D-174-05): `len(tier1_hits) >= 5` AND no
   explicit URL → `Tier2Result(skipped=True)`.
3. Build candidates in priority order `[tavily, exa, builtin]` (the `_Candidate`
   dataclass + tool-name constants stay).
4. Absent providers with a marker → append `"tavily"` / `"exa"` to `degraded`
   (built-in floor has no marker).
5. `available = [c for c in candidates if c.available]` (priority order).
6. **Fan-out (D-174-01):** run the search (+ explicit-URL fetch) of EVERY
   available provider CONCURRENTLY — reuse `_run_provider` per provider, fanned
   out across an outer `ThreadPoolExecutor` (wall-clock = slowest provider).
7. **Degraded (D-174-04, no fall-through):** for each available provider whose
   search raised OR returned zero, append its `search_tool` to `degraded`; plus
   any raised fetch tool (`failed_tools`). Dedup markers preserving first-seen
   order. DELETE the primary/fallback selection and the bounded fall-through
   block entirely.
8. **Merge + dedup by URL (D-174-03):** iterate providers in PRIORITY order
   (Tavily → Exa → built-in); add each hit whose `url` was not already seen
   (Tavily wins a duplicate URL); hits without a `url` key are always kept.
9. Return `Tier2Result(hits=deduped, skipped=False, degraded_sources=degraded)`.

## Phases

### Phase 1 — RED: rewrite the lockstep tests to fan-out semantics

- [x] T-1 — Rewrite `test_ai_research_tier2.py` for the fan-out contract
  - Agent: build
  - Files: `tests/integration/test_ai_research_tier2.py`
  - Principles applied: §10.5 TDD (RED before GREEN), §10.7 Clean Code
  - Patch (deterministic): N/A — judgment rewrite. Concretely:
    - Invert the "only the selected provider runs" assertions: under fan-out
      ALL available providers' searches run (e.g. `test_tavily_used_as_primary_when_available`,
      `test_exa_used_as_primary_when_available`, `test_falls_to_exa_when_tavily_unavailable`
      now assert every available `*_search.calls` ran once).
    - DELETE / replace the bounded-fall-through suite (D-174-04 removes it):
      `test_tavily_raise_falls_through_to_exa_once`, `test_tavily_empty_falls_through_to_exa_once`,
      `test_exa_empty_falls_through_to_builtin_once_when_tavily_absent`,
      `test_second_provider_empty_does_NOT_fall_through_again`,
      `test_fall_through_preserves_explicit_url_fetch`. Replace with fan-out
      tests: all available run concurrently; a raising/empty provider records
      its tool in `degraded_sources` but does NOT suppress the others.
    - `hits` assertions become the MERGED+DEDUPED set across providers, with the
      Tavily>Exa>built-in tie-break on a shared URL (add a dedup test where
      Tavily and Exa return the SAME url → Tavily row kept).
    - Domain-filter tests: assert the filter passed to EVERY available provider's
      search (not just the selected one).
    - Keep unchanged: skip-heuristic tests (`test_tier2_skipped_...`,
      `test_skip_threshold_boundary`, `test_tier2_runs_when_*`), the
      signature test, and the search/fetch parallel-start test.
  - Gate: `pytest tests/integration/test_ai_research_tier2.py` FAILS against the
    current cascade helper (RED proven) before T-2.

### Phase 2 — GREEN: rewrite the helper to fan-out

- [x] T-2 — Replace the cascade+fall-through in `_ai_research_tier2_helper.py` with fan-out
  - Agent: build
  - Files: `tests/integration/_ai_research_tier2_helper.py:144-263`
  - Principles applied: §10.1 KISS (delete fall-through dead-path), §10.3 SOLID (single function, injected deps unchanged), §10.5 TDD (make T-1 green)
  - Patch (deterministic): N/A — judgment rewrite per the Architecture algorithm
    (steps 5-9). Keep signature, `_Candidate`, tool-name constants, skip
    heuristic, `_run_provider`. Remove `primary`/`fallback` selection + the
    `if search_failed:` fall-through block. Add the outer fan-out executor + the
    priority-order URL dedup merge. Update the module + function docstrings from
    "cascade / one bounded fall-through (D-172-02)" to "concurrent fan-out
    (D-174-01..04)".
  - Gate: `pytest tests/integration/test_ai_research_tier2.py` GREEN.

### Phase 3 — Docs: handler + SKILL describe fan-out, supersede D-172-02

- [x] T-3 — Rewrite `tier2-web.md` algorithm + status to fan-out
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/tier2-web.md:9-17,57-107,124-165`
  - Principles applied: §10.6 SDD (handler ↔ helper stay 1:1), §10.7 Clean Code
  - Patch (deterministic): N/A — prose. Rewrite §"Web Provider" + Steps 3-5 +
    Resilience + Status: "ordered capability cascade with one bounded
    fall-through" → "concurrent fan-out of all available providers, merge+dedup
    by URL (Tavily>Exa>built-in)". State D-174-04 supersedes D-172-02.
  - Gate: no stale "cascade"/"fall-through"/"first available"/"D-172-02 fall-through"
    language remains in `tier2-web.md`; handler matches the helper algorithm.

- [x] T-4 — Update `SKILL.md` Tier-2 wording + example
  - Agent: build
  - Files: `.claude/skills/ai-research/SKILL.md:16,41,3`
  - Principles applied: §10.6 SDD, §10.4 DRY (canonical edited once; mirrors generated)
  - Patch (deterministic): N/A — prose. Line 41 (Tier-2 step) and line 16
    (capability detection) reworded from primary/secondary cascade to
    parallel fan-out + URL-dedup; description line 3 phrasing if it implies
    single-provider web. Keep the citation / 3-directions contract untouched.
  - Gate: `SKILL.md` Tier-2 text says fan-out (Tavily+Exa concurrent); no
    "primary/secondary fall-through" framing remains.

### Phase 4 — Propagate mirrors

- [x] T-5 — Regenerate mirror + template surfaces via dev sync
  - Agent: build
  - Files: `.codex/`, `.opencode/`, `.github/`, `.agents/`, `src/ai_engineering/templates/project/...` (ai-research SKILL.md + handlers)
  - Principles applied: §10.4 DRY (generator propagates canonical), §10.6 SDD (mirror/template parity contract)
  - Patch (deterministic): N/A — run the generator, do not hand-edit:
    ```
    ai-eng dev sync
    ```
  - Gate: `dev sync` clean; every ai-research SKILL.md / tier2-web.md mirror +
    template twin carries the fan-out wording (no `magenta`-style drift).

### Phase 5 — Verify

- [x] T-6 — Full test + parity verification
  - Agent: verify
  - Files: `tests/integration/test_ai_research_tier2.py`, `test_ai_research_resilience.py`, `test_ai_research_skill_present.py` (read-only)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Gate: `pytest tests/integration/test_ai_research_tier2.py tests/integration/test_ai_research_resilience.py tests/integration/test_ai_research_skill_present.py` all green; `ai-eng gate run --mode=local` 0 findings; no handler↔helper drift.

## Gate Criteria (plan-level)

- `tier2_web` runs all available providers concurrently and returns a
  URL-deduped merged hit list (Tavily>Exa>built-in tie-break); no fall-through
  path remains.
- Lockstep parity: `tier2-web.md` algorithm == `_ai_research_tier2_helper.py`.
- All ai-research integration tests green; local gate clean.
- Mirrors + template twins regenerated (no drift); only the ai-research surface
  + its tests changed (Non-Goals held: no Tier 0/1/3, citation contract, or
  domain-filter semantics touched).

## Quality Outcome

T-1..T-6 complete; one bounded quality-remediation pass consumed, then terminal reassessment PASS.

- **Implementation:** `tier2_web` rewritten cascade → concurrent fan-out (all available providers, priority-order URL dedup Tavily>Exa>built-in, fall-through removed, signature unchanged); handler + SKILL docs + mirrors via `dev sync`.
- **Review (ai-review + adversarial validator):** verdict sound/ship-worthy, no blocker/critical/high. One MEDIUM (F1: the handler Step-4 pseudo-code — the LLM-executed artifact — had `c.search_tool`-on-tuple + a leaked-loop-var bug while the Python oracle was correct) + 7 low.
- **Remediation (one bounded pass):** F1 fixed — Step 4 rewritten to mirror the helper 1:1 (`_Candidate` record + per-iteration `candidate = available[index]`), byte-identical across 8 mirror/template twins; F2 timing de-flaked to a peak-concurrency counter (5/5 loops); F4 mixed raise+empty degrade test; F7 omitted-domain-kwarg regression test; F8 plan note + resilience-test rename; F9 spec/handler wording → "exact URL string".
- **Terminal reassessment:** no remaining blocker/critical/high. 42 tests green (tier2 + resilience + skill-present + canonical-structure). `ai-eng gate run --mode=local` → 0 findings. Ruff clean. No suppressions.
- **Excluded from delivery:** `observations.yml` (pre-existing, owns PR #597).

## Notes

- `test_ai_research_resilience.py` imports `tier2_web` and DOES exercise the web
  layer: `test_exa_absent_falls_back_to_builtin_and_records_degraded` calls
  `tier2_web` with Tavily+Exa absent and asserts the built-in carries the search
  while `"exa"` lands in `degraded_sources`. That assertion holds unchanged under
  fan-out (an absent provider is still recorded; the built-in floor still runs),
  so the test stays green. Its remaining cases assert Tier-1/Tier-3 degraded
  sources (context7/ms_learn/gh_search/notebooklm). The test was renamed from the
  stale `falls_back`/cascade wording to fan-out-accurate naming (behavior and
  assertions unchanged); T-6 confirms.
- `test_ai_research_skill_present.py` checks handler-file PRESENCE only (no
  wording assertions) — doc rewrites do not break it.
- Degraded semantics shift under fan-out: a provider that ran but returned zero
  is now recorded in `degraded_sources` (D-174-04), where the old cascade only
  recorded the single selected provider's emptiness. New tests pin this.
