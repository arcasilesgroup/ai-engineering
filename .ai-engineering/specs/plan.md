---
execution_route:
  version: 1
  spec: spec-150
  executor: autopilot
  automation: assisted
  concern_count: 7
  estimated_files: 18
  reason: >
    Multi-concern refactor of /ai-research — Tier 3 backend swap + async
    redesign, Tier 2 Exa wiring, capability-detection fail-soft, +3-directions
    output contract, persist/classify changes, env tunable, SKILL.md + mirror
    regen. ~16 hand-edited files across handlers + 5 lockstep helpers + 6 test
    files + config, plus generated mirrors. Crosses ≥3 concerns and ≥10 files →
    autopilot wraps plan+build in waves.
  safe_next_command: "/ai-autopilot"
spec: spec-150
status: draft
pipeline: full
---

# Plan — Async-first NotebookLM autonomous deep research (Tier 3 redesign)

> Contract for execution. Operator approves before build. Spec:
> `.ai-engineering/specs/spec.md` (D1–D8, AC1–7).

## Architecture

- **Pattern**: `ad-hoc` — the existing **lockstep mirror** pattern. `/ai-research`
  is pure LLM-driven markdown; the only testable code is the Python lockstep
  helpers under `tests/integration/_ai_research_*`, which mirror each handler 1:1.
  Every handler edit MUST be matched in its helper and tests (AC7).
- **New element**: async launch via **background subagent** (`Agent`
  `run_in_background`) blocking on `nlm_research(mode=deep)` at T0; main runs Tiers
  0–2; bounded-wait harvest at the end (D1, D4). In the lockstep helper this is
  modeled with injected `clock` + `job_status` callables (deterministic tests).
- **Cross-helper dep (caution)**: `_ai_research_persist_helper.py:32` imports
  `topic_slug` from `_ai_research_tier3_helper`. The Tier 3 helper rewrite MUST keep
  `topic_slug`, `hash6`, `notebook_title` exported.

## Design

`--skip-design` rationale: no new UI surface. Output is CLI-skill markdown; the only
contract change is the appended `## Recommended Directions` section (D8), specified
in the spec. No design-intent doc required.

## Prerequisites (DONE — do not redo)

- Branch `notebooklm-async-tier3` created off `main`.
- spec.md promoted (spec-149 preserved at
  `.ai-engineering/specs/spec-149-obvious-by-default-essentials.md`).
- MCP config aligned (Claude user-scope + Codex `mcp_servers` → `uvx --from
  notebooklm-skill notebooklm-mcp`). **Do NOT re-touch MCP config.**
- Operator-only manual step (NOT a build task): `uvx notebooklm login`. Build +
  tests use injected mocks.

---

## Phase 1 — Tier 3 backend swap + async redesign (core)

Gate (phase): `pytest tests/integration/test_ai_research_tier3.py
tests/integration/test_ai_research_resilience.py -q` green.

- [ ] **T-1.1 — RED: rewrite Tier 3 tests for the new contract**
  - Agent: build
  - Files: `tests/integration/test_ai_research_tier3.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — judgment required (new tool surface + async).
  - Detail: replace `notebook_create/source_add/notebook_query/server_info` mocks
    with `nlm_create_notebook`, `nlm_research(mode=deep)`, `nlm_ask`, `nlm_list`
    (capability/auth probe). Add tests: default-launch (no flag) when available;
    background-launch ordering (launched before Tier 1); bounded-wait harvest
    success; harvest timeout → degrade + `notebook_id` persisted + `timed_out=True`;
    capability probe fail → degrade, no `nlm_*` calls. Keep `should_invoke_tier3`
    parametrized test updated to the default-on rule.
  - Gate: tests fail (RED) against current helper.

- [ ] **T-1.2 — GREEN: rewrite Tier 3 lockstep helper**
  - Agent: build
  - Files: `tests/integration/_ai_research_tier3_helper.py`
  - Principles applied: §10.5 TDD, §10.3 SOLID (inject `clock`/`job_status`)
  - Detail: extend `Tier3Result` with `report_markdown`, `sources_discovered:
    list[str]`, `timed_out: bool`. Replace callables with `nlm_create_notebook`,
    `nlm_research`, `nlm_ask`, `nlm_list`. New
    `should_launch_tier3(*, notebooklm_available)` → True whenever available (D3);
    drop legacy `should_invoke_tier3` (hard delete, no shim per Hard Rule 3) unless a
    test still needs it. Implement `tier3_launch()` (create notebook + start
    research) and `tier3_harvest(*, clock, job_status, wait_budget_sec)` (bounded
    poll → report or `timed_out`). KEEP `topic_slug`, `hash6`, `notebook_title`
    exported (persist dep). Capability/auth probe via `nlm_list` (replaces
    `server_info`).
  - Gate: T-1.1 tests pass (GREEN).

- [ ] **T-1.3 — GREEN: rewrite Tier 3 handler markdown (lockstep)**
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/tier3-notebooklm.md`
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Detail: document the new sequence verbatim to the helper — background launch at
    T0, `nlm_*` tool names, capability/auth probe via `nlm_list` (drop `server_info`
    / `nlm login` text → `uvx notebooklm login` + `~/.notebooklm/storage_state.json`),
    bounded-wait harvest, timeout→degrade+persist `notebook_id`, default-on trigger.
    Update the "Implementation Reference" + "Status" sections.
  - Gate: handler ↔ helper algorithm match (AC7); manual diff review.

---

## Phase 2 — Tier 2 Exa wiring

Gate (phase): `pytest tests/integration/test_ai_research_tier2.py -q` green.

- [ ] **T-2.1 — RED: Tier 2 Exa tests**
  - Agent: build
  - Files: `tests/integration/test_ai_research_tier2.py`
  - Principles applied: §10.5 TDD
  - Detail: add `web_search_exa` / `web_fetch_exa` mock callables; assert Exa used
    when available; assert fallback to built-in `WebSearch`/`WebFetch` when Exa
    absent (capability detection); preserve domain-filter pass-through + skip
    threshold tests.
  - Gate: RED.

- [ ] **T-2.2 — GREEN: Tier 2 lockstep helper adds Exa + fallback**
  - Agent: build
  - Files: `tests/integration/_ai_research_tier2_helper.py`
  - Principles applied: §10.5 TDD, §10.4 DRY (shared availability check w/ Phase 3)
  - Detail: add `web_search_exa`/`web_fetch_exa` callables; select Exa when
    available else built-in; record absent provider in `degraded_sources`; keep
    `detect_explicit_url` + skip heuristic.
  - Gate: T-2.1 GREEN.

- [ ] **T-2.3 — GREEN: Tier 2 handler markdown (Exa)**
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/tier2-web.md`
  - Principles applied: §10.6 SDD
  - Detail: document Exa as the primary web provider with built-in fallback; exact
    MCP names `mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`.
  - Gate: handler ↔ helper match.

---

## Phase 3 — Capability-detection fail-soft (D7, G5)

Gate (phase): `pytest tests/integration/test_ai_research_resilience.py -q` green.

- [ ] **T-3.1 — RED: absence (not just exception) tests**
  - Agent: build
  - Files: `tests/integration/test_ai_research_resilience.py`
  - Principles applied: §10.5 TDD
  - Detail: NotebookLM / Context7 / Exa **absent** (capability probe says
    unavailable) → tier skipped silently, recorded in `degraded_sources`, run exits 0
    with output (AC2, AC4). Distinct from transient-exception path.
  - Gate: RED.

- [ ] **T-3.2 — GREEN: shared capability detection in helpers**
  - Agent: build
  - Files: `tests/integration/_ai_research_tier1_helper.py`,
    `tests/integration/_ai_research_tier2_helper.py`,
    `tests/integration/_ai_research_tier3_helper.py`
  - Principles applied: §10.4 DRY, §10.2 YAGNI (minimal probe, no framework)
  - Detail: a small `is_available(probe)`-style guard reused by tiers; absent →
    skip + degrade, never raise. No generic async-job framework (Non-Goal).
  - Gate: T-3.1 GREEN; Phase 1/2 tests still green.

---

## Phase 4 — Output contract: +3 recommended directions (D8, G7)

Gate (phase): `pytest tests/unit/skills/ai_research/test_citation_validator.py -q` green.

- [ ] **T-4.1 — RED: 3-directions tests**
  - Agent: build
  - Files: `tests/unit/skills/ai_research/test_citation_validator.py`
  - Principles applied: §10.5 TDD
  - Detail: assert `SynthesizeResult.recommended_directions` has EXACTLY 3 entries,
    each carrying ≥1 `[N]` or `[unsourced]` (AC5); merged-sources dedup from
    NotebookLM + Tiers 0–2 (D2).
  - Gate: RED.

- [ ] **T-4.2 — GREEN: synthesize helper +directions +merge**
  - Agent: build
  - Files: `tests/integration/_ai_research_synthesize_helper.py`
  - Principles applied: §10.5 TDD
  - Detail: add `recommended_directions: list[Direction]` (title, rationale,
    trade-off, citations); validator enforces count==3 + citation per direction;
    merge+dedup NotebookLM `sources_discovered` with tier hits. Keep
    `CITATION_PATTERN` pinned.
  - Gate: T-4.1 GREEN.

- [ ] **T-4.3 — GREEN: synthesize handler markdown**
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/synthesize-with-citations.md`
  - Principles applied: §10.6 SDD
  - Detail: document the `## Recommended Directions` block (exactly 3) + source merge.
  - Gate: handler ↔ helper match.

---

## Phase 5 — Persist notebook_id + classify default-deep

Gate (phase): `pytest tests/unit/skills/ai_research/test_persist.py -q` green.

- [ ] **T-5.1 — Persist notebook_id + report for --reuse-notebook**
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/persist-artifact.md`,
    `tests/integration/_ai_research_persist_helper.py`,
    `tests/unit/skills/ai_research/test_persist.py`
  - Principles applied: §10.6 SDD, §10.5 TDD
  - Detail: persist `notebook_id` + (when present) deep `report_markdown` so a later
    `--reuse-notebook=<id>` harvests it (AC6). Preserve `topic_slug` import from tier3
    helper.
  - Gate: persist tests green.

- [ ] **T-5.2 — classify-query default-deep**
  - Agent: build
  - Files: `.claude/skills/ai-research/handlers/classify-query.md`,
    `tests/integration/_ai_research_tier1_helper.py` (`classify_tags`)
  - Principles applied: §10.6 SDD
  - Detail: NotebookLM deep research is default-on when available (D3); comparative
    tag no longer gates Tier 3 launch (kept only for routing metadata if used).
  - Gate: tier1 classify tests green.

---

## Phase 6 — Env tunable (harvest timeout)

- [ ] **T-6.1 — Add `AIENG_RESEARCH_NLM_WAIT_SEC`**
  - Agent: build
  - Files: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/runtime_state.py`
  - Principles applied: §10.4 DRY (reuse `_env_int`)
  - Patch (deterministic):
    ```python
    # after the existing _env_int constant block (~line 96)
    RESEARCH_NLM_WAIT_SEC = _env_int("AIENG_RESEARCH_NLM_WAIT_SEC", 300, ceiling=900)
    ```
  - Gate: import test; value-bounds test.

---

## Phase 7 — SKILL.md + mirror regen + docs

Gate (phase): `uv run ai-eng dev sync --check` clean; full
`pytest tests/integration/test_ai_research_*.py tests/unit/skills/ai_research -q` green.

- [ ] **T-7.1 — Rewrite SKILL.md**
  - Agent: build
  - Files: `.claude/skills/ai-research/SKILL.md`
  - Principles applied: §10.7 Clean Code, §10.6 SDD
  - Detail: update Process (Tier 3 launches first / harvested last; Exa in Tier 2;
    default-deep), CLI Flags (clarify `--reuse-notebook`; NotebookLM deep is default
    when available), Output Contract (+`## Recommended Directions`), Common Mistakes
    (drop `server_info` line; add capability-skip note), Examples.
  - Gate: section sanity; manual review.

- [ ] **T-7.2 — Regenerate mirrors**
  - Agent: build
  - Files: `.codex/skills/ai-research/**`, `.gemini/skills/ai-research/**`,
    `.github/skills/ai-research/**`, install templates under
    `src/ai_engineering/templates/project/`
  - Principles applied: §10.4 DRY (single source `.claude/`)
  - Patch (deterministic):
    ```bash
    uv run ai-eng dev sync && uv run ai-eng dev sync --check
    ```
  - Gate: `dev sync --check` exit 0.

- [ ] **T-7.3 — Document env var in canonical rulebook**
  - Agent: build
  - Files: `CLAUDE.md` (+ mirrors regenerated by T-7.2)
  - Principles applied: §10.7 Clean Code
  - Detail: add `AIENG_RESEARCH_NLM_WAIT_SEC` (default 300, ceiling 900) to the
    "Runtime Layer Tunables" list with a one-line description.
  - Gate: present in tunables section.

---

## Phase 8 — Final verification

- [ ] **T-8.1 — Full verify**
  - Agent: verify (read-only)
  - Files: n/a
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Detail: run full ai-research test suite + `ai-eng dev sync --check` +
    `ai-eng spec verify --sections`. Confirm AC1–AC7 evidence.
  - Gate: all green; no suppressions (Hard Rule 2).

- [ ] **T-8.2 — OQ2 verification (deferred / manual)**
  - Agent: verify
  - Files: n/a
  - Principles applied: §10.6 SDD
  - Detail: confirm whether MCP `nlm_research` blocks until done or returns a job
    handle. Requires `uvx notebooklm login` (operator). If unavailable, the build
    assumes **blocking** (D1) — background subagent holds the call. Record outcome;
    if it returns a handle, file a follow-up to simplify the wait model.
  - Gate: documented finding (non-blocking for this PR if auth absent).

---

## Risks carried from spec

R1 fragile browser-automation backend · R2 subagent must load `notebooklm` MCP ·
R3 notebook proliferation (default-on) · R4 async lockstep testability (injected
clock/job_status) · R5 Exa quota (fallback) · R6 own-branch isolation (done).

## Notes

- Hard Rule 3 (no shims): the Tier 3 tool-name swap is a hard rename — delete old
  callables, do not alias.
- TDD pairs: every GREEN helper task is preceded by its RED test task.
- `safe_next_command`: **/ai-autopilot** (multi-concern, ~18 files).
