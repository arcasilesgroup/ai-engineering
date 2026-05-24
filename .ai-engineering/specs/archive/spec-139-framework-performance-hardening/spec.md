---
spec: spec-139
slug: framework-performance-hardening
title: Framework Performance Hardening — Concurrency Cap, Host Preflight, Hook Hot-Path Budget, SessionEnd Retention
status: approved
effort: large
branch: claude/review-spec-drafts-DX2pD
source_brief: .ai-engineering/specs/drafts/framework-performance-hardening-brief.md
target_dispatch: /ai-build
chains_after: spec-138
mantra: "ai-engineering NEVER causes WindowServer to hang. Every wave declares a concurrency budget. Every LLM call earns its place."
trigger_incident: macOS M1 Pro kernel panic during /ai-autopilot — WindowServer watchdog timeout 171s; compressor 100% segments (BAD); 42 swapfiles
date_approved: 2026-05-16
auto_approved: true
auto_approval_reason: operator invoked --no-hitl autonomous run; the trigger incident is real and waiting is not an option; brief carries explicit recommendations on all 11 open decisions
summary: Cap parallel agent dispatch with `AIENG_MAX_WAVE_AGENTS` (auto-tuned from host capacity), add `ai-eng host probe` preflight, enforce hook hot-path budgets via module-level mtime-based caching in `prompt-injection-guard.py` + batched writes in `instinct-observe.py` + convergence-skip in `runtime-stop.py`, wire `runtime-rotate-throttled.py` to SessionEnd across the three active runtime surfaces (claude-code, codex, gemini-cli), add `state.db PRAGMA incremental_vacuum` to SessionEnd, replace LLM calls with deterministic Python on structural paths (`ai-eng spec verify --sections`, `ai-eng plan dag-build`, `commit_compose --desc`, `pr_body_compose` reading spec `summary:`), and reconcile CLAUDE.md tunables documentation with code defaults. Closes the kernel-panic vector and the per-tool-call hook tax.
---

# spec-139 — Framework Performance Hardening

> Mantra: **ai-engineering NEVER causes WindowServer to hang. Every wave declares a concurrency budget. Every LLM call earns its place.**

## Summary

A real macOS M1 Pro (16 GB) kernel-panicked under userspace-watchdog timeout while executing `/ai-autopilot`: WindowServer missed 171 s of check-ins, the memory compressor reached 100 % of segments (BAD), and 42 swapfiles existed. The proximate cause traces to ai-engineering itself — four uncapped parallel-dispatch sites (autopilot Phase 2 deep-plan fan-out, Phase 4 wave build fan-out, the policy-orchestrator `ThreadPoolExecutor`, and an interpretable "verify+guard+review x3" stale claim contradicting the canonical single-round contract), compounded by per-tool-call hook tax (`prompt-injection-guard.py` reloads a 38 KB IOC catalogue on every Bash/Write/Edit; `instinct-observe.py` writes NDJSON on both Pre and Post; `runtime-stop.py` invokes ruff + pytest-smoke on every SubagentStop cascade), runtime artefacts whose retention policies exist but are never triggered, and structural LLM calls that a 20-line Python script could do better. This spec ships nine milestones in one PR that close the kernel-panic class, surface host capacity to dispatchers, enforce hook hot-path budgets, wire runtime rotation to SessionEnd across the three active runtime surfaces (claude-code, codex, gemini-cli), and replace LLM judgment with deterministic scripts on every structural path that earns nothing from LLM reasoning.

## Goals

1. **Concurrency-cap effective.** `AIENG_MAX_WAVE_AGENTS=2` on the trigger machine causes Phase 2 to dispatch 2 agents at a time, not N. Verified via the new `wave_dispatch_batched` framework event.
2. **Host preflight active.** `ai-eng host probe` returns valid JSON on darwin and linux; `host_capacity` event is emitted before every wave by any skill that dispatches ≥ 2 parallel subagents; degradation to cap = 1 triggers when `memory_pressure ≥ 50 %` or `swap_used_pct ≥ 20 %`.
3. **Manifest reads eliminated from dispatched agents.** Phase 0 resolves stack context once, propagates as `STACK_CONTEXT=…` JSON in every dispatch prompt; `tool-history.ndjson` for an N=6 autopilot run shows zero `Read` calls on `manifest.yml` from build / explore / plan agents.
4. **No stale "x3" claim.** Grep returns zero matches in any committed file under `.claude/`, `.codex/`, `.gemini/`, `.github/`.
5. **Hot-path budget met.** p95 hook timing: `prompt-injection-guard.py` < 50 ms (cached); `instinct-observe.py` < 5 ms (buffered); `auto-format.py` < 30 ms (debounced); `runtime-stop.py` skips convergence on SubagentStop cascade within 30 s of last check.
6. **Runtime rotation triggers.** `SessionEnd` invokes `runtime-rotate-throttled.py` across all three active runtime surfaces; NDJSON rotates above thresholds (consumes spec-138 M4 wiring); `state.db` incremental vacuum runs when free pages > 1000.
7. **Deterministic short-circuits.** `/ai-brainstorm` calls `ai-eng spec verify --sections` first; `/ai-autopilot` Phase 3 calls `ai-eng plan dag-build` first; LLM invoked only when deterministic path returns ambiguity.
8. **No residual avoidable LLM compose calls.** `/ai-commit`, `/ai-pr` always pass `--desc` / read `summary:` frontmatter.
9. **Tunables documented.** Every new `AIENG_*` env var in CLAUDE.md; drift test (`test_tunables_docs_match_code.py`) green.

## Non-Goals

- Reducing the total skill count (54) or agent count (24) — separate concern, lives in spec-140.
- Adopting a different LLM provider or local-only mode.
- Switching from Claude CLI to a custom orchestration loop.
- Distributed orchestration / remote agents.
- Replacing `/ai-autopilot` Phase architecture.
- Removing the auditing layer (governed by CONSTITUTION.md §13 hard rule).
- Per-spec custom concurrency budgets (YAGNI — single global cap with auto-tune covers 95 %).
- Real-time pressure-based dynamic re-throttling mid-wave.
- `opencode` and `cursor` hook wiring (mirror directories absent on disk; deferred until the directories materialize).
- `github-copilot` runtime SessionEnd wiring (no conversational SessionEnd surface — `.github/hooks/` is git-lifecycle only).

## Decisions

- **D-139-01 — Default `AIENG_MAX_WAVE_AGENTS`.** Auto-compute from host with floor=2, ceiling=6. Rationale: adapts to operator hardware; floor protects single-core / 8 GB hosts; ceiling prevents accidental fan-out on 64 GB workstations. Resolves brief D1.
- **D-139-02 — Host preflight scope.** Apply to all skills that dispatch ≥ 2 parallel subagents: `/ai-autopilot`, `/ai-build`, `/ai-review`, `/ai-verify`. Skills that dispatch ≤ 1 skip the probe. Rationale: the probe overhead (one `vm_stat` + two `sysctl` calls) is only justified when the dispatch could exhaust resources. Resolves brief D2.
- **D-139-03 — Hot-path cache invalidation strategy.** mtime-based (file-level). Rationale: atomic syscall, cheap, sufficient. False-positive invalidation is harmless (one extra reload); false-negative requires content tampering already covered by `AIENG_HOOK_INTEGRITY_MODE`. Resolves brief D3.
- **D-139-04 — NDJSON rotation policy.** Archive + start fresh chain + retain 3 archives in `state/archives/`. Rationale: audit chain preserved (Article-III); old archives age out via `runtime_rotate.py`. Resolves brief D4.
- **D-139-05 — Phase 3 DAG fallback semantics.** Escalate to LLM Phase-3 reasoning automatically when `ai-eng plan dag-build` reports conflicts. Rationale: preserves current behavior for the 10 % ambiguous case; deterministic short-circuit handles the 90 %. Resolves brief D5.
- **D-139-06 — `summary:` frontmatter migration.** Soft initially (warn and synthesize from spec title), hard after 30 days. Rationale: existing specs (spec-128 through spec-137) have varied frontmatter; a hard cutover would break re-build of historical context. Resolves brief D6.
- **D-139-07 — Tunable surface — env vars vs manifest knobs.** Both, env precedence. Rationale: manifest captures project defaults; env overrides for one-off runs. Mirrors existing `AIENG_*` pattern. Resolves brief D7.
- **D-139-08 — Validation on the trigger machine.** Synthetic repro pre-merge (DoD step), plus 30-day post-merge monitoring via `host_capacity` events. Rationale: both protect against the immediate regression and surface drift. Resolves brief D8.
- **D-139-09 — Hexagonal placement of `host/probe.py`.** Adapter layer under `src/ai_engineering/adapters/host/`. Rationale: host inspection is a port to the operating system; domain is concurrency policy. Resolves brief D9.
- **D-139-10 — Backwards compatibility for "x3" correction.** Hard rename per CONSTITUTION.md §3. Rationale: the text drift was a bug, not a contract; CHANGELOG documents the breakage. Resolves brief D10.
- **D-139-11 — opencode / cursor wiring scope.** Wait — defer per-surface wiring until those mirror directories materialize in a separate spec. Rationale: creating `.opencode/` with only a hook config and no skills/agents would violate Surface Axiom A1 (parity). CHANGELOG documents the deferral. Resolves brief D11.
- **D-139-12 — Order alongside spec-138.** spec-138 ships the NDJSON rotation wire; this spec adds the 1-hour throttle wrapper (`runtime-rotate-throttled.py`) and `state.db PRAGMA incremental_vacuum`. Rationale: cleaner sequencing in same PR.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Concurrency cap of 2-3 makes autopilot feel "slow" on healthy hosts | MEDIUM | Auto-tune from host capacity (D-139-01); 32 GB / 16 cores → cap of 4-6 |
| Host probe returns wrong values on macOS Sonoma / Sequoia | HIGH | Snapshot tests on multiple macOS versions; fail-open default (cap=auto fallback to 2) |
| `prompt-injection-guard.py` cache invalidation race | MEDIUM | mtime check is atomic; cache per-process not shared; worst case one extra reload |
| `instinct-observe.py` buffering loses events on crash | LOW | SubagentStop is the natural flush point; persistence loss bounded to last 5 s; instinct data is advisory, not audit |
| `runtime-rotate-throttled.py` fires while autopilot is mid-run | MEDIUM | Throttle 1 hour; SessionEnd only fires at conversation end, not mid-tool-call |
| Deterministic plan DAG misses semantic conflicts | MEDIUM | Phase 3 LLM still runs when script returns ambiguity (D-139-05) |
| Forced `--desc` from task title produces poor commit messages | LOW | Task title in `plan.md` is human-written or `/ai-plan`-curated; bound by plan quality |
| Mandatory spec `summary:` field breaks existing specs | MEDIUM | Soft migration (D-139-06) — 30-day warn window |
| `state.db incremental_vacuum` interferes with active session | LOW | Runs only at SessionEnd, never mid-session |
| Removing redundant manifest reads changes agent behavior | LOW | `STACK_CONTEXT` JSON byte-equivalent to a manifest re-parse; integration test asserts equivalence |
| New tunables proliferate "knob soup" | MEDIUM | Every new tunable has a sensible default; CLAUDE.md table sorted by relevance |
| 9 milestones in one PR overwhelms reviewers | MEDIUM | Atomic commits per milestone; CHANGELOG is the index; M1+M4 alone is the safety-critical subset |
| The kernel panic recurs despite this work | CRITICAL | Validation step: rerun the failing autopilot on the same machine post-merge; document outcome in PR |

## References

- doc: .ai-engineering/specs/drafts/framework-performance-hardening-brief.md
- doc: CONSTITUTION.md §13 (hard rules)
- doc: CLAUDE.md "Hot-Path Discipline" section
- doc: .ai-engineering/specs/archive/spec-135-framework-performance-hardening.md (predecessor draft on same theme)
- pr: arcasilesgroup/ai-engineering#509 (spec-128/131/132/133/134 — concurrent surface work)

## Open Questions

None — all eleven open decisions in the brief are resolved as D-139-01 through D-139-11; D-139-12 documents the spec-138 coordination.
