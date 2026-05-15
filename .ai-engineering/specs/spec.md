---
spec: spec-135
slug: framework-performance-hardening
title: Framework Performance Hardening — Concurrency Budget, Host Preflight, Hook Hot-Path Discipline
status: approved
effort: large
branch: spec-135/framework-performance-hardening
source_brief: .ai-engineering/specs/drafts/framework-performance-hardening-brief.md
target_dispatch: /ai-autopilot
chains_after: spec-134
trigger_incident: macOS M1 Pro kernel panic during /ai-autopilot — WindowServer watchdog timeout 171s; compressor 100% segments (BAD); 42 swapfiles
summary: Cap parallel agent dispatch, add host preflight probe, enforce hook hot-path budgets, wire runtime rotation to SessionEnd across 3 active surfaces, and replace LLM calls with deterministic Python on structural paths so the framework cannot kernel-panic an operator machine.
---

# Framework Performance Hardening

## Summary

A real macOS M1 Pro (16 GB) kernel-panicked under userspace-watchdog timeout while executing `/ai-autopilot`: WindowServer missed 171 s of check-ins, the memory compressor reached 100 % of segments (BAD), and 42 swapfiles existed. The proximate cause traces to ai-engineering itself — four uncapped parallel-dispatch sites (autopilot Phase 2 deep-plan fan-out, Phase 4 wave build fan-out, the policy-orchestrator `ThreadPoolExecutor`, and an interpretable "verify+guard+review x3" stale claim contradicting the canonical single-round contract), compounded by per-tool-call hook tax (`prompt-injection-guard.py` reloads a 38 KB IOC catalogue on every Bash/Write/Edit; `instinct-observe.py` writes NDJSON on both Pre and Post; `runtime-stop.py` invokes ruff + pytest-smoke on every SubagentStop cascade), runtime artefacts whose retention policies exist but are never triggered, and structural LLM calls that a 20-line Python script could do better. This spec lands a single PR `spec-135/framework-performance-hardening` carrying nine milestones that close the kernel-panic class, surface host capacity to dispatchers, enforce hook hot-path budgets, wire runtime rotation to SessionEnd across the three active runtime surfaces (claude-code, codex, gemini-cli), and replace LLM judgment with deterministic scripts on every structural path that earns nothing from LLM reasoning.

## Goals

1. **Concurrency-cap effective.** `AIENG_MAX_WAVE_AGENTS=2` on the trigger machine causes Phase 2 to dispatch 2 agents at a time, not N. Verified via the new `wave_dispatch_batched` framework event (introduced by M1 — emitted by `phase-deep-plan.md`, `phase-implement.md`, and the orchestrator on each batch boundary) showing 3 batches of 2 instead of one batch of 6.
2. **Host preflight active.** `ai-eng host probe` returns valid JSON on darwin and linux; `host_capacity` event is emitted before every wave by any skill that dispatches ≥ 2 parallel subagents; degradation to cap = 1 triggers when `memory_pressure ≥ 50 %` or `swap_used_pct ≥ 20 %`.
3. **Manifest reads eliminated from dispatched agents.** Phase 0 resolves stack context once, propagates as `STACK_CONTEXT=…` JSON in every dispatch prompt; `tool-history.ndjson` for a N=6 autopilot run shows zero `Read` tool calls on `manifest.yml` from build / explore / plan agents.
4. **No residual stale "x3" or "max 3 rounds" claim.** Framework-wide grep across `.claude/`, `.codex/`, `.gemini/`, `.github/`, and `docs/` returns zero matches conflicting with the canonical single-round contract at `phase-quality.md:3`.
5. **Hook hot-path budget enforced.** Measured p95 on the trigger machine: `prompt-injection-guard.py` < 50 ms (cached); `instinct-observe.py` < 5 ms (buffered); `auto-format.py` < 30 ms (debounced); `runtime-stop.py` convergence skipped on SubagentStop cascade when `< 30 s` since last green check.
6. **Runtime rotation triggered automatically.** `SessionEnd` (and surface-equivalents on codex / gemini-cli) invokes `runtime-rotate-throttled.py`; `framework-events.ndjson` rotates above 100 k lines or 50 MB; `state.db PRAGMA incremental_vacuum` runs when free pages > 1000.
7. **Deterministic short-circuits in place.** `/ai-brainstorm` calls `ai-eng spec verify --sections` before any LLM section-presence judgment; `/ai-autopilot` Phase 3 calls `ai-eng plan dag-build` first and only escalates to LLM when the import-graph parser reports unresolvable conflicts.
8. **No residual avoidable LLM compose calls.** `/ai-commit`, `/ai-build`, `/ai-autopilot`, `/ai-pr` always pass `commit_compose.py --desc "<plan-task-title>"`; `/ai-pr` never invokes `pr_body_compose.py --bullets-prompt` when spec carries `summary:` frontmatter.
9. **Tunables documented; doc/code drift closed.** Every new and existing `AIENG_*` env var documented in `CLAUDE.md` (and mirrors); `AIENG_TOOL_OFFLOAD_BYTES` default reconciled (16384 in code, was misdocumented as 4096); `test_tunables_docs_match_code.py` green.
10. **Trigger-machine validation.** Pre-merge: synthetic `/ai-autopilot` run with N = 8 sub-specs on the trigger 16 GB M1 Pro; memory pressure stays < 60 % throughout; no watchdog timeout; no kernel panic; outcome documented in the PR body. Post-merge: a 30-day operator-dashboard follow-up brief consumes `host_capacity` events.
11. **Cross-IDE wiring parity.** M6 SessionEnd wiring lands in `.claude/settings.json`, `.codex/hooks.json`, and `.gemini/settings.json` (with Gemini-native event mapping verified during implementation); `test_hook_wiring_parity.py` green; `github-copilot` waived in fixture (no conversational SessionEnd).
12. **Manifest hygiene.** `manifest.yml surfaces.enabled` no longer declares `opencode` or `cursor` — only surfaces with materialized mirrors remain (claude-code, codex, gemini-cli, github-copilot).
13. **Lifecycle plumbing portable.** `python3 .ai-engineering/scripts/spec_lifecycle.py start_new <slug> <title>` runs successfully on Python 3.9 (and later); `/ai-brainstorm` no longer fail-opens on the host that triggered this spec.

## Non-Goals

- Do **not** reduce or restructure the total skill / agent count in this spec — that is the orthogonal cohesion concern of the predecessor spec-134 brief.
- Do **not** adopt a different LLM provider, local-only mode, or replace the Claude CLI subprocess contract.
- Do **not** redesign `/ai-autopilot` phase architecture (this brief caps concurrency, not phases).
- Do **not** remove the auditing layer (`framework-events.ndjson`, `state.db`) — audit-chain immutability is a Constitution §13.1 hard rule.
- Do **not** re-architect the hexagonal layer; performance hardening must be layer-respectful.
- Do **not** introduce per-spec custom concurrency budgets, real-time pressure-based dynamic re-throttling mid-wave, or distributed / remote orchestration — explicit YAGNI in this brief.
- Do **not** wire `runtime-rotate-throttled.py` into `.opencode/` or `.cursor/` — those mirror directories do not exist and are being **removed** from `manifest.yml surfaces.enabled` in this PR (D-135-11).
- Do **not** add a runtime SessionEnd surface to `.github/hooks/hooks.json` — `.github/` is git-lifecycle, not conversational; explicitly waived in `test_hook_wiring_parity.py`.
- Do **not** ship the mandatory-`summary:` block in this PR — it lands soft (warn + autopopulate from title) and hardens in spec-140 (D-135-06).

## Decisions

### D-135-01 — Single PR delivery, all nine milestones, severity-first commit sequencing

**Decision**: Land M1 – M9 in one PR on `spec-135/framework-performance-hardening`. Commit order within the PR mirrors brief §11 hand-off: safety (M1, M4) → observability + docs (M2, M9) → hot-path (M5) → determinism (M3, M7, M8) → retention (M6). Each milestone composes as a discrete atomic commit set under Conventional Commits §13.6.

**Rationale**: Operator confirmed (interrogation Q1) that a single cohesive PR is preferred over a hotfix split. The brief flagged "M1 + M4 alone is the safety-critical subset and can ship first as a hotfix branch if needed," but the operator chose the cohesive perf-story narrative. Severity-first ordering preserves the option to validate the safety subset on the trigger machine before later commits stack on, without splitting the PR.

### D-135-02 — Concurrency cap default = auto-tune with floor = 2, ceiling = 6

**Decision**: `AIENG_MAX_WAVE_AGENTS` default is `auto`, computed as `min(free_ram_gb // 4, cores // 2, 6)` with a hard floor of `2` and a hard ceiling of `6`. On the trigger machine (16 GB / 8 cores / ~8 GB free / 10 % pressure) this yields cap = 2. On a 32 GB / 16-core workstation it yields cap = 4. On a 64 GB workstation it caps at 6 to prevent accidental fan-out. Env override has precedence over manifest knob (D-135-12).

**Rationale**: Auto-tune adapts to operator hardware rather than imposing a one-size-fits-all cap. Floor = 2 protects single-core / 8 GB hosts from accidentally serializing to cap = 0 due to integer truncation. Ceiling = 6 prevents wave-fan-out from running away on large workstations where parallelism is technically affordable but operationally rarely justified. This is the brief default and it directly closes the kernel-panic vector on the trigger machine: cap = 2 makes the 6-agent fan-out simply impossible.

### D-135-03 — Host preflight applies to every skill that dispatches ≥ 2 parallel subagents

**Decision**: `/ai-autopilot`, `/ai-build` (wave dispatch path), `/ai-review` (specialist roster), `/ai-verify` (4-verifier roster), and `/ai-plan` (parallel exploration phase) all consult `probe()` before fan-out. Single-dispatch skills (`/ai-explore` alone, `/ai-debug`, `/ai-test`, `/ai-commit`, etc.) skip the probe to preserve their hot-path budget.

**Rationale**: The risk surface is parallel dispatch, not the skill identity. Wrapping single-shot operations in the probe would add latency to every hot path, violating the < 200 ms hook budget. Limiting the probe to fan-out sites matches the actual concurrency exposure and keeps single-shot skills fast.

### D-135-04 — Hot-path cache invalidation = mtime-based

**Decision**: Module-level caches in `prompt-injection-guard.py` (IOC catalogue, decision-store) and other hot-path scripts key on `Path.stat().st_mtime`. On mtime change, reload; otherwise serve from cache. Per-process scope — no cross-process shared state.

**Rationale**: mtime is an atomic syscall, cheap, and sufficient for the worst-case failure mode (one extra reload). Content-hash invalidation would be more correct but more expensive, and the false-negative scenario (stale cache despite content tampering) is already covered by hook-integrity sha256 enforcement (`AIENG_HOOK_INTEGRITY_MODE=enforce`).

### D-135-05 — NDJSON rotation policy = archive + retain 3 archives + start fresh

**Decision**: When `framework-events.ndjson` exceeds 100 k lines or 50 MB, `ai-eng maintenance reset-events --auto` archives the current chain to `state/archives/framework-events-<timestamp>.ndjson.gz` and starts a fresh chain. Up to three archives retained; older archives age out via `runtime_rotate.py`.

**Rationale**: Preserves Constitution §13.1 audit-chain immutability (archive, never truncate). Three archives is enough historical depth to investigate any incident within a reasonable forensic window without unbounded growth. Older archives are bounded by `runtime_rotate.py`'s 30-day TTL.

### D-135-06 — Mandatory spec `summary:` frontmatter — soft now, hard at spec-140

**Decision**: `spec-schema.md` adds `summary:` to required frontmatter. `/ai-brainstorm` warns when missing and autopopulates from `title:`. `/ai-pr` reads `summary:` when present, falls back to `--bullets-prompt` LLM call when absent. CHANGELOG flags a 30-day deprecation window; hard cutover lands in spec-140.

**Rationale**: Hard cutover in this PR would force migration of every existing approved spec (some lack `summary:`) inside the same already-large spec-135 PR, mixing perf hardening with spec metadata churn. The soft path captures the optimization for new specs immediately and lets existing specs migrate during the window. Brief default.

### D-135-07 — Tunable surface = both manifest and env, env precedence

**Decision**: Every tunable introduced or touched in this spec has both a manifest knob (e.g., `performance.concurrency.max_wave_agents`) and an env override (e.g., `AIENG_MAX_WAVE_AGENTS`). Env beats manifest beats hard-coded default.

**Rationale**: Mirrors the existing `AIENG_*` pattern. Manifest captures the project-wide default committed to source; env enables one-off operator overrides without editing tracked files. Documented in `CLAUDE.md` "Runtime Layer Tunables" (M9).

### D-135-08 — Phase-3 DAG fallback = escalate to LLM on conflict

**Decision**: `ai-eng plan dag-build` parses sub-spec `exports:/imports:` YAML and returns a wave-assignment JSON. When the parser detects conflicts unresolvable by import-graph alone (cycle, missing export, ambiguous overlap), it returns `{"status": "ambiguous", "conflicts": […]}` and `/ai-autopilot` Phase 3 escalates to the LLM-driven reasoning that lives there today. The 90 % structural case is deterministic; the 10 % semantic case keeps the existing behavior.

**Rationale**: Preserves the safety net for genuinely ambiguous decompositions (which do occur and require judgment) while eliminating LLM cost for the common case where the YAML alone suffices.

### D-135-09 — Host probe placement = adapter layer, not domain

**Decision**: `src/ai_engineering/adapters/host/probe.py` carries the platform adapters (darwin, linux); `src/ai_engineering/host/policy.py` (domain) carries the `auto_concurrency_cap(...)` decision. Mirrors how `state/db.py` and `state/instincts.py` are organized.

**Rationale**: Host inspection is a port to the operating system; concurrency budget is the domain decision. Hexagonal §10.8 layering test (`tests/architecture/test_layer_isolation.py`) enforces this.

### D-135-10 — "x3" / "max 3 rounds" correction is a hard rename, framework-wide

**Decision**: Sweep all stale references across `.claude/`, `.codex/`, `.gemini/`, `.github/`, and `docs/`. Replace with the canonical single-round phrasing matched to `phase-quality.md:3`. Verified by `test_agent_description_contract.py` which greps the entire tree for the forbidden patterns. No backwards-compat shim, no deprecation alias — Constitution §13.3.

**Rationale**: Operator confirmed (interrogation Q2) that the M4 sweep must be framework-wide, not the brief's narrower "fix line 3 only." The brief itself flagged line 3, but the same contradiction also exists on `ai-autopilot.md:18` ("max 3 rounds") and the grep test (`test_agent_description_contract.py`) is the authoritative verification surface. The panic vector is interpretation-sensitive — the LLM that reads any description must see exactly one consistent claim everywhere.

### D-135-11 — Drop `opencode` and `cursor` from `manifest.yml surfaces.enabled` in this PR

**Decision**: Diverges from brief recommendation. `manifest.yml surfaces.enabled` is edited to list only the materialized surfaces — `claude-code`, `codex`, `gemini-cli`, `github-copilot`. The `.opencode/` and `.cursor/` directories do not exist on disk; declaring them creates a conceptual debt that downstream tooling (parity tests, hook-wiring tests) must work around. CHANGELOG documents the removal as a `BREAKING CHANGES` entry with a "re-declare in a future spec when the mirror payload is authored" note.

**Rationale**: Operator chose this over the brief's "defer entirely" recommendation (interrogation Q6). Cleaner posture: we do not declare surfaces we cannot materialize. Removing the declarations simplifies `test_hook_wiring_parity.py` (no "deferred" stub list) and prevents downstream specs from inheriting unwarranted parity obligations. When opencode or cursor are wanted, a dedicated spec materializes mirror + skill + agent + wiring atomically.

### D-135-12 — Validation commitment = synthetic repro pre-merge + 30-day post-merge monitoring

**Decision**: Pre-merge DoD gate: operator runs `/ai-autopilot` on a spec with N = 8 sub-specs on the same 16 GB M1 Pro that originally panicked; captures `top -l 1 -s 0 -n 0` samples; confirms memory pressure < 60 % throughout; no watchdog timeout; no kernel panic; documents the outcome in the PR body. Post-merge: a follow-up brief (`framework-observability-dashboard-brief.md`) consumes `host_capacity` framework events to build a 30-day operator dashboard. The dashboard work is **out of scope** for spec-135 — only the event substrate is in scope here.

**Rationale**: Operator owns the trigger machine; the synthetic repro is the only way to actually prove the panic vector is closed. Tests alone (`test_concurrency_budgets.py`) prove the mechanism works in isolation, not that the panic vector is closed on the specific hardware. The 30-day monitoring extends confidence but is correctly deferred to a follow-up brief that owns the dashboard.

### D-135-13 — `spec_lifecycle.py` Python 3.11 dependency fix

**Decision**: `.ai-engineering/scripts/spec_lifecycle.py` uses `from datetime import UTC` (requires Python ≥ 3.11). The brainstorm session for *this very spec* failed to bootstrap the DRAFT sidecar because the host runs Python 3.9 (fail-open per skill spec, but the script is silently broken on every < 3.11 host). The fix replaces the import with the 3.9-compatible `datetime.timezone.utc`. The Python-floor sub-question (raise `python_requires` vs maintain 3.9 compatibility) defers to `/ai-plan` after a grep of the existing codebase. A goal entry (Goal 13) is added to verify closure.

**Rationale**: Caught during evidence sweep — the framework's own lifecycle plumbing silently no-ops on common operator hosts. Including this fix preserves the perf-hardening narrative's "every script earns its place" mantra. Small, localized change; out-of-scope deferral would orphan the bug. Operator confirmed in-scope during spec review.

### D-135-14 — Brief's evidence catalog promoted intact to the plan; severity assignments accepted

**Decision**: The 23 P-IDs in brief §5 (P1 – P23) map 1:1 onto the M1 – M9 implementation milestones, with the brief's severity classification preserved (CRITICAL: P1, P2, P15; HIGH: P3, P4, P5, P6, P8, P16; MEDIUM: P7, P9, P10, P11, P12, P13, P18, P22, P23; LOW: P14, P17, P19, P20, P21). `/ai-plan` MUST decompose milestones into TDD-first tasks that resolve each P-ID it covers.

**Rationale**: The brief's evidence catalog is the load-bearing artefact for verifying spec-135 closure. Renumbering or recategorizing would lose the audit trail back to the kernel panic. The plan is the contract that closes each P explicitly.

### D-135-15 — Adopt brief defaults silently for D3, D4, D5, D7, D9, D10

**Decision**: Decisions D-135-04 (mtime invalidation), D-135-05 (NDJSON rotation), D-135-07 (env precedence), D-135-08 (DAG fallback), D-135-09 (hexagonal placement), D-135-10 (hard rename for x3) all follow the brief's recommended resolutions verbatim. No interrogation question was asked for these because every alternative is materially worse (e.g., content-hash invalidation vs mtime adds expense for no real correctness gain in a sha256-pinned-hook environment).

**Rationale**: Interrogation budget is best spent on decisions where the operator has genuine policy preference. Where the brief's recommendation is technically dominant, adopting silently preserves the budget. All such decisions are surfaced here so the operator can override during the review loop.

## Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Concurrency cap of 2 – 3 makes autopilot feel slow on healthy hosts | MEDIUM | Auto-tune from host capacity (D-135-02) — 32 GB / 16 cores yields cap = 4; cap is per-host not global; manifest knob + env override allow project-wide adjustment |
| R2 | Host probe returns wrong values on macOS Sonoma / Sequoia | HIGH | Snapshot tests on multiple macOS versions; fail-open default falls back to cap = auto with `floor = 2`; `tests/integration/test_host_preflight.py` covers 4 scenarios (healthy / high pressure / low free RAM / single core) |
| R3 | `prompt-injection-guard.py` mtime-based cache misses a tampered IOC file with preserved mtime | LOW | `AIENG_HOOK_INTEGRITY_MODE=enforce` (default) already verifies hook script sha256; IOC catalog tampering is a higher-privilege threat than the perf optimization addresses; risk-accept via `ai-eng risk accept` if surfaced by security review |
| R4 | `instinct-observe.py` buffered writes lose the last < 5 s of events on a crash | LOW | SubagentStop is the natural flush point; instinct data is advisory not audit (Article-III audit chain lives in `framework-events.ndjson` which is unbuffered); document the bound in the script docstring |
| R5 | `runtime-rotate-throttled.py` fires while autopilot is mid-run | MEDIUM | Throttle to 1 hour minimum; SessionEnd in Claude Code only fires when conversation ends (not mid-tool-call); equivalent on codex / gemini-cli verified during M6 wiring |
| R6 | Deterministic plan DAG misses semantic conflicts (cycle detection only) | MEDIUM | Phase 3 LLM still runs when script returns `{"status": "ambiguous"}` (D-135-08); script handles structural 90 %, LLM handles semantic 10 % |
| R7 | Forced `--desc` from plan task title produces poor commit messages | LOW | Task titles in `plan.md` are either human-written or `/ai-plan`-curated; quality bound by plan quality, not commit-time prose; soft fallback to `<DESC>` placeholder when title is empty |
| R8 | Mandatory `summary:` field breaks existing specs | MEDIUM (mitigated by D-135-06) | Soft enforcement initially; `/ai-brainstorm` autopopulates from title; CHANGELOG announces 30-day window; hard cutover lands in spec-140 |
| R9 | `state.db PRAGMA incremental_vacuum` interferes with active session | LOW | Runs only at SessionEnd; never mid-session; bounded to a single 1000-page vacuum per invocation |
| R10 | `STACK_CONTEXT` propagation drifts semantically from a fresh manifest re-parse | LOW | `tests/integration/test_stack_context_propagation.py` asserts byte-equivalence; Phase 0 re-computes per session, not cached across sessions |
| R11 | New tunables proliferate "knob soup" in `CLAUDE.md` | MEDIUM | Single `AIENG_HOST_PREFLIGHT_DISABLED=1` opt-out covers all preflight tunables; CLAUDE.md table is sorted by relevance; M9 owns the documentation hygiene |
| R12 | Single PR with 9 milestones overwhelms reviewers | MEDIUM | Atomic commits per milestone with severity-first ordering (D-135-01); CHANGELOG is the index; brief's §11 hand-off sequence guides reviewer through the safety subset first |
| R13 | Dropping `opencode` / `cursor` from `surfaces.enabled` surprises operators expecting that support | MEDIUM | CHANGELOG `BREAKING CHANGES` entry explicitly calls out the removal; D-135-11 documents the re-declare-when-materialized policy; predecessor spec-134 governance referenced |
| R14 | The kernel panic recurs despite this work | CRITICAL | DoD validation step (D-135-12): rerun the failing autopilot on the same hardware post-merge; document outcome in PR body; 30-day monitoring catches regression via `host_capacity` events |
| R15 | `spec_lifecycle.py` fix introduces unrelated Python-version churn | LOW | D-135-13 scopes the fix to a single import replacement; `/ai-plan` decides whether to add a `python_requires` floor based on what other framework code already requires |

## References

- doc: .ai-engineering/specs/drafts/framework-performance-hardening-brief.md
- doc: CONSTITUTION.md
- doc: docs/principles.md
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/manifest.yml
- pr: arcasilesgroup/ai-engineering#509
- doc: .claude/skills/ai-autopilot/handlers/phase-quality.md
- doc: .claude/agents/ai-autopilot.md
- doc: .ai-engineering/scripts/hooks/prompt-injection-guard.py
- doc: .ai-engineering/scripts/runtime_rotate.py
- doc: src/ai_engineering/policy/orchestrator.py
- doc: CLAUDE.md

## Open Questions

1. **Python version floor for D-135-13.** Does the framework already require Python ≥ 3.11 elsewhere? `/ai-plan` resolves by grepping `pyproject.toml` and any `python_requires` declarations before deciding between 3.9-compat backfill vs raising the floor.
2. **Gemini-native end-of-session event mapping (M6).** Brief speculates `AfterAgent` or session-stop equivalent. `/ai-plan` must read Gemini hook docs (or `/ai-research`) and pin the exact event name before M6 wiring lands. Failure mode is a silent no-op on gemini-cli, which `test_hook_wiring_parity.py` would catch.
3. **`state.db` schema for `host_capacity` events.** Does the existing `events` table accept the JSON shape proposed in §4.2 of the brief, or does it require a migration? `/ai-plan` decides whether the event lives in `framework-events.ndjson` only (Article-III chain) or both NDJSON and `events` (queryable).
4. **CHANGELOG `BREAKING CHANGES` shape for the manifest surface removal (D-135-11).** Phrasing must be unambiguous about the re-declare path for opencode / cursor and must not promise a future spec timeline.

---

**Status**: approved 2026-05-15 — `/ai-plan` may consume.
