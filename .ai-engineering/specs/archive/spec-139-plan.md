---
spec: spec-139
slug: framework-performance-hardening
title: Plan — Framework Performance Hardening
pipeline: build
phases: 9
status: approved
branch: claude/review-spec-drafts-DX2pD
date_approved: 2026-05-16
auto_approved: true
single_concern: false
---

# Plan — spec-139 Framework Performance Hardening

Nine milestones mapped 1-to-1 to the brief's M1–M9. Each milestone is independently shippable; the safety-critical subset (M1 + M4) closes the kernel-panic class on its own.

## Branch / PR

- Working branch: `claude/review-spec-drafts-DX2pD`
- Target: `main` via single PR carrying spec-138 + spec-139 + spec-140 + spec-141 (multi-spec autonomous run).

## Quality bar

- §10.5 TDD: every milestone ships RED tests first.
- §10.4 DRY: M3 manifest read happens once, not per agent; M8 `commit_compose.py` consumes plan-derived data.
- §10.2 YAGNI: no dynamic mid-wave re-throttle; no per-spec budgets; no telemetry surface that isn't load-bearing.
- §10.8 Hexagonal: M2 host probe is a port (`adapters/host/`); darwin/linux are adapters.

## Milestone M1 — Concurrency budget primitive

**Anchor:** §10.1 KISS · §10.2 YAGNI · §10.7 Clean Code · D-139-01.

### Tasks

- [x] **M1.T1** — Add `AIENG_MAX_WAVE_AGENTS` env var + manifest knob `performance.concurrency.max_wave_agents`. Loader in `src/ai_engineering/config/`.
- [x] **M1.T2** — Phase 2 (`phase-deep-plan.md`): wrap fan-out in deterministic batching loop — dispatch in batches of `cap`, await each batch.
- [x] **M1.T3** — Phase 4 (`phase-implement.md`): same batching for wave dispatch.
- [x] **M1.T4** — Phase 5 (`phase-quality.md`): cap = `min(3, AIENG_MAX_QUALITY_AGENTS)`; make explicit.
- [x] **M1.T5** — `src/ai_engineering/policy/orchestrator.py:489` and `:1209`: replace `max_workers = max(1, len(checkers))` with `min(len(checkers), max_thread_workers)`.
- [x] **M1.T6** — Update `.claude/agents/ai-autopilot.md:24` text to reflect cap.
- [x] **M1.T7** — `tests/architecture/test_concurrency_budgets.py` GREEN with 6 scenarios (env / manifest / default-auto / explicit-int / cap-of-1-serial / cap-larger-than-N).
- [x] **M1.T8** — `tests/unit/policy/test_orchestrator_max_workers.py` GREEN.

## Milestone M2 — Resource preflight probe

**Anchor:** §10.6 SDD · §10.8 Hexagonal · D-139-02 · D-139-09.

### Tasks

- [x] **M2.T1** — New module `src/ai_engineering/adapters/host/probe.py` with `HostProbe` dataclass + `probe()` function.
- [x] **M2.T2** — darwin adapter: `vm_stat`, `sysctl hw.memsize`, `sysctl hw.ncpu`, `sysctl vm.swapusage`.
- [x] **M2.T3** — linux adapter: `/proc/meminfo`, `/proc/cpuinfo`, `/proc/swaps`.
- [x] **M2.T4** — New CLI subcommand `ai-eng host probe` emits JSON.
- [x] **M2.T5** — New framework event `host_capacity` written to NDJSON (per spec-138 SSOT-PD: NDJSON canonical for events).
- [x] **M2.T6** — `/ai-autopilot` Phase 0 + `/ai-build` step 0 consult `probe()` before dispatch.
- [x] **M2.T7** — When `probe.ok_to_dispatch == False`: emit `host_pressure_warning`; degrade to cap=1.
- [x] **M2.T8** — `tests/integration/test_host_preflight.py` GREEN: 4 scenarios (healthy / high pressure / low free RAM / single core).
- [x] **M2.T9** — `tests/architecture/test_layer_isolation.py` confirms `adapters/host/` is a port, not domain.

## Milestone M3 — Phase-0 stack context pre-resolution

**Anchor:** §10.4 DRY.

### Tasks

- [x] **M3.T1** — Phase 0 reads `manifest.yml` once, computes resolved stack list + test command + format command. Resolver lives at `src/ai_engineering/autopilot/stack_context.py` (`resolve_stack_context` + `write_stack_context`, pure stdlib, fail-open).
- [x] **M3.T2** — `phase-deep-plan.md` now carries the new "Step 0 — Stack context resolution (spec-139 M3)" block that invokes `resolve_stack_context()` / `write_stack_context()` and writes `.ai-engineering/runtime/autopilot/<active>/stack-context.json`.
- [x] **M3.T3** — `phase-implement.md` dispatch loop (step 2b, item 3b) now requires every Build agent invocation to include `STACK_CONTEXT=<JSON>`; the Phase 2 dispatch list in `phase-deep-plan.md` carries the same requirement.
- [x] **M3.T4** — `.claude/agents/ai-build.md`, `ai-explore.md`, `ai-plan.md` rewritten: stack reads now come from the `STACK_CONTEXT` dispatch-prompt variable; manifest.yml mentions remain only as "do NOT re-read" pointers. Fallback path (`resolve_stack_context()`) documented for non-autopilot dispatch.
- [x] **M3.T5** — `.venv/bin/ai-eng dev sync` regenerated `.codex/`, `.gemini/`, `.github/`, `.opencode/`, `.cursor/`, and `templates/project/` mirrors after the skill/agent edits; `ai-eng dev sync --check` returns "Mirrors in sync".
- [x] **M3.T6** — `tests/integration/test_stack_context_propagation.py` GREEN (10 cases): canonical keys, python defaults, polyglot fan-out, idempotency, missing manifest, manifest without stacks, unreadable manifest (directory), valid JSON, byte-stable sorted output, runtime-subdir creation.

## Milestone M4 — Stale "x3" claim correction

**Anchor:** §10.7 Clean Code · §13 hard rules · D-139-10.

### Tasks

- **M4.T1** — Edit `.claude/agents/ai-autopilot.md:3`: change "verify+guard+review x3" to "verify+guard+review (single round, fail-loud)".
- **M4.T2** — Re-mirror to `.codex/`, `.gemini/`, `.github/` via `scripts/sync_mirrors/core.py`.
- **M4.T3** — `tests/architecture/test_agent_description_contract.py` enforces: no occurrence of "x3", "×3", "3 rounds" in any agent description that conflicts with `phase-quality.md:3` single-round contract.

## Milestone M5 — Hook hot-path budget enforcement

**Anchor:** §10.1 KISS · §10.5 TDD · D-139-03.

### Tasks

- **M5.T1** — `prompt-injection-guard.py`: module-level LRU cache for IOC catalogue + decision-store, invalidated on mtime change.
- **M5.T2** — `instinct-observe.py`: batched writes (50-event buffer / 5 s flush / SubagentStop flush).
- **M5.T3** — `runtime-stop.py`: skip convergence check when (a) last < 30 s ago AND (b) no git changes AND (c) Stop is SubagentStop cascade.
- **M5.T4** — `auto-format.py`: skip formatter when file mtime within `_AUTOFORMAT_DEBOUNCE_SEC` (default 1 s) of last format.
- **M5.T5** — New env: `AIENG_HOOK_CACHE_TTL_SEC` (default 300), `AIENG_HOOK_BUDGET_PROFILE` (0/1).
- **M5.T6** — `tests/unit/hooks/test_hot_path_budget.py` GREEN — measures actual hook timing under load with `AIENG_HOOK_ENGINE` set to each of `(default-claude, codex, gemini)`.
- **M5.T7** — `tests/unit/hooks/test_canonical_events_count.py` still GREEN (no event change).

## Milestone M6 — Runtime rotation throttle + state.db vacuum

**Anchor:** §10.1 KISS · §10.4 DRY · D-139-12 (coordinates with spec-138 M4.T4).

### Tasks

- [x] **M6.T1** — New script `.ai-engineering/scripts/hooks/runtime-rotate-throttled.py` (canonical, IDE-agnostic). Throttle: 1 hour minimum between runs (touch `.ai-engineering/runtime/.rotate-lastrun`).
- [x] **M6.T2** — Update `runtime-session-end.py` to add `state.db PRAGMA incremental_vacuum(1000)` when free pages > 1000. (NDJSON rotation invocation lives in spec-138 M4.T4.)
- [x] **M6.T3** — Cross-IDE wiring:
  - `.claude/settings.json` SessionEnd → `runtime-rotate-throttled.py`.
  - `.codex/hooks.json` Stop → same with `AIENG_HOOK_ENGINE=codex`.
  - `.gemini/settings.json` AfterAgent → same with `AIENG_HOOK_ENGINE=gemini` + `CLAUDE_HOOK_EVENT_NAME=SessionEnd`.
- [x] **M6.T4** — `tests/integration/test_runtime_rotation_lifecycle.py` GREEN — 7 cases covering subprocess wrapper invocation across the lifecycle (sentinel created on first run, throttle skips second run, env override releases gate, non-SessionEnd events short-circuit, plus three resolver micro-tests).
- [x] **M6.T5** — `tests/architecture/test_hook_wiring_parity.py` GREEN — 6 cases assert M6 wiring exists once in each of `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json` and that Codex / Gemini commands carry the `AIENG_HOOK_ENGINE=<engine>` label. `tests/unit/hooks/test_state_db_incremental_vacuum.py` (new) — 4 cases cover the M6.T2 helper (vacuum runs when freelist > 1000, skips when ≤1000, no-ops on missing DB, no-ops on corrupt DB).

## Milestone M7 — Deterministic spec verify + plan DAG

**Anchor:** §10.6 SDD · §10.5 TDD · D-139-05.

### Tasks

- [x] **M7.T1** — New CLI: `ai-eng spec verify --sections <path>` returns missing section headers (deterministic regex / string-contains check, lives in `src/ai_engineering/cli_commands/spec_cmd.py`).
- [x] **M7.T2** — New CLI: `ai-eng plan dag-build <subdir>` returns wave assignment JSON (pure-Python topological sort in `src/ai_engineering/cli_commands/plan_cmd.py`, wired through the new `plan` Typer sub-group in `cli_factory.py`).
- [x] **M7.T3** — `/ai-brainstorm` Step 6 now runs `ai-eng spec verify --sections .ai-engineering/specs/spec.md` BEFORE the LLM validation pass; the structural exit-1 short-circuits the LLM call.
- [x] **M7.T4** — `/ai-autopilot` Phase 3 ORCHESTRATE now invokes `ai-eng plan dag-build` FIRST in a new "Step 0 -- Deterministic DAG Pre-Pass" section; LLM reasoning fires only when the script reports conflicts. `tests/unit/cli/test_spec_verify.py` (4 cases) and `tests/unit/cli/test_plan_dag_build.py` (5 cases) GREEN; fixtures live under `tests/unit/cli/fixtures/{spec_verify,plan_dag}/`.

## Milestone M8 — Determinism final-mile (commit + PR)

**Anchor:** §10.4 DRY · D-139-06.

### Tasks

- [x] **M8.T1** — Updated `/ai-commit`, `/ai-build` (`handlers/deliver.md`), `/ai-autopilot` (`handlers/phase-implement.md`, `handlers/phase-deliver.md`), and `/ai-pr` Step 13 to compose commit subjects via `commit_compose.py --desc "<plan-task-title>"` deterministically. Skill markdown now documents the `grep -m1 '^- \[ \] ' .ai-engineering/specs/plan.md | sed 's/^- \[ \] //' | head -c 60` helper for callers and marks the `<DESC>` placeholder fallback as deprecated.
- [x] **M8.T2** — Added the mandatory `summary:` field to `.ai-engineering/reference/spec-schema.md` with a 30-day soft-rollout window (D-139-06): `frontmatter_missing_summary` emits ADVISORY until 2026-06-16 and BLOCKER after. `tools/spec_lint/checks/frontmatter.py` enforces the dated severity at lint time; `summary` joined `EXTRAS_ALLOWLIST` so the unknown-key advisory stays silent. All four archive specs in the run (138/139/140/141) already carry `summary:`.
- [x] **M8.T3** — Rewrote `.claude/skills/ai-pr/SKILL.md` Step 14 to invoke `pr_body_compose.py` WITHOUT `--bullets-prompt` whenever spec frontmatter carries `summary:`. Legacy specs that predate the field still trigger an advisory-warning fall back. The script already prefers `frontmatter.summary` over `--bullets-prompt`, so no Python change was needed.
- [x] **M8.T4** — `tests/unit/skills/test_no_residual_llm_compose.py` (3 cases) GREEN: greps every committed skill file across `.claude/`, `.codex/`, `.gemini/`, `.github/`, and every project-template surface for forbidden patterns; defends the active spec.md `summary:` field as defence-in-depth.
- [x] **M8.T5** — `ai-eng dev sync` regenerated `.codex/`, `.gemini/`, `.github/`, and project-template mirrors after each skill edit; `ai-eng dev sync --check` returns "Mirrors in sync".

## Milestone M9 — CLAUDE.md reconciliation + tunables documentation

**Anchor:** §10.7 Clean Code · D-139-07.

### Tasks

- [x] **M9.T1** — Update `CLAUDE.md` "Runtime Layer Tunables" to add: `AIENG_MAX_WAVE_AGENTS`, `AIENG_MAX_QUALITY_AGENTS`, `AIENG_MAX_THREAD_WORKERS`, `AIENG_HOST_PREFLIGHT_*`, `AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_NDJSON_MAX_LINES`, `AIENG_NDJSON_MAX_BYTES`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC`.
- [x] **M9.T2** — Fix `AIENG_TOOL_OFFLOAD_BYTES` default — change from `4096` to `16384` to match code.
- [x] **M9.T3** — Re-mirror to `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`.
- [x] **M9.T4** — `tests/architecture/test_tunables_docs_match_code.py` (parses CLAUDE.md table, greps code defaults, asserts match).

## Cross-spec coordination

- **spec-138 dependency.** M6 consumes the SessionEnd NDJSON rotation wire added by spec-138 M4.T4. This spec does NOT duplicate the rotation invocation; only adds the 1-hour throttle wrapper and `state.db PRAGMA incremental_vacuum`.
- **spec-140 dependency.** spec-140 removes the `instinct-observe.py` double-registration (PreToolUse + PostToolUse). M5.T2 here adds batching that survives the deduplication; verify both via the parametrized timing test.
- **spec-141 dependency.** None.

## Out of single-concern envelope

This plan is 9-milestone / multi-file and does NOT satisfy `/ai-build --no-hitl` single-concern gate. Implementation proceeds via the multi-spec orchestration; quality loop runs once at the end of the combined run.
