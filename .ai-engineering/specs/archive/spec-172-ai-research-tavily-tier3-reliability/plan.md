---
spec: spec-172
title: "Plan — spec-172 ai-research: Tavily web provider + NotebookLM Tier-3 reliability"
status: approved
pipeline: full
phases: 6
execution_route:
  version: 2
  spec: spec-172
  executor: build
  automation: hitl
  concern_count: 2
  estimated_files: 15
  reason: "Two-workstream /ai-research reliability spec (Tavily Tier-2 provider + NotebookLM Tier-3 bug-fixes) spanning ~15 hand-edited files. Auto-classifier routed autopilot (>=10 files); operator explicitly chose /ai-build single-stream (offered at plan STOP). Re-routed to executor: build per operator override — clean RED/GREEN pairs execute fine single-stream; waves sequenced to avoid same-file (SKILL.md, settings) races."
  safe_next_command: "/ai-build"
---

# Plan — spec-172 ai-research: Tavily web provider + NotebookLM Tier-3 reliability

## Design

Two independent workstreams over `/ai-research`, merged into one slot:

- **WS-A (Tavily, Tier 2):** turn today's hard single-selection (Exa → built-in)
  into a capability-detected cascade **Tavily → Exa → built-in** with **one
  bounded fall-through** on raise-or-empty (D-172-01, D-172-02). Wire Tavily via
  `mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract` (canonical server
  name `tavily`), allowlist + repo `.mcp.json` registration, operator docs.
- **WS-B (NotebookLM, Tier 3):** bug-fix only, **fail-soft kept**. Replace the
  phantom `job_status` poll with a real status-poll loop (D-172-05), fix the 404
  login command across 6 sites (D-172-06), align permissions to real
  `mcp__notebooklm__*` names (D-172-07), harden the harvest loop with back-off +
  retry + terminal-status branches (D-172-08), pre-check subagent MCP
  availability (D-172-11).

Lockstep parity (D-172-10) is enforced at every handler edit (helper twin +
`ai-eng dev sync` mirrors) and in the final verify phase.

## Architecture

Pattern: **ad-hoc / ports-and-adapters-lite** (§10.8). Search and NotebookLM
providers are injected callables behind capability flags — no provider registry,
no manifest keys (§10.2 YAGNI). The handler `.md` is the executable spec (§10.6
SDD); the `tests/integration/_ai_research_*_helper.py` files are the lockstep
reference implementations (AC7) and must stay byte-aligned in behavior with the
handler prose.

### Reconciliations applied (from the completeness-critic pass)

- **Permissions single-owner (critic gap #1/#2):** exactly ONE task owns each
  settings file's final content (T-25 local, T-26 template). NotebookLM uses the
  **6 explicit `mcp__notebooklm__nlm_*` names** on BOTH surfaces; Tavily uses the
  `mcp__tavily__*` glob on both. No glob/explicit drift.
- **D-172-09 no-banner (critic gap #3):** first-class RED test added (T-16).
- **SKILL.md phantom framing (critic gap #4):** SKILL.md:38 + :42 corrected
  inside T-22 (mechanism rewrite), not just the handler.
- **Template `.mcp.json` (critic gap #5):** intentionally NOT shipped — an API
  key cannot be committed (§13 secrets) and D-172-04 scopes server registration
  to the operator. The template allowlist entry is harmless: absent Tavily MCP
  is fail-soft (cascade degrades to Exa). Documented in T-8.

### Cross-task file touch notes

- `SKILL.md` is edited on distinct lines by **T-7** (:41 Tier-2 summary) and
  **T-22** (:38, :42 Tier-3 mechanism) — no overlap.
- `src/ai_engineering/templates/project/.claude/settings.json:16` is edited by
  **T-26 only** (merges the Tavily entry + NotebookLM rename — never both tasks).
- `tunable doc` lives in CANONICAL source (root + template `CLAUDE.md` are
  generated); **T-24** edits CANONICAL, then `ai-eng dev sync` regenerates.

---

## Phase 1 — WS-A Tavily: RED tests (§10.5)

- [x] T-1 — RED: tier2_web accepts Tavily provider params
  - Agent: build
  - Files: tests/integration/test_ai_research_tier2.py:31-34, tests/integration/test_ai_research_tier2.py:108-131
  - Principles applied: §10.5 TDD, §10.3 SOLID (DIP — providers injected as callables)
  - Patch (deterministic): insert after the imports block (after line 34):
    ```python
    def test_tier2_web_accepts_tavily_provider_params() -> None:
        """RED: tier2_web must accept tavily_search/tavily_fetch + tavily_available (D-172-01)."""
        import inspect
        from tests.integration._ai_research_tier2_helper import tier2_web as _fn
        params = inspect.signature(_fn).parameters
        for name in ("tavily_search", "tavily_fetch", "tavily_available"):
            assert name in params, f"tier2_web missing required Tavily param {name!r}"
    ```
    Then thread `tavily_search`, `tavily_fetch`, `tavily_available: bool = False`
    through the `_call_tier2` wrapper (lines 108-131) to `tier2_web(...)`, Tavily
    callables defaulting to no-op recorders so existing Exa/built-in tests pass.
    Keep `exa_available` semantics intact (judgment edit on the wrapper).
  - Gate: `pytest tests/integration/test_ai_research_tier2.py::test_tier2_web_accepts_tavily_provider_params` (RED until T-5)

- [x] T-2 — RED: 3-provider cascade selection (Tavily primary → Exa → built-in)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier2.py:134-330
  - Principles applied: §10.5 TDD, §10.2 YAGNI (capability flags, not a registry), §10.3 SOLID
  - Patch: OMITTED — judgment edit. Add cases (reuse existing `_RecordingSearch`/`_RecordingFetch`/`_RaisingSearch`; Tavily recorders default to no-op via T-1 wrapper):
    - `test_tavily_used_as_primary_when_available`: tavily+exa available → `tavily_search` once; `exa_search.calls == []`; `web_search.calls == []`; `"tavily"` NOT in degraded; hits are Tavily's.
    - `test_tavily_fetch_used_for_explicit_url`: explicit URL + tavily available → `tavily_fetch.calls == ["https://example.org/article"]`; Exa/built-in fetch not called.
    - `test_falls_to_exa_when_tavily_unavailable`: tavily=False, exa=True → `exa_search` once; `tavily_search.calls == []`; `"tavily"` in degraded; `"exa"` NOT in degraded.
    - `test_falls_to_builtin_when_tavily_and_exa_unavailable`: both False → `web_search` once; `"tavily"` and `"exa"` in degraded.
    - `test_tavily_available_does_not_record_degraded`: tavily success → `degraded_sources == []`.
    Domain-filter pass-through (`allowed_domains`/`blocked_domains`) asserts on the *selected* provider (Tavily when primary).
  - Gate: `pytest tests/integration/test_ai_research_tier2.py -k "tavily_used or falls_to or does_not_record"` (RED until T-5)

- [x] T-3 — RED: ONE bounded fall-through on raise-OR-empty, record degraded (D-172-02)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier2.py:276-330
  - Principles applied: §10.5 TDD, §10.3 SOLID (single decision point), §10.7 Clean Code
  - Patch: OMITTED — judgment edit (the behavior that supersedes tier2-web.md:106). Add a `_RecordingSearch([])` empty variant + cases:
    - `test_tavily_raise_falls_through_to_exa_once`: tavily raises, tavily+exa available → `exa_search` exactly once; `web_search.calls == []` (no second fall-through); tavily search tool name in degraded; hits are Exa's.
    - `test_tavily_empty_falls_through_to_exa_once`: tavily returns 0 results → `exa_search` once; tavily marker in degraded; hits are Exa's.
    - `test_exa_empty_falls_through_to_builtin_once_when_tavily_absent`: tavily=False, exa empty → `web_search` once; degraded has tavily(absent)+exa markers; hits are built-in's.
    - `test_second_provider_empty_does_NOT_fall_through_again`: tavily empty → exa empty → built-in available → `web_search.calls == []`; `result.hits == []`; both markers recorded. Pins "bounded = one".
    - `test_fall_through_preserves_explicit_url_fetch`: tavily search raises but its fetch returned the explicit-URL hit → that hit preserved AND Exa search ran once.
  - Gate: `pytest tests/integration/test_ai_research_tier2.py -k "falls_through or second_provider or preserves_explicit"` (RED until T-5)

- [x] T-4 — RED: existing tier-2 tests keep passing under the cascade default
  - Agent: build
  - Files: tests/integration/test_ai_research_tier2.py:139-549
  - Principles applied: §10.5 TDD, §10.4 DRY (single `_call_tier2` wrapper)
  - Patch: OMITTED — judgment edit. With `_call_tier2` defaulting `tavily_available=False` + no-op Tavily recorders, existing tests need no per-call edits EXCEPT degraded-equality assertions:
    - `test_exa_available_does_not_record_degraded` (:256) asserts `degraded_sources == []` with exa available; under cascade default this records `"tavily"`. Flip to `tavily_available=True` so the empty-list invariant still means "primary succeeded".
    - membership assertions (`"exa" in degraded_sources`, e.g. :198) stay green.
    - `test_tier2_skipped_*` (:406) runs before selection → `degraded_sources == []` regardless; leave as-is.
  - Gate: `pytest tests/integration/test_ai_research_tier2.py` (pre-existing green after T-5)

## Phase 2 — WS-A Tavily: GREEN implementation (§10.5, §10.6)

- [x] T-5 — GREEN: Tavily→Exa→built-in cascade + single bounded fall-through in helper
  - Agent: build
  - Files: tests/integration/_ai_research_tier2_helper.py:14-19, :53-56, :68-83, :102-160
  - Principles applied: §10.3 SOLID (one selection decision, DIP), §10.2 YAGNI (3 flags, no registry), §10.7 Clean Code, §10.4 DRY
  - Patch: OMITTED — judgment edit (control-flow rewrite). Implement exactly:
    1. Add constants after :56 — `_TAVILY_SEARCH_TOOL = "mcp__tavily__tavily_search"`, `_TAVILY_FETCH_TOOL = "mcp__tavily__tavily_extract"` (single-URL fetch = `tavily_extract`, wraps a one-element URL array; the callable hides that shape).
    2. Extend `tier2_web` keyword-only signature: add `tavily_search`, `tavily_fetch`, `tavily_available: bool` BEFORE the Exa params; keep `allowed_domains`/`blocked_domains` last.
    3. Replace the two-branch `if exa_available` (:111-122) with an ordered cascade: build `(available, search_fn, fetch_fn, search_tool, fetch_tool, absent_marker)` candidates in order Tavily, Exa, built-in (built-in always available). First `available` candidate = primary; each skipped higher-priority candidate appends its marker (`"tavily"`, then `"exa"`) to `degraded` (capability degrade, NOT the fall-through). Built-in has no marker.
    4. Run primary search (and fetch on explicit URL) on the existing ThreadPoolExecutor. After: `search_failed = raised OR returned 0 hits`. On failure → record the primary search tool/marker in `degraded` and do the SINGLE bounded fall-through (next available candidate after primary, run its search once, merge hits). NO loop — exactly one, even if the fall-through also returns empty.
    5. Preserve surviving explicit-URL fetch hits from the primary across the fall-through (merge, don't discard).
    6. Update module docstring (:14-19) + callable-type notes for the 3-provider cascade + bounded fall-through.
  - Gate: `pytest tests/integration/test_ai_research_tier2.py` (ALL green — T-1..T-4 pass)

- [x] T-6 — GREEN: mirror cascade + fall-through prose into tier2-web.md, supersede :106
  - Agent: build
  - Files: .claude/skills/ai-research/handlers/tier2-web.md:9-16, :28-30, :54-64, :88-95, :104-122
  - Principles applied: §10.6 SDD, §10.4 DRY (lockstep with helper), §10.7 Clean Code
  - Patch: OMITTED — judgment prose, match the GREEN helper:
    - Heading → `## Web Provider: Tavily Primary, Exa Secondary, Built-in Fallback`. Body: 3-tier capability cascade — PRIMARY Tavily (`mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`), SECONDARY Exa, FALLBACK built-in; each absent higher-priority provider recorded in `degraded_sources` (`"tavily"`, then `"exa"`), never raises (D-172-01).
    - Inputs (:28-30): add `tavily_search`, `tavily_fetch`, `tavily_available`.
    - Step-3 selection (:54-64): replace with ordered-cascade pseudo-code (first-available wins; skipped markers appended).
    - Resilience §, supersede :106 — replace "The failure of one provider's call never falls through…" with: "**One bounded fall-through (D-172-02, supersedes the former no-fall-through rule).** If the selected provider's search RAISES or returns ZERO results, record it in `degraded_sources` and fall through to the NEXT available provider EXACTLY ONCE. A second empty/raising result does NOT trigger a further fall-through. Surviving explicit-URL fetch hits from the primary are preserved across the fall-through."
    - Sources Invoked: add 2 Tavily rows as PRIMARY, demote Exa to SECONDARY.
    - Implementation Reference signature: add the new params ordered before Exa.
    - Status §: note Tavily primary wiring (spec-172, D-172-01..04).
  - Gate: `python -c "t=open('.claude/skills/ai-research/handlers/tier2-web.md').read(); assert 'mcp__tavily__tavily_search' in t and 'mcp__tavily__tavily_extract' in t and 'bounded fall-through' in t.lower() and 'selection is decided once' not in t"` then `pytest tests/unit -k surface_parity`

- [x] T-7 — GREEN: SKILL.md:41 Tier-2 summary (Tavily primary)
  - Agent: build
  - Files: .claude/skills/ai-research/SKILL.md:41
  - Principles applied: §10.6 SDD, §10.4 DRY
  - Patch (deterministic):
    ```diff
    @@ -41,1 +41,1 @@
    -5. **Tier 2 -- web (Exa, built-in fallback)** -- follow `handlers/tier2-web.md`. Invoke web search + fetch in parallel when Tier 1 produced fewer than 5 high-quality hits, or the query references an explicit URL. Search uses Exa (`mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`) when available, falling back to the built-in `WebSearch` / `WebFetch` (recording `"exa"` in `degraded_sources`) when not. Honor `--allowed-domains` and `--blocked-domains`.
    +5. **Tier 2 -- web (Tavily primary, Exa secondary, built-in fallback)** -- follow `handlers/tier2-web.md`. Invoke web search + fetch in parallel when Tier 1 produced fewer than 5 high-quality hits, or the query references an explicit URL. Search uses Tavily (`mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`) when available, then Exa (`mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`), then the built-in `WebSearch` / `WebFetch`; each absent higher-priority provider is recorded in `degraded_sources` (`"tavily"`, `"exa"`). If the selected provider raises or returns zero results, fall through to the next available provider exactly once (D-172-02). Honor `--allowed-domains` and `--blocked-domains`.
    ```
  - Gate: `grep -q "mcp__tavily__tavily_search" .claude/skills/ai-research/SKILL.md && grep -q "exactly once (D-172-02)" .claude/skills/ai-research/SKILL.md` then `pytest tests/unit -k "surface_parity or mirror"`

- [x] T-8 — GREEN: register tavily MCP under canonical name + operator setup docs (D-172-03)
  - Agent: build
  - Files: .mcp.json (new, repo root), .claude/skills/ai-research/handlers/tier2-web.md (new "## Operator Setup -- Tavily MCP")
  - Principles applied: §10.6 SDD, §10.4 DRY, §10.3 SOLID
  - Patch: OMITTED for prose; `.mcp.json` is mechanical. Repo has NO `.mcp.json` today. Canonical server name `tavily`, HTTP, key from env (§13 — NEVER inline, NEVER `?tavilyApiKey=`). Create `.mcp.json`:
    ```json
    {
      "mcpServers": {
        "tavily": {
          "type": "http",
          "url": "https://mcp.tavily.com/mcp/",
          "headers": { "Authorization": "Bearer ${TAVILY_API_KEY}" }
        }
      }
    }
    ```
    Yields tool names `mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`. Add a handler "## Operator Setup -- Tavily MCP" section: (1) CLI equivalent `claude mcp add --transport http tavily https://mcp.tavily.com/mcp/ --header "Authorization: Bearer $TAVILY_API_KEY"`; (2) `TAVILY_API_KEY` exported in the operator shell, resolved from env, never committed; (3) verify `claude mcp list` + tools resolve as `mcp__tavily__tavily_search`/`_extract`; (4) absent/unregistered Tavily is fail-soft — cascade falls to Exa then built-in. NOTE: no installer-template `.mcp.json` is shipped (cannot commit a key; D-172-04 scopes registration to the operator).
  - Gate: `python -c "import json; m=json.load(open('.mcp.json')); s=m['mcpServers']['tavily']; assert s['url']=='https://mcp.tavily.com/mcp/' and 'tavilyApiKey' not in json.dumps(m)"` and `gitleaks protect --staged` and `grep -q "Operator Setup -- Tavily MCP" .claude/skills/ai-research/handlers/tier2-web.md`

## Phase 3 — WS-B NotebookLM: RED tests (§10.5)

- [x] T-9 — RED: poll-by-status replaces phantom job_status; status field is the signal (D-172-05)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:319-369, tests/integration/test_ai_research_tier3.py:124-143
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k harvest -x` (RED until T-17)
  - Prose: Drop the phantom `job_status(notebook_id)` callable; `tier3_harvest` polls status via injected `poll_status(notebook_id)` returning `{"status": "in_progress"|"completed"|"failed"|..., "report"/"report_markdown": ..., "sources": [...]}`. Rename `_ScriptedJobStatus`→`_ScriptedPollStatus`; drive `test_harvest_success_populates_report_and_sources` `in_progress→in_progress→completed`. Regression case: an early `in_progress` payload with a non-empty `sources` list does NOT terminate until `status=="completed"` (sources stream mid-run; count is a weak secondary heuristic only).

- [x] T-10 — RED: status case-insensitive + attribute/dict alias tolerance (D-172-05, D-172-08)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:372-399
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k "alias or status_case" -x` (RED until T-17)
  - Prose: Extend `test_harvest_reads_report_alias_field` + add `test_harvest_status_is_case_insensitive`: normalize status literals case-insensitively (`"COMPLETED"`, `"Completed"` both terminate); tolerate report under `report`/`report_markdown`/`summary` and via attribute OR `.get` (prefer attribute/`.get`, subscript deprecated); sources read tuple-or-list with the same tolerance.

- [x] T-11 — RED: terminal failed/error status stops and degrades, no infinite poll (D-172-08)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:433-475
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k "failed or terminal" -x` (RED until T-17)
  - Prose: `test_harvest_failed_status_stops_and_degrades`: `poll_status` returns `{"status":"failed"}` (+ `"error"` variant) → returns `Tier3Result(degraded=True, timed_out=False, report_markdown="", notebook_id=<preserved>)` with a failure warning; assert `poll_status.calls == 1` (terminal short-circuits without burning budget). `timed_out` stays False (terminal, not wall-clock).

- [x] T-12 — RED: [AUTH_REQUIRED] mid-poll escalates, not "still running" (D-172-06, D-172-08)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:433-475
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k auth_required -x` (RED until T-17)
  - Prose: `test_harvest_auth_required_escalates_not_keep_polling`: `poll_status` returns/raises an `[AUTH_REQUIRED]` signal on poll 1 → harvest stops immediately (`poll_status.calls == 1`), `degraded=True`, `timed_out=False`, warning contains the CORRECT login command `uvx --from notebooklm-skill notebooklm login`. Pin the string in lockstep with T-19.

- [x] T-13 — RED: bounded back-off poll cadence (capped, no tight while-True) (D-172-08)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:433-475, tests/integration/test_ai_research_tier3.py:106-122
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k backoff -x` (RED until T-17)
  - Prose: `test_harvest_polls_with_capped_backoff`: inject a recording `sleep(seconds)` + `clock`; `poll_status` stays `in_progress` several iterations then `completed`. Assert `sleep` is called between polls with a non-decreasing, capped interval (cap honoured; fixed 5s OR capped exponential accepted) — loop never spins without sleeping. Kills `while True` no-sleep at helper:259-273. Budget check uses the injected clock.

- [x] T-14 — RED: bounded retry + try/except around nlm_create_notebook & nlm_research at launch (D-172-08)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:161-311
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k "retry or transient" -x` (RED until T-18)
  - Prose: `test_launch_retries_transient_create_then_succeeds` (create raises once then returns id → retries ≤2, succeeds, no degrade) and `test_launch_degrades_after_retry_budget_exhausted` (research always raises → exhausts bounded retry → `degraded=True, notebook_id=<created-or-"">` + warning, NEVER propagates the exception, fail-soft D-172-09). Extend `_RecordingCreateNotebook`/`_RecordingResearch` with a `raises_n` counter.

- [x] T-15 — RED: subagent MCP-availability pre-check before launch (D-172-11)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:161-211
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k "precheck or subagent_unavailable" -x` (RED until T-23)
  - Prose: `test_launch_subagent_mcp_unavailable_degrades_at_launch`: the `nlm_list` probe is the in-subagent availability gate — when it reports unavailable/raises, launch degrades with the correct login warning and ZERO `nlm_create_notebook`/`nlm_research` calls. Frames the existing probe as a first-class, named D-172-11 contract (no new code path if the probe already covers it).

- [x] T-16 — RED: degraded Tier-3 does NOT abort synthesis / no blocking banner (D-172-09)
  - Agent: build
  - Files: tests/integration/test_ai_research_resilience.py (new case), tests/integration/test_ai_research_tier3.py:433-475
  - Principles applied: §10.5 TDD, §10.6 SDD
  - Patch: none — judgment edit
  - Gate: `pytest tests/integration/test_ai_research_resilience.py -k "fail_soft or no_banner or degraded_continues" -x` (RED until T-17/T-18)
  - Prose: First-class fail-soft contract (closes critic gap #3). Add `test_degraded_tier3_does_not_block_synthesis`: for each degrade terminal (timeout, failed, [AUTH_REQUIRED], launch-exhausted) assert the harvest/launch returns a `Tier3Result`/dict with `degraded=True` and the run is expected to proceed on Tiers 0-2 — i.e. neither `tier3_launch` nor `tier3_harvest` raises, calls `sys.exit`, or returns any "blocking" sentinel. Assert the degrade is a *warning*, not a hard stop (D-172-09).

## Phase 4 — WS-B NotebookLM: GREEN implementation (§10.5, §10.6)

- [x] T-17 — GREEN: rewrite tier3_harvest — status-poll loop, alias tolerance, terminal branches, capped back-off (D-172-05, D-172-08, D-172-09)
  - Agent: build
  - Files: tests/integration/_ai_research_tier3_helper.py:130-131, :208-290, :211-217
  - Principles applied: §10.6 SDD, §10.7 Clean Code, §10.1 KISS
  - Patch: none — judgment edit (makes T-9..T-13, T-16 green)
  - Prose: Replace `job_status` param with `poll_status: Callable[[str], dict]`; add injected `sleep: Callable[[float], None]` (default `time.sleep`). Loop: `start = clock()`; call `poll_status(notebook_id)`; `_read_status(payload)` prefers attribute then `.get("status")`, normalizes `str(...).strip().lower()` vs the status literals; branch — `completed` → break, read report+sources via alias-tolerant `_read_report`/`_read_sources`; `failed`/`error` → `degraded=True, timed_out=False` + failure warning (stop); `[AUTH_REQUIRED]` (sentinel or caught) → `degraded=True` + CORRECT login warning (stop); `in_progress`/`not_found`/`no_research` → keep polling; `clock()-start > wait_budget_sec` → existing timeout branch (`timed_out=True`, preserve `notebook_id`, reuse-notebook warning); else `sleep(min(next_backoff, cap))`. Generalize `_read_report` to accept `summary`; add `_read_sources` (tuple|list). Preserve public signatures except `job_status`→`poll_status`. NOTE: there is NO `mcp__notebooklm__job_status` tool — completion is detected by re-polling status (resolved OQ).
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -x`

- [x] T-18 — GREEN: harden tier3_launch — try/except + bounded retry, stay fail-soft (D-172-08, D-172-09)
  - Agent: build
  - Files: tests/integration/_ai_research_tier3_helper.py:158-205
  - Principles applied: §10.6 SDD, §10.7 Clean Code, §10.1 KISS
  - Patch: none — judgment edit (makes T-14 green)
  - Prose: Wrap steps 2-3 (`nlm_create_notebook`, `nlm_research`) in `_with_retry(fn, attempts=2)` — catch, retry once, on exhaustion return a degraded launch dict (`degraded=True`, `notebook_id`=created id or `""`, warning naming the failed step) instead of raising. Keep `nlm_list` probe as-is (already fail-soft via `is_available`). Preserve unavailable/reuse paths byte-for-byte. KISS — no exponential back-off on launch (one transient retry; back-off belongs in harvest).
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k "retry or transient or launch" -x`

- [x] T-19 — GREEN: helper _UNAVAILABLE_WARNING + harvest warnings → correct login command (D-172-06, site 1/6)
  - Agent: build
  - Files: tests/integration/_ai_research_tier3_helper.py:137-143
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    @@ -137,7 +137,7 @@
     # Operator recovery path for an absent / unauthenticated NotebookLM. References
     # the ``claude-world/notebooklm-skill`` auth model (NOT the legacy ``nlm login``).
     _UNAVAILABLE_WARNING = (
    -    "notebooklm unavailable or unauthenticated -- run `uvx notebooklm login` "
    +    "notebooklm unavailable or unauthenticated -- run `uvx --from notebooklm-skill notebooklm login` "
         "(auth state at `~/.notebooklm/storage_state.json`); Tier 3 skipped, "
         "synthesizing from Tiers 0-2 only"
     )
    ```
  - Gate: `pytest tests/integration/test_ai_research_resilience.py tests/integration/test_ai_research_tier3.py -k login -x`

- [x] T-20 — GREEN: login-command lockstep in test_ai_research_tier3.py (D-172-06, D-172-10; sites 2-3/6)
  - Agent: build
  - Files: tests/integration/test_ai_research_tier3.py:282, tests/integration/test_ai_research_tier3.py:487
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch (deterministic):
    ```diff
    @@ -282,1 +282,1 @@
    -    assert "uvx notebooklm login" in joined, (
    +    assert "uvx --from notebooklm-skill notebooklm login" in joined, (
    @@ -487,1 +487,1 @@
    -        "warnings": ["notebooklm unavailable -- run `uvx notebooklm login`"],
    +        "warnings": ["notebooklm unavailable -- run `uvx --from notebooklm-skill notebooklm login`"],
    ```
  - Gate: `pytest tests/integration/test_ai_research_tier3.py -k "login or skips_when_launch_degraded or warning" -x`

- [x] T-21 — GREEN: login-command lockstep in test_ai_research_resilience.py (D-172-06, D-172-10; sites 4-6/6)
  - Agent: build
  - Files: tests/integration/test_ai_research_resilience.py:12, tests/integration/test_ai_research_resilience.py:170, tests/integration/test_ai_research_resilience.py:202-203
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch (deterministic):
    ```diff
    @@ -12,1 +12,1 @@
    -    with a warning suggesting ``uvx notebooklm login`` and no other
    +    with a warning suggesting ``uvx --from notebooklm-skill notebooklm login`` and no other
    @@ -170,1 +170,1 @@
    -      * A warning suggests ``uvx notebooklm login`` so the user can recover.
    +      * A warning suggests ``uvx --from notebooklm-skill notebooklm login`` so the user can recover.
    @@ -202,2 +202,2 @@
    -    assert any("uvx notebooklm login" in w for w in launch["warnings"]), (
    -        f"Warnings must suggest 'uvx notebooklm login' for recovery; got {launch['warnings']}"
    +    assert any("uvx --from notebooklm-skill notebooklm login" in w for w in launch["warnings"]), (
    +        f"Warnings must suggest 'uvx --from notebooklm-skill notebooklm login' for recovery; got {launch['warnings']}"
    ```
  - Gate: `pytest tests/integration/test_ai_research_resilience.py -x`

- [x] T-22 — GREEN: handler mechanism rewrite + login fix + SKILL.md:38/42 (D-172-05, D-172-06, critic gap #4)
  - Agent: build
  - Files: .claude/skills/ai-research/handlers/tier3-notebooklm.md:29-33, :78, :84-117, :123, .claude/skills/ai-research/SKILL.md:38, .claude/skills/ai-research/SKILL.md:42
  - Principles applied: §10.6 SDD, §10.7 Clean Code, §10.4 DRY (lockstep helper↔handler, AC7)
  - Patch (deterministic): handler login swaps are mechanical:
    ```diff
    @@ -78,1 +78,1 @@
    -   operator recovery path -- `uvx notebooklm login` and
    +   operator recovery path -- `uvx --from notebooklm-skill notebooklm login` and
    @@ -123,1 +123,1 @@
    -`degraded=True` and surfaces a warning suggesting `uvx notebooklm login` (auth
    +`degraded=True` and surfaces a warning suggesting `uvx --from notebooklm-skill notebooklm login` (auth
    ```
  - Prose (judgment, SDD rewrite, lockstep with T-17): §Inputs (:29-33) drop `job_status` → add `poll_status` + `sleep`; §Launch step 3 (:84-89) replace "assumed BLOCKING" with the resolved fact — `nlm_research(mode="deep")` is NON-blocking (returns `status="in_progress"` ack; capture `task_id` to pin polls); §Harvest (:95-117) replace `job_status` with the status-poll loop until terminal status, alias-tolerant report/sources read, distinct `[AUTH_REQUIRED]` vs `failed`/`error` terminals, capped back-off, bound by `AIENG_RESEARCH_NLM_WAIT_SEC`; note source/artifact count is a weak secondary heuristic; document timeout-then-degrade as the common outcome and `--reuse-notebook` as primary recovery. ALSO fix SKILL.md:38 (launch wording) and SKILL.md:42 (replace "wait on the deep-research job" → "poll the deep-research job status until a terminal state, bounded by AIENG_RESEARCH_NLM_WAIT_SEC; on timeout/failure degrade and preserve notebook_id for --reuse-notebook"). Edit ONLY canonical `.claude/...`; `ai-eng dev sync` regenerates `.codex/.agents/.github` + template twins.
  - Gate: `ai-eng dev sync` then `pytest tests/unit/docs tests/unit/config -k "surface or mirror or parity" -x` and `! grep -rn "wait on the deep-research job\|assumed BLOCKING\|job_status" .claude/skills/ai-research/`

- [x] T-23 — GREEN: document the subagent MCP-availability pre-check in handler + SKILL.md (D-172-11, D-172-09)
  - Agent: build
  - Files: .claude/skills/ai-research/handlers/tier3-notebooklm.md:67-79, .claude/skills/ai-research/SKILL.md
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Patch: none — judgment edit (makes T-15 green)
  - Prose: §Launch (:67-79) state the `nlm_list` probe runs INSIDE the background subagent as the D-172-11 availability gate — before any create/research — and on unavailable/raise the subagent degrades at T0 (no blocking banner, fail-soft D-172-09); the main agent proceeds on Tiers 0-2. Mirror the one-line gate note into the SKILL.md Tier-3 dispatch section. Canonical edit only; `ai-eng dev sync` propagates.
  - Gate: `ai-eng dev sync` then `pytest tests/integration/test_ai_research_tier3.py -k precheck -x` and `pytest tests/unit/docs -k "surface or mirror" -x`

- [x] T-24 — GREEN: harvest poll-interval tunable + template mirror + CANONICAL doc (D-172-08)
  - Agent: build
  - Files: .ai-engineering/scripts/hooks/_lib/runtime_state.py:123-127, src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/runtime_state.py, CANONICAL source for the Runtime Layer Tunables block
  - Principles applied: §10.2 YAGNI, §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): add adjacent to `RESEARCH_NLM_WAIT_SEC`:
    ```diff
    @@ -127,0 +128,5 @@
     RESEARCH_NLM_WAIT_SEC = _env_int("AIENG_RESEARCH_NLM_WAIT_SEC", 300, ceiling=900)
    +
    +# spec-172 D-172-08: harvest poll cadence. Initial/fixed back-off interval
    +# (seconds) between research status polls; capped so a 900s budget cannot
    +# spin. 5s default matches the SDK wait_for_completion interval; 60s ceiling.
    +RESEARCH_NLM_POLL_INTERVAL_SEC = _env_int("AIENG_RESEARCH_NLM_POLL_INTERVAL_SEC", 5, ceiling=60)
    ```
  - Prose: Copy the edit BYTE-IDENTICALLY into the template-mirror `runtime_state.py` (NO CI guards this parity — verify by hand, per scripts-template-mirror-parity). Add the `AIENG_RESEARCH_NLM_POLL_INTERVAL_SEC` row to the Runtime Layer Tunables block in the CANONICAL source (NOT root/template CLAUDE.md directly — those are generated; run `ai-eng dev sync`). T-17 reads this as the back-off base.
  - Gate: `pytest tests/unit/hooks -k "runtime_state or tunable" -x` and `diff .ai-engineering/scripts/hooks/_lib/runtime_state.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/runtime_state.py`

## Phase 5 — Shared permissions allowlist (single-owner reconciliation, D-172-04, D-172-07, D-172-10)

- [x] T-25 — GREEN: local allowlist — explicit nlm_* names + tavily glob (sole owner of the file)
  - Agent: build
  - Files: .claude/settings.local.json:3-5
  - Principles applied: §10.4 DRY (one allowlist datum), §10.2 YAGNI, §10.7 Clean Code
  - Patch (deterministic): final content —
    ```json
    {
      "permissions": {
        "allow": [
          "mcp__notebooklm__nlm_list",
          "mcp__notebooklm__nlm_create_notebook",
          "mcp__notebooklm__nlm_research",
          "mcp__notebooklm__nlm_ask",
          "mcp__notebooklm__nlm_list_sources",
          "mcp__notebooklm__nlm_list_artifacts",
          "mcp__tavily__*"
        ]
      }
    }
    ```
  - Gate: `python -c "import json; a=json.load(open('.claude/settings.local.json'))['permissions']['allow']; assert 'mcp__tavily__*' in a and 'mcp__notebooklm__nlm_research' in a and 'mcp__notebooklm__nlm_list_artifacts' in a"`

- [x] T-26 — GREEN: template allowlist — drop wrong prefix, explicit nlm_* names + tavily glob (sole owner of line 16)
  - Agent: build
  - Files: src/ai_engineering/templates/project/.claude/settings.json:15-16
  - Principles applied: §10.4 DRY (template mirrors live allowlist FORM), §10.2 YAGNI, §10.10 lockstep (D-172-10)
  - Patch (deterministic):
    ```diff
    @@ -14,3 +14,9 @@
           "TaskUpdate",
           "mcp__context7__*",
    -      "mcp__notebooklm-mcp__*"
    +      "mcp__notebooklm__nlm_list",
    +      "mcp__notebooklm__nlm_create_notebook",
    +      "mcp__notebooklm__nlm_research",
    +      "mcp__notebooklm__nlm_ask",
    +      "mcp__notebooklm__nlm_list_sources",
    +      "mcp__notebooklm__nlm_list_artifacts",
    +      "mcp__tavily__*"
         ],
    ```
  - Gate: `python -c "import json; a=json.load(open('src/ai_engineering/templates/project/.claude/settings.json'))['permissions']['allow']; assert 'mcp__tavily__*' in a and 'mcp__notebooklm__nlm_research' in a and 'mcp__notebooklm-mcp__*' not in a"` and `pytest tests/unit/config -k "settings or template or permission" -x`

## Phase 6 — Verify (lockstep + full suite, §10.4, §10.5)

- [x] T-27 — VERIFY: Workstream A lockstep + parity gate (D-172-10)
  - Agent: verify
  - Files: tests/integration/test_ai_research_tier2.py, tests/integration/_ai_research_tier2_helper.py, .claude/skills/ai-research/handlers/tier2-web.md, .claude/skills/ai-research/SKILL.md, .claude/settings.local.json, src/ai_engineering/templates/project/.claude/settings.json, .mcp.json
  - Principles applied: §10.5 TDD (green gate), §10.4 DRY (lockstep), §10.6 SDD
  - Patch: N/A
  - Gate: `pytest tests/integration/test_ai_research_tier2.py -q` AND `pytest tests/unit -k "surface_parity or mirror or settings" -q` AND `python -c "t=open('.claude/skills/ai-research/handlers/tier2-web.md').read(); h=open('.claude/skills/ai-research/SKILL.md').read(); s=open('tests/integration/_ai_research_tier2_helper.py').read(); assert all('mcp__tavily__tavily_search' in x for x in (t,h,s))"` AND `gitleaks protect --staged`

- [x] T-28 — VERIFY: Workstream B lockstep + parity gate (D-172-10)
  - Agent: verify
  - Files: tests/integration/test_ai_research_tier3.py, tests/integration/test_ai_research_resilience.py, tests/integration/_ai_research_tier3_helper.py, .claude/skills/ai-research/handlers/tier3-notebooklm.md, .claude/settings.local.json, src/ai_engineering/templates/project/.claude/settings.json, .ai-engineering/scripts/hooks/_lib/runtime_state.py
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch: N/A
  - Gate: `ai-eng dev sync && pytest tests/integration/test_ai_research_tier3.py tests/integration/test_ai_research_resilience.py tests/unit/config tests/unit/docs -x` then confirm zero legacy strings: `! grep -rn "uvx notebooklm login\b\|mcp__notebooklm-mcp__\|job_status" --include="*.py" --include="*.md" --include="*.json" . | grep -v node_modules | grep -v "/archive/" | grep -v "/drafts/"`

- [x] T-29 — VERIFY: terminal full-changeset gate + fail-soft confirmation (D-172-09, D-172-10)
  - Agent: verify
  - Files: (whole changeset)
  - Principles applied: §10.5 TDD, §10.7 Clean Code, §10.6 SDD
  - Patch: N/A
  - Gate: `ai-eng dev sync` (zero residual diff) AND `pytest tests/integration -k ai_research -q && pytest tests/unit/config tests/unit/docs tests/unit/hooks -q` AND `gitleaks protect --staged` AND fail-soft confirmation: `! grep -nE "raise |sys\\.exit" tests/integration/_ai_research_tier3_helper.py | grep -viE "is_available|probe|_with_retry|re-raise|raises"` (the only executable raise is `_with_retry`'s internal re-raise, fully caught by `tier3_launch`; no hard-stop on launch/harvest happy or degrade paths, D-172-09) AND scripts template-mirror parity `diff .ai-engineering/scripts/hooks/_lib/runtime_state.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/runtime_state.py`

## Dependencies & ordering

- Phase 1 (T-1..T-4) → Phase 2 (T-5 makes them green; T-6/T-7/T-8 are GREEN docs/config).
- Phase 3 (T-9..T-16) → Phase 4: T-17 greens T-9..T-13+T-16; T-18 greens T-14; T-23 greens T-15.
- T-24 (tunable) precedes T-17's back-off use (T-17 reads `RESEARCH_NLM_POLL_INTERVAL_SEC`).
- Phase 5 (T-25, T-26) independent of test phases — sole owners of the settings files; run before T-27/T-28 parity checks.
- Phase 6 last. WS-A and WS-B are mutually independent and can run as parallel waves under /ai-autopilot.

## Out of scope / follow-ups

- No installer-template `.mcp.json` (secrets posture; operator registers Tavily).
- spec-150 lifecycle stays `draft` (separate hygiene; not closed here).
- Citation/synthesis contract unchanged.

## Quality Outcome

All 29 tasks complete. Single bounded quality-remediation pass consumed and closed.

**Deterministic verify** — full `tests/integration` + `tests/unit` = **7569 passed, 13 skipped**. `/ai-research` slice (tier2 30 + tier3 + resilience) green. config/docs/hooks/architecture green (620 passed). `dev sync --check` green; hooks-manifest re-pinned (runtime_state.py sha); runtime_state twin parity identical; helper↔handler↔SKILL Tavily lockstep confirmed; fail-soft (D-172-09) confirmed; `.mcp.json` gitleaks-clean (`${TAVILY_API_KEY}`, no inline key). ruff clean on all 12 edited Python files.

**Quality review** — 3 findings, all remediated in the one bounded pass:
- HIGH F1: integration twin `tests/integration/test_settings_template_narrow.py` allowlist updated 13→19 entries (the unit twin was fixed but this one was orphaned). FIXED + verified.
- MEDIUM F2: plan T-29 fail-soft gate grep made `_with_retry`-tolerant. FIXED.
- LOW F3: harvest cadence upgraded from a constant `sleep(5)` to real capped exponential back-off (5→60s), making the cap live and the "back-off" wording accurate (D-172-08). FIXED + verified.

**Two pre-existing failures also fixed** (autonomous, §9):
- `test_canonical_structure` — the parked spec-171 left a non-canonical `specs/spec-171/` dir; relocated `design-intent.md` into `drafts/` (completed parking).
- `test_spec_lint::test_frontmatter_unknown_key_is_advisory` — date time-bomb (`summary` hard-required after 2026-06-16); added `summary` to the isolated fixture.

**Remaining (not remediated — environmental):** 16 CLI-JSON tests (`host_probe`/`plan_dag`/`spec_verify`/`release`) fail LOCALLY only, via stack-drift stdout pollution from the gitignored `./.opencode/node_modules` (`JSONDecodeError: Extra data`). Green in clean CI.

**Out-of-scope observation:** repo-root `.opencode/skills/ai-research/*` is a stale orphan surface — NOT a `dev sync` target (targets are `.codex/.agents/.github` + templates), unguarded by parity tests. Pre-existing; template `.opencode` (consumer-facing) IS synced. Candidate for a separate surface-hygiene cleanup.
