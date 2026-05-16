---
title: "Framework Performance Hardening — Deterministic-First Pipeline, Bounded Concurrency, Memory Discipline, Hook Hot-Path Budget Enforcement"
status: draft
audience: /ai-brainstorm
trigger_incident: "macOS M1 Pro kernel panic during /ai-autopilot or /ai-build — WindowServer watchdog timeout 171s; memory compressor 100% of segments (BAD); 42 swapfiles; userspace_watchdog reboot"
branch: spec-135/framework-performance-hardening
length_estimate: "~840 lines"
authoring_style: "Staff Principal Architect IQ-200 — long-horizon, hexagonal, fail-loud, evidence-anchored, host-aware, cross-IDE"
principles_required: [KISS, YAGNI, DRY, SOLID, TDD, SDD, clean-code, hexagonal]
delivery_mode: "Multi-wave continuation / hard-rename / no-shim / Conventional Commits per Constitution §13.6 / cross-IDE wiring parity across 3 active runtime surfaces (claude-code, codex, gemini-cli)"
predecessor_brief: "skills-agents-excellence-v2-brief.md (spec-134 — orthogonal: UX cohesion vs performance)"
mantra: "ai-engineering NEVER causes WindowServer to hang. Every wave declares a concurrency budget. Every LLM call earns its place — scripts do the mechanical work. The hot path is profiled, not assumed."
---

> **READ FIRST.** This brief was generated AFTER a real macOS kernel panic on an Apple Silicon M1 Pro (16 GB) while running `/ai-autopilot` or `/ai-build`. The diagnosis: severe memory pressure (compressor at 100% of segments, 42 swapfiles, WindowServer missed 171s of watchdog check-ins). The hypothesis: ai-engineering's orchestrators fan out parallel Claude subagent processes without an explicit concurrency or memory budget, compounding the cost of every spec into N concurrent Claude processes each consuming multiple GB of RSS, plus hook overhead per tool call, plus state/runtime artefacts that grow unbounded. Every claim below carries a `file:line` citation gathered by `/ai-explore` during a 15-minute audit (143k tokens / 110 tool calls). No implementation begins until this brief is promoted to `spec-NNN` and approved through `/ai-brainstorm`.
>
> **Scope discipline.** This is a performance refactor of **survival**, not of polish. The framework is currently capable of killing a developer machine. Every change here exists because a parallel dispatch lacks a cap, a hook fires too often, an LLM is invoked for work a 50-line script can do better, or a runtime artefact grows without retention. KISS is the test: if a deterministic Python script can replace an LLM call without loss of judgment, the LLM call is wrong. The framework must feel lightweight, predictable, and never kernel-panic an operator's machine.

---

## 0. North Star

The picture that stays on the wall:

> **A developer types `/ai-autopilot` on a 16 GB M1 Pro and the framework declares a concurrency budget BEFORE dispatching anything — "Host: 16 GB / 8 cores / memory_pressure=42% → wave concurrency cap = 3 agents." The Phase-2 deep-plan fans out 3 explore+plan agents at a time (not 10 simultaneously). The Phase-4 build wave fans out 3 build agents at a time. The Phase-5 quality loop runs 3 assessors with shared cached context. Manifest reads happen ONCE in Phase 0 and propagate as JSON in dispatch prompts (no 12 redundant `Read` calls). Plan DAG construction is a Python parse of `exports:/imports:` YAML (no LLM judgment for the 90% case). Spec shape validation is a 20-line regex check. CHANGELOG entries skeleton from `git-cliff`. Hook hot-path scripts cache catalogues at module scope. `prompt-injection-guard.py` loads IOC + decision-store ONCE per session, not once per tool call. `instinct-observe.py` batches writes. `runtime_rotate.py` runs on every `SessionEnd`. `framework-events.ndjson` rotates at 100k lines / 50 MB. The framework never causes WindowServer to hang. Every operator can predict the resource cost of any `/ai-*` command from its dispatch budget alone.**

This is the photo. Every milestone in §6 advances at least one pixel of it. Every Open Decision in §10 lives because the photo is not yet developed.

---

## 1. Executive Summary (one screen)

**Nine performance deltas land in PR `spec-135`:**

1. **Concurrency budget primitive — `AIENG_MAX_WAVE_AGENTS`** caps parallel agent dispatch in `/ai-autopilot` Phase 2, Phase 4, Phase 5, and the policy orchestrator's ThreadPoolExecutor. Default `3` on 16 GB hosts; auto-tunes from host RAM/cores. The single biggest win — prevents the kernel panic class entirely.
2. **Resource preflight probe — `ai-eng host probe`** runs `vm_stat` + `sysctl hw.memsize` + `sysctl hw.ncpu` and emits `host_capacity` framework event. Skills consult the probe BEFORE dispatching a wave; degrade to serial when `memory_pressure ≥ 50%` or `swap_used_pct ≥ 20%`.
3. **Stack context pre-resolution in Phase 0** — manifest.yml is read ONCE in Phase 0; resolved JSON propagates as `STACK_CONTEXT=…` in every agent dispatch prompt. Eliminates 12+ redundant `Read` tool calls per autopilot run plus their downstream hook firings.
4. **Stale "x3" claim correction** — `.claude/agents/ai-autopilot.md:3` says "verify+guard+review x3" but the canonical contract at `phase-quality.md:3` mandates single round. The contradiction can let an LLM interpret license for 3 rounds × 16 agents = 48 invocations. Hard-correct the description to match the canonical contract.
5. **Hook hot-path budget enforcement** — Module-level LRU cache in `prompt-injection-guard.py` for IOC + decision-store; batched NDJSON writes in `instinct-observe.py` (flush on SubagentStop or every N calls); `runtime-stop.py` convergence check gated by mtime-based skip. Pre-tool-use hooks measured: combined `<200 ms` for a Bash/Edit/Write call.
6. **Deterministic spec shape validation + plan DAG construction** — `ai-eng spec verify --sections` checks Markdown section presence in 20 lines of Python; `ai-eng plan dag-build` parses sub-spec `exports:/imports:` YAML and emits a DAG without LLM. Phase 3 (ORCHESTRATE) calls the script first; LLM is invoked only when conflicts cannot be resolved by import graph alone.
7. **Runtime rotation wired to SessionEnd** — `runtime_rotate.py` already implements 7-day / 30-day / 10K-line retention but is uncalled. Wire it to `.claude/settings.json` `SessionEnd` event with a 1-hour throttle. Prevents `runtime/tool-outputs/` from accumulating MB across long autopilot runs.
8. **NDJSON + state.db retention enforcement** — `framework-events.ndjson` rotates at the lesser of 100k lines or 50 MB via `ai-eng maintenance reset-events --auto` invoked from `SessionEnd`. `state.db` `VACUUM` runs on `SessionEnd` when `auto_vacuum=INCREMENTAL` reports free pages > 1000.
9. **Tunables surface expansion + CLAUDE.md reconciliation** — Document `AIENG_MAX_WAVE_AGENTS`, `AIENG_HOST_PREFLIGHT_MIN_FREE_MB`, `AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT`, `AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_NDJSON_MAX_LINES`. Fix `AIENG_TOOL_OFFLOAD_BYTES` docs vs code discrepancy (4096 documented, 16384 implemented).

**Scope:** single branch `spec-135/framework-performance-hardening`, continuation work. Hard-rename per Constitution §13.3, Conventional Commits per §13.6, single-round quality loop per §13.5.

**Quality stamp at delivery:** every milestone passes its `§10.x` anchor + a new `tests/architecture/test_concurrency_budgets.py` + `tests/integration/test_host_preflight.py` + `tests/unit/hooks/test_hot_path_budget.py`.

---

## 2. Scope Boundary

### In scope (this brief / this PR)

| Item | Reason |
|------|--------|
| `AIENG_MAX_WAVE_AGENTS` env + manifest knob with auto-tune from host capacity | P1 — single biggest win, prevents kernel panic class |
| `ai-eng host probe` CLI command + `host_capacity` framework event | P2 — observability + degradation trigger |
| Phase-0 stack context resolver + JSON propagation in dispatch prompts | P3 — eliminates redundant manifest reads |
| Stale "x3" claim correction in `.claude/agents/ai-autopilot.md:3` | P4 — correctness/safety |
| `prompt-injection-guard.py` IOC + decision-store LRU cache | P5 — hottest hook on Edit/Write/Bash path |
| `instinct-observe.py` batched write mode | P6 — 2× write reduction per agent |
| `runtime-stop.py` convergence-skip on Stop-cascade within 30s | P7 — reduces ruff/pytest re-runs |
| `runtime_rotate.py` wired to `SessionEnd` hook with 1-hour throttle | P8 — closes growth loop |
| `framework-events.ndjson` automatic rotation on `SessionEnd` | P9 — Article-III source-of-truth stays bounded |
| `ai-eng spec verify --sections` Python validator | P10 — replaces LLM section-presence check |
| `ai-eng plan dag-build` Python DAG constructor | P11 — replaces LLM Phase-3 reasoning for the 90% case |
| `commit_compose.py --desc` forced from plan task title | P12 — eliminates per-commit LLM call |
| `pr_body_compose.py` requires spec `summary:` frontmatter | P13 — eliminates per-PR LLM call when spec has summary |
| ThreadPoolExecutor `max_workers` cap (Wave 2 gate orchestrator) | P14 — caps subprocess parallelism alongside agent parallelism |
| CLAUDE.md tunables documentation reconciliation | P15 — closes drift between docs and code |
| Cross-IDE hook wiring parity for M6 across `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json` | P23 — three active runtime surfaces declared in `manifest.yml surfaces.enabled` |
| New tests under `tests/architecture/`, `tests/integration/`, `tests/unit/hooks/` | TDD §10.5 |
| CHANGELOG row per behavioral change + BREAKING CHANGES section | Constitution §13.3 + §13.6 |

### Out of scope (deferred to future briefs)

| Item | Why deferred |
|------|--------------|
| Reducing the total skill count (54) or agent count (24) | Scope vs `skills-agents-excellence-v2-brief.md` (orphan surfacing + naming). Different brief. |
| Adopting a different LLM provider or local-only mode | Architectural; out-of-scope for performance hardening |
| Switching from Claude CLI to a custom orchestration loop | Out-of-scope; preserves existing subprocess contract |
| Distributed orchestration / remote agents (run on cluster) | Out-of-scope; this is single-host performance hygiene |
| Replacing `/ai-autopilot` Phase architecture | Out-of-scope; this brief caps concurrency, doesn't redesign phases |
| Removing the auditing layer (framework-events, state.db) | Out-of-scope; audit chain is Constitution §13 hard rule |
| Re-architecting Hexagonal layer (§10.8) | Out-of-scope; perf hardening is layer-respectful |
| Per-spec custom concurrency budgets | YAGNI §10.2 — single global cap with auto-tune covers the 95% case |
| Real-time pressure-based dynamic re-throttling mid-wave | YAGNI §10.2 — preflight check before wave start is sufficient |
| `opencode` and `cursor` hook wiring | Both surfaces are declared in `manifest.yml surfaces.enabled` but their mirror directories (`.opencode/`, `.cursor/`) **do not exist on disk** at the time of writing. Defer wiring to the spec that materializes those mirrors. Skill-body mirrors (M1, M3, M4, M8) will appear there automatically once `scripts/sync_mirrors/core.py` writes them. |
| `github-copilot` runtime SessionEnd wiring | `.github/hooks/` is a git-lifecycle surface, not a runtime conversational surface. There is no Copilot equivalent of `SessionEnd` to wire. M6 is N/A for Copilot. |

---

## 3. Diagnostic Snapshot — Current State

### 3.1 The incident — what the kernel actually reported

The trigger for this brief is real, not hypothetical. From the macOS panic report:

```
panic(cpu 1 caller …): userspace watchdog timeout:
  no successful checkins from WindowServer (1 induced crashes) in 171 seconds
Compressor Info: 69% of compressed pages limit (OK) and
                 100% of segments limit (BAD) with 42 swapfiles and OK swap space
RELEASE_ARM64_T6000   # Apple M1 Pro
```

Translated: the macOS memory compressor was saturated (100% segments — BAD), 42 swapfiles existed (healthy systems run 1–5), WindowServer (the UI server) blocked waiting for swap I/O for 171s, the watchdog forced a panic to reboot. No hardware failure. No third-party kext involvement. Pure software-induced resource starvation.

The incident occurred during a `/ai-autopilot` or `/ai-build` invocation. The hypothesis under investigation: ai-engineering's orchestrators are the proximate cause.

### 3.2 Parallel agent dispatch — no concurrency caps

The audit found four uncapped parallel-dispatch sites:

**3.2.1 — `/ai-autopilot` Phase 2 (DEEP PLAN): N parallel agents per sub-spec, NO CAP.**

- Evidence: `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md:30`
  > "Dispatch all agents in parallel (parallel in Claude Code, sequential in other IDEs). Each agent receives a self-contained prompt…"
- Evidence: `.claude/agents/ai-autopilot.md:24`
  > "Dispatch N parallel agents for deep codebase exploration and planning"
- **Cap status:** **NONE**. A spec with 10 sub-specs fires 10 simultaneous Claude heavy-model processes each loading the codebase context. On a 16 GB M1 Pro, this alone can exhaust resident memory.

**3.2.2 — `/ai-autopilot` Phase 4 (IMPLEMENT): per-wave parallel build agents, NO CAP.**

- Evidence: `.claude/skills/ai-autopilot/handlers/phase-implement.md:47`
  > "For each non-blocked sub-spec in the wave, dispatch the build agent with a fresh context … All agents in the wave dispatch in parallel. They do not share context with each other."
- **Cap status:** **NONE**. If Wave 1 contains 6 sub-specs, 6 Claude processes spawn simultaneously, each potentially modifying files, each triggering hook firings on every Edit/Write.

**3.2.3 — Policy orchestrator `ThreadPoolExecutor`: max_workers = checker count, NO EXTERNAL CAP.**

- Evidence: `src/ai_engineering/policy/orchestrator.py:489`
  > `max_workers = max(1, len(checkers))`
- Evidence: `src/ai_engineering/policy/orchestrator.py:1209`
  > `max_workers = max(1, len(spec_list))`
- **Cap status:** **NONE**. Each "checker" can itself spawn a heavy subprocess (gitleaks, ruff, ty, pytest-smoke, validate). 5 local checkers run truly in parallel.

**3.2.4 — Stale "x3" claim — possible misinterpretation as 3 quality rounds.**

- Evidence: `.claude/agents/ai-autopilot.md:3`
  > "runs quality convergence loops (verify+guard+review x3)"
- Evidence (canonical): `.claude/skills/ai-autopilot/handlers/phase-quality.md:3`
  > "**Contract**: single round, fail-loud — spec-131 D-131-05"
- **Risk:** An LLM reading the agent description header could interpret "x3" as license for 3 quality rounds instead of 1. Each round dispatches Verify + Guard + Review = 3 simultaneous (with Review fanning out to 9 specialists). 3 rounds × 16 invocations = 48 agent invocations for a single autopilot quality phase.

**3.2.5 — Cumulative agent count for `/ai-autopilot` N=6 sub-specs, 2 waves:**

| Phase | Agents launched | Parallel? |
|---|---|---|
| Phase 2 (Deep Plan) | 6 × (Explore+Plan) = 12 | Yes, all at once |
| Phase 4 Wave 1 (Build) | 3 Build agents | Yes |
| Phase 4 Wave 2 (Build) | 3 Build agents | Yes |
| Phase 4 wave-end Guard | 2 × 1 Guard agent | Sequential per wave |
| Phase 5 Verify + Guard + Review | 3 agents | Yes |
| Phase 5 Review (--full) | 9 specialist sub-agents | Yes within Review |
| Phase 5 Review validator | 1 agent | Sequential |
| **Total upper bound** | **~33+ agent invocations** | — |

A larger spec (10 sub-specs, 3 waves) reaches 50+ invocations. **No single variable or manifest field caps this total.**

### 3.3 Worktree claim is phantom; venv mode caused real friction

- Evidence: `.claude/skills/ai-build/SKILL.md:3`
  > "dispatches the build agent in an isolated worktree"
- Evidence: `.claude/skills/_shared/execution-kernel.md:13`
  > "dispatch ONE specialized agent in a fresh context window. Never let an agent carry context across tasks -- isolation is the point."

Search for `git worktree add` in `.claude/skills/`, `.claude/agents/`, and `src/ai_engineering/` returns no actual invocation. The "isolated worktree" language refers to agent-context isolation (fresh Claude invocation), not filesystem worktree isolation. The skill description at `ai-build/SKILL.md:3` is misleading.

But filesystem worktrees ARE created elsewhere — and were observed to cause real performance damage:

- Evidence: `.ai-engineering/contexts/python-env-modes.md:6`
  > "worktree creation under venv triggered a multi-minute per-cwd .venv re-install"

And no cleanup path exists:

- Evidence: `.ai-engineering/scripts/runtime_rotate.py:72`
  > `def _rotate_autopilot(now: float)` — calls `shutil.rmtree(entry)` on stale `runtime/autopilot/sub-*` dirs only. No `git worktree remove` invocation in any script in the framework.

### 3.4 Hook hot-path cost — the per-tool-call tax

11 canonical hook events fire on every session lifecycle event. The audit measured the heaviest:

**3.4.1 — `prompt-injection-guard.py` (PreToolUse on Bash/Write/Edit/MultiEdit):**

- Evidence: `.ai-engineering/scripts/hooks/prompt-injection-guard.py:1`
  > "Blocks CRITICAL injection matches (exit 2), warns on HIGH matches (exit 0). Applies to Bash, Write, Edit, and MultiEdit tools."
- File size: 38 KB, 988 lines.
- Behavior: loads IOC catalog (`.ai-engineering/iocs.json`) + parses `decision-store.json` ON EVERY hook firing.
- Impact: a build agent making 50 Edit calls causes 50 IOC catalogue loads.

**3.4.2 — `auto-format.py` (PostToolUse on Edit/Write/MultiEdit):**

- Evidence: `.ai-engineering/scripts/hooks/auto-format.py:66-68`
  > `subprocess.run(cmd, capture_output=True, timeout=_FORMATTER_TIMEOUT, cwd=str(project_root))` where `_FORMATTER_TIMEOUT = 15`.
- Impact: spawns ruff / prettier / gofmt subprocess on every file edit. A build agent modifying 5 files triggers 5 formatter subprocesses (concurrent if the agent edits in parallel).

**3.4.3 — `runtime-stop.py` (Stop event, fires per agent including SubagentStop cascade):**

- Evidence: `.ai-engineering/scripts/hooks/runtime-stop.py:321-322`
  > `result: ConvergenceResult = check_convergence(project_root, fast=True)`
- Behavior: `check_convergence` invokes ruff + pytest-smoke at every Stop.
- Impact: for a 12-agent Phase 2, convergence check fires up to 12 times in quick succession at the end of the phase. Each fires a ruff + pytest subprocess.

**3.4.4 — `instinct-observe.py` (BOTH PreToolUse AND PostToolUse):**

- Evidence: `.claude/settings.json` (PreToolUse and PostToolUse both wire `instinct-observe.py`)
- Behavior: appends to `.ai-engineering/state/observation-events.ndjson` on every tool call.
- Impact: a build agent making 100 tool calls causes 200 NDJSON file appends.

### 3.5 Mirror sync is already deterministic (good news)

- Evidence: `scripts/sync_mirrors/core.py:23-80` — pure-Python. No subprocess calls.
- Evidence: `grep -n "subprocess" scripts/sync_mirrors/core.py` returns 0 hits.
- Evidence: `.claude/settings.json` does NOT wire mirror sync into any hook.
- **Verdict:** mirror sync is correctly deterministic and out of the hot path. **No action needed.**

### 3.6 State growth — bounded by retention policy that does not fire

| Artefact | Current size | Retention policy | Triggered automatically? |
|----------|--------------|------------------|--------------------------|
| `.ai-engineering/state/state.db` | 196 KB | `auto_vacuum=INCREMENTAL` | DB-level only; no `VACUUM` schedule |
| `.ai-engineering/state/framework-events.ndjson` | 249 KB, 479 lines | `ai-eng maintenance reset-events` (manual) | **NO** — no hook calls it |
| `.ai-engineering/runtime/tool-outputs/` | grows per offload | 7-day TTL in `runtime_rotate.py` | **NO** — `runtime_rotate.py` is uncalled |
| `.ai-engineering/runtime/autopilot/sub-*/` | per sub-spec | 30-day TTL in `runtime_rotate.py` | **NO** — same |
| `.ai-engineering/runtime/tool-history.ndjson` | grows | 10k lines / 5 MB cap | **NO** — same |

- Evidence: `src/ai_engineering/cli_commands/maintenance.py:440`
  > "Archive framework-events.ndjson and seed a fresh chain (spec-114 G-5)."
- Evidence (no auto-trigger): no hook in `.claude/settings.json` references `reset-events` or `runtime_rotate`.

`runtime_rotate.py` has the correct retention policies, but **it is not connected to any event**.

### 3.7 Tunable surface gap

The audit enumerated five documented tunables in `CLAUDE.md:162-166`:

| Variable | CLAUDE.md default | Actual code default | Controls |
|---|---|---|---|
| `AIENG_TOOL_OFFLOAD_BYTES` | 4096 | **16384** (discrepancy!) | Threshold for offloading tool output |
| `AIENG_LOOP_WINDOW` | 6 | 6 | Loop detection window |
| `AIENG_RALPH_MAX_RETRIES` | 5 | 5 | Ralph loop reinjection cap |
| `AIENG_RALPH_BLOCK` | 0 | 0 | Convergence-failure reinjection mode |
| `AIENG_HOOK_INTEGRITY_MODE` | enforce | enforce | sha256 mismatch handling |

- Evidence (CLAUDE.md): `CLAUDE.md:162`
- Evidence (code): `.ai-engineering/scripts/hooks/_lib/runtime_state.py:93`
  > `TOOL_OFFLOAD_BYTES = _env_int("AIENG_TOOL_OFFLOAD_BYTES", 16384, ceiling=8 * 1024 * 1024)`

**Gap:** NONE of the five tunables caps concurrency, memory, or wave fan-out. The control surface for "how many agents may run at once" does not exist.

### 3.8 Determinism opportunities — LLM calls that should be scripts

The audit identified 12 candidates where an LLM is invoked for work a deterministic script could do equally well. Highest-leverage:

| # | Current LLM call | Citation | Proposal | Risk |
|---|---|---|---|---|
| F.1 | Manifest stack read per agent | `.claude/agents/ai-build.md:27` | Pre-resolve in Phase 0; pass JSON | Low |
| F.2 | Commit `<DESC>` placeholder | `.claude/skills/ai-commit/SKILL.md:63` | Force `--desc` from task title | Low |
| F.3 | PR body `--bullets-prompt` | `.claude/skills/ai-pr/SKILL.md:85` | Require spec `summary:` frontmatter | Low |
| F.4 | Spec section validation | `.claude/skills/ai-brainstorm/SKILL.md:57` + `.ai-engineering/contexts/spec-schema.md:46` | Python `ai-eng spec verify --sections` | Low |
| F.9 | Plan DAG construction | `.claude/skills/ai-autopilot/SKILL.md:50` | Parse `exports:/imports:` YAML | Medium |
| F.12 | Per-task Guard advisory | `.claude/skills/ai-build/SKILL.md:25` | Deterministic decision-store lookup; LLM only on novel question | Medium |

(F.5 risk-accept lookup, F.6 decision queries, F.7 mirror sync are **already** deterministic — no action.)

### 3.9 Numeric snapshot

| Metric | Value | Source |
|---|---|---|
| Skills | 54 | `ls .claude/skills/ \| wc -l` |
| Agents (first-class + sub) | 24 | `ls .claude/agents/ \| wc -l` |
| Hook scripts | 23 | `ls .ai-engineering/scripts/hooks/*.py \| wc -l` |
| Hook events wired | 11 | `.claude/settings.json` |
| Worst-case hook firings per tool call | 8 (4 Pre + 4 Post) | `.claude/settings.json` |
| `state.db` size | 196 KB | `ls -lh` |
| `framework-events.ndjson` size / lines | 249 KB / 479 | `ls -lh` + `wc -l` |
| `prompt-injection-guard.py` size / lines | 38 KB / 988 | `ls -lh` + `wc -l` |
| `ThreadPoolExecutor` Wave-2 max workers | unbounded (= checker count) | `orchestrator.py:489` |
| `ThreadPoolExecutor` spec dispatch max workers | unbounded (= spec count) | `orchestrator.py:1209` |
| Quality loop max agent invocations (Phase 5) | ~16 | analysis |
| Max autopilot agent invocations (N=6) | ~33+ | analysis |
| Documented tunables capping concurrency | **0** | `CLAUDE.md:162-166` |
| Documented tunables capping memory | **0** | same |

---

## 4. Final Architecture — Target State

### 4.1 Concurrency budget primitive

A single global cap, auto-tuned from host capacity, surfaced as:

```yaml
# .ai-engineering/manifest.yml
performance:
  concurrency:
    max_wave_agents: auto         # auto | <int>
    max_quality_agents: 3         # parallel assessor cap in Phase 5
    max_thread_workers: 4         # ThreadPoolExecutor cap for orchestrator
  preflight:
    enabled: true
    min_free_memory_mb: 2048      # abort dispatch below
    max_memory_pressure_pct: 50   # abort dispatch above
    max_swap_used_pct: 20         # abort dispatch above
```

```bash
# Environment overrides
AIENG_MAX_WAVE_AGENTS=3            # caps Phase 2/4 fan-out
AIENG_MAX_QUALITY_AGENTS=3         # caps Phase 5 assessor count
AIENG_MAX_THREAD_WORKERS=4         # caps orchestrator.py ThreadPoolExecutor
AIENG_HOST_PREFLIGHT_DISABLED=0    # 0 = preflight on, 1 = off
AIENG_HOST_PREFLIGHT_MIN_FREE_MB=2048
AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT=50
```

Auto-tune algorithm (host-aware):

```python
def auto_concurrency_cap(host: HostProbe) -> int:
    # host.total_ram_gb, host.free_ram_gb, host.cores, host.pressure_pct
    if host.pressure_pct >= 50:
        return 1   # serialize when host is already stressed
    by_ram = max(1, host.free_ram_gb // 4)         # ~4 GB headroom per agent
    by_cpu = max(1, host.cores // 2)               # leave cores for OS / IDE
    return min(by_ram, by_cpu, 6)                  # absolute ceiling 6
```

For the trigger machine (16 GB / 8 cores / 8 GB free / 10% pressure): `min(2, 4, 6) = 2`. The kernel-panic incident with 6+ parallel agents simply cannot happen under this cap.

### 4.2 Resource preflight probe — `ai-eng host probe`

New deterministic CLI subcommand:

```bash
$ ai-eng host probe
{
  "total_ram_gb": 16,
  "free_ram_gb": 7.2,
  "cores": 8,
  "pressure_pct": 12,
  "swap_used_pct": 0,
  "platform": "darwin-arm64",
  "ok_to_dispatch": true,
  "recommended_cap": 2
}
```

Implementation (darwin):

```python
def probe_darwin() -> HostProbe:
    free_mem = parse_vm_stat()           # vm_stat -> free + inactive pages
    total_ram = sysctl("hw.memsize") / 1e9
    cores = sysctl("hw.ncpu")
    pressure = compute_pressure(...)      # see Apple Activity Monitor calculation
    swap = parse_sysctl_vm_swapusage()
    return HostProbe(...)
```

Emits `host_capacity` framework event into `state.db` `events` table on every dispatch. Skills consult `probe.ok_to_dispatch` BEFORE Phase 2 / Phase 4 fan-out. When false:
- Emit `host_pressure_warning` event.
- Degrade to serial (cap=1) for the wave.
- Surface a one-line warning to operator: `"Host under pressure (memory_pressure=52%) — running serial."`

### 4.3 Phase-0 stack context resolver

Currently every agent reads `manifest.yml` independently:

- Evidence: `.claude/agents/ai-build.md:27`
  > "Read .ai-engineering/manifest.yml field providers.stacks to determine the project's active stacks."

Target: resolve ONCE in Phase 0, pass as JSON:

```bash
# Phase 0 emits an artefact that downstream phases consume
.ai-engineering/runtime/autopilot/<spec>/stack-context.json
```

Every dispatch prompt includes `STACK_CONTEXT={"stacks": ["python", "typescript"], "test_command": "pytest -q", …}` as a top-level variable. Agents never `Read` `manifest.yml`; they read the variable.

For N=6 sub-specs in Phase 2 + 6 in Phase 4 + 1 each in Phase 5, this eliminates **13 redundant `Read` tool calls**. Each saved `Read` also avoids 8 hook firings (4 Pre + 4 Post).

### 4.4 Hook hot-path budget enforcement

**P5.1 — `prompt-injection-guard.py` module-level cache:**

```python
# Top of file
_IOC_CACHE: tuple[float, dict] | None = None      # (mtime, parsed)
_DECISION_STORE_CACHE: tuple[float, dict] | None = None

def load_iocs() -> dict:
    global _IOC_CACHE
    p = Path(".ai-engineering/iocs.json")
    mtime = p.stat().st_mtime
    if _IOC_CACHE and _IOC_CACHE[0] == mtime:
        return _IOC_CACHE[1]
    data = json.loads(p.read_text())
    _IOC_CACHE = (mtime, data)
    return data
```

Per-process cache: 50 tool calls = 1 disk read (not 50). Invalidated on file mtime change.

**P5.2 — `instinct-observe.py` batched writes:**

Append to in-memory list; flush on:
- 50 events accumulated, OR
- 5 seconds elapsed, OR
- SubagentStop fires for parent process.

NDJSON write count reduces from 200 per agent to ~5 per agent.

**P5.3 — `runtime-stop.py` convergence-skip:**

Convergence checker runs ruff + pytest-smoke. Skip when:
- Last successful convergence check < 30s ago, AND
- No files changed since last check (`git status --short` empty), AND
- Current Stop is a SubagentStop cascade (not a top-level Stop).

### 4.5 Deterministic-first pipeline

Replace LLM with Python where structural:

**P10 — `ai-eng spec verify --sections`:**

```python
REQUIRED_SECTIONS = [
    "## 0", "## 1", "## 2", "## 3", "## 4",
    "## 5", "## 6", "## 7", "## 8", "## 9",
    "## 10", "## 11", "## 12", "## 13",
]
def verify_sections(spec_path: Path) -> list[str]:
    text = spec_path.read_text()
    return [s for s in REQUIRED_SECTIONS if s not in text]
```

20 lines. Replaces the LLM section-presence check in `/ai-brainstorm` SKILL.md:57.

**P11 — `ai-eng plan dag-build`:**

```python
def build_dag(sub_spec_dir: Path) -> WaveDAG:
    deps: dict[str, set[str]] = {}
    for plan in sub_spec_dir.glob("sub-*/plan.md"):
        front = parse_yaml_frontmatter(plan)
        exports = set(front.get("exports", []))
        imports = set(front.get("imports", []))
        deps[plan.parent.name] = imports
    return topo_sort_into_waves(deps)
```

100 lines. Replaces LLM Phase-3 reasoning at `.claude/skills/ai-autopilot/SKILL.md:50` for the 90% case. LLM invoked only when import-graph fails to resolve a conflict (rare).

**P12 — `commit_compose.py --desc` forced:**

`/ai-build`, `/ai-autopilot`, `/ai-pr` always pass `--desc "<plan-task-title>"`. Eliminates the `<DESC>` placeholder LLM call documented at `.claude/skills/ai-commit/SKILL.md:63`.

**P13 — `pr_body_compose.py` requires spec `summary:`:**

`/ai-brainstorm` spec-schema gains a mandatory `summary:` frontmatter field. `pr_body_compose.py` always reads from this; never invokes `--bullets-prompt` (eliminates LLM call at `.claude/skills/ai-pr/SKILL.md:85`).

### 4.6 Runtime rotation wired to lifecycle

`.claude/settings.json` gains:

```json
{
  "hooks": {
    "SessionEnd": [
      { "type": "command", "command": "${AIENG_SCRIPTS}/runtime-session-end.py", "timeout": 5 },
      { "type": "command", "command": "${AIENG_SCRIPTS}/runtime-rotate-throttled.py", "timeout": 30 }
    ]
  }
}
```

New script `runtime-rotate-throttled.py`:

```python
LAST_RUN_FILE = Path(".ai-engineering/runtime/.rotate-lastrun")
THROTTLE_SEC = 3600   # 1 hour

if LAST_RUN_FILE.exists():
    if time.time() - LAST_RUN_FILE.stat().st_mtime < THROTTLE_SEC:
        sys.exit(0)
subprocess.run([sys.executable, "-m", "ai_engineering.scripts.runtime_rotate"], check=False)
LAST_RUN_FILE.touch()
```

Runtime artefacts now have a guaranteed retention loop.

### 4.7 NDJSON + state.db retention

`runtime-session-end.py` gains:

```python
# When framework-events.ndjson exceeds 100k lines OR 50 MB → archive + restart chain
NDJSON_MAX_LINES = int(os.getenv("AIENG_NDJSON_MAX_LINES", "100000"))
NDJSON_MAX_BYTES = int(os.getenv("AIENG_NDJSON_MAX_BYTES", str(50 * 1024 * 1024)))

if should_rotate_ndjson(path, NDJSON_MAX_LINES, NDJSON_MAX_BYTES):
    subprocess.run(["ai-eng", "maintenance", "reset-events", "--auto"], check=False)

# state.db incremental vacuum when free pages > 1000
if free_page_count(db) > 1000:
    conn.execute("PRAGMA incremental_vacuum(1000)")
```

---

## 5. Evidence Catalog — Issues by ID

Format: `P<N> — <title> (SEVERITY) — <citation>`

- **P1 — Phase 2 uncapped fan-out (CRITICAL)** — `.claude/skills/ai-autopilot/handlers/phase-deep-plan.md:30`; N parallel explore+plan agents per sub-spec, no cap. Direct cause of kernel-panic class.
- **P2 — Phase 4 uncapped wave fan-out (CRITICAL)** — `.claude/skills/ai-autopilot/handlers/phase-implement.md:47`; per-wave N build agents in parallel, no cap.
- **P3 — Agent description uncapped claim (HIGH)** — `.claude/agents/ai-autopilot.md:24`; "Dispatch N parallel agents …" with no cap-text. Self-reinforcing for any LLM reading the description.
- **P4 — Stale "x3" claim (HIGH — correctness/safety)** — `.claude/agents/ai-autopilot.md:3` vs `.claude/skills/ai-autopilot/handlers/phase-quality.md:3`; the agent description contradicts the canonical contract, opening interpretive license for 3 rounds × 16 agents.
- **P5 — `ThreadPoolExecutor` uncapped (HIGH)** — `src/ai_engineering/policy/orchestrator.py:489` and `:1209`; subprocess-level parallelism uncapped by external policy.
- **P6 — `prompt-injection-guard.py` reloads IOC catalogue every call (HIGH)** — `.ai-engineering/scripts/hooks/prompt-injection-guard.py:1`; 38 KB JSON parsed per Bash/Write/Edit. With 50 Edits per build agent → 50 reloads.
- **P7 — `auto-format.py` spawns subprocess per edit (MEDIUM)** — `.ai-engineering/scripts/hooks/auto-format.py:66-68`; ruff/prettier/gofmt 15s timeout per Edit/Write/MultiEdit.
- **P8 — `runtime-stop.py` runs convergence on every Stop (HIGH)** — `.ai-engineering/scripts/hooks/runtime-stop.py:321-322`; SubagentStop cascade can fire 12 convergence checks (ruff + pytest-smoke) in seconds at end of Phase 2.
- **P9 — `instinct-observe.py` writes on both Pre+Post (MEDIUM)** — `.claude/settings.json`; 200 NDJSON appends per 100-tool-call agent.
- **P10 — Worktree claim is phantom (MEDIUM — accuracy)** — `.claude/skills/ai-build/SKILL.md:3`; "isolated worktree" language is misleading. No `git worktree add` in any skill or agent.
- **P11 — venv mode caused real multi-minute friction (MEDIUM — historical)** — `.ai-engineering/contexts/python-env-modes.md:6`; documented per-cwd re-install pain.
- **P12 — `runtime_rotate.py` uncalled (MEDIUM)** — `.ai-engineering/scripts/runtime_rotate.py:72`; retention policy exists but no hook triggers it.
- **P13 — `framework-events.ndjson` rotation manual only (MEDIUM)** — `src/ai_engineering/cli_commands/maintenance.py:440`; `reset-events` command exists but no hook invokes it.
- **P14 — `AIENG_TOOL_OFFLOAD_BYTES` docs/code drift (LOW — documentation)** — `CLAUDE.md:162` says 4096; `.ai-engineering/scripts/hooks/_lib/runtime_state.py:93` defaults to 16384.
- **P15 — No concurrency tunable surface (CRITICAL)** — `CLAUDE.md:162-166`; zero env var caps wave fan-out, agent count, or memory budget.
- **P16 — No host preflight probe (HIGH)** — search for `host_capacity`, `memory_check`, `preflight` returns zero matches across `.ai-engineering/`, `src/`, `.claude/`. No skill consults host before dispatching.
- **P17 — No SubagentStop concurrent-agent counter (LOW)** — `.ai-engineering/scripts/hooks/runtime-subagent-stop.py:95`; records completion, not peak concurrency. Missing observability for the very metric that matters.
- **P18 — Per-agent manifest reads (MEDIUM)** — `.claude/agents/ai-build.md:27`; every dispatched agent reads `manifest.yml` independently. N redundant `Read` calls per autopilot run.
- **P19 — `commit_compose.py <DESC>` placeholder LLM call (LOW)** — `.claude/skills/ai-commit/SKILL.md:63`; one LLM call per commit avoidable when plan task title exists.
- **P20 — `pr_body_compose.py --bullets-prompt` LLM call (LOW)** — `.claude/skills/ai-pr/SKILL.md:85`; one LLM call per PR avoidable when spec carries `summary:`.
- **P21 — `/ai-brainstorm` LLM section validation (LOW)** — `.claude/skills/ai-brainstorm/SKILL.md:57` + `.ai-engineering/contexts/spec-schema.md:46`; structural section presence is a regex, not an LLM judgment.
- **P22 — Phase 3 DAG construction LLM-driven (MEDIUM)** — `.claude/skills/ai-autopilot/SKILL.md:50`; the orchestrator reasons about file-overlap matrix and import-chain graph in LLM context while Phase 2 already produces structured `exports:/imports:` YAML.
- **P23 — `runtime_rotate.py` wiring missing across all 3 active runtime surfaces (MEDIUM — cross-IDE)** — `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json` each lack a SessionEnd-equivalent invocation of `runtime_rotate.py`. The canonical script exists at `.ai-engineering/scripts/hooks/` but no hook config in any active IDE references it. Manifest declares 6 surfaces in `surfaces.enabled` ([.ai-engineering/manifest.yml](.ai-engineering/manifest.yml)); `.opencode/` and `.cursor/` directories are absent on disk — wiring deferred for those until the mirrors materialize.

---

## 6. Roadmap — 9 Milestones

Each milestone names its principle anchor(s), the **Why**, **What**, **Done when**, **Tests**.

### M1 · Concurrency budget primitive [§10.1 KISS · §10.2 YAGNI · §10.7 Clean Code]

**Why.** P1, P2, P3, P5, P15 — the kernel-panic root cause. No cap exists today; any wave with high N can starve the host.

**What.**
- Add `AIENG_MAX_WAVE_AGENTS` env var + manifest knob `performance.concurrency.max_wave_agents`.
- Phase 2 (`phase-deep-plan.md`): wrap fan-out in a deterministic batching loop — dispatch in batches of `cap`, await each batch.
- Phase 4 (`phase-implement.md`): same batching for wave dispatch.
- Phase 5 (`phase-quality.md`): cap is `min(3, AIENG_MAX_QUALITY_AGENTS)` — already low; just make explicit.
- `src/ai_engineering/policy/orchestrator.py:489` and `:1209`: replace `max_workers = max(1, len(checkers))` with `min(len(checkers), max_thread_workers)`.
- Update `.claude/agents/ai-autopilot.md:24` text to reflect cap.

**Done when.**
- [ ] `AIENG_MAX_WAVE_AGENTS=2` causes Phase 2 to dispatch 2-at-a-time (verifiable via `framework_event kind=wave_dispatch_batched`).
- [ ] `manifest.yml` knob respected; env overrides manifest.
- [ ] `tests/architecture/test_concurrency_budgets.py` GREEN with 6 scenarios (env / manifest / default-auto / explicit-int / cap-of-1-serial / cap-larger-than-N).
- [ ] `tests/unit/policy/test_orchestrator_max_workers.py` GREEN.

### M2 · Resource preflight probe [§10.6 SDD · §10.8 Hexagonal — adapter port]

**Why.** P16 — no host-awareness in the framework. The kernel panic was reachable because dispatch happened blind.

**What.**
- New module `src/ai_engineering/host/probe.py` with `HostProbe` dataclass + `probe()` function.
- darwin adapter: `vm_stat`, `sysctl hw.memsize`, `sysctl hw.ncpu`, `sysctl vm.swapusage`.
- linux adapter: `/proc/meminfo`, `/proc/cpuinfo`, `/proc/swaps`.
- New CLI subcommand `ai-eng host probe` emits JSON.
- New framework event `host_capacity` written to `state.db events`.
- `/ai-autopilot` Phase 0 + `/ai-build` step 0 consult `probe()` before dispatch.
- When `probe.ok_to_dispatch == False`: emit `host_pressure_warning` event; degrade to cap=1.

**Done when.**
- [ ] `ai-eng host probe` returns valid JSON on darwin and linux.
- [ ] `tests/integration/test_host_preflight.py` GREEN with 4 scenarios (healthy host / high pressure / low free RAM / single core).
- [ ] Phase 0 emits `host_capacity` event verifiable in `framework-events.ndjson`.
- [ ] Hexagonal layer test: `tests/architecture/test_layer_isolation.py` confirms `host/` is a port, not domain.

### M3 · Phase-0 stack context pre-resolution [§10.4 DRY]

**Why.** P18 — 13+ redundant `Read` calls per autopilot run. Each saved `Read` also saves 8 hook firings.

**What.**
- Phase 0 reads `manifest.yml` once, computes resolved stack list + test command + format command.
- Writes `.ai-engineering/runtime/autopilot/<spec>/stack-context.json`.
- Every Phase 2 / Phase 4 / Phase 5 dispatch prompt includes the resolved JSON as `STACK_CONTEXT=...`.
- Agent description files (`ai-build.md:27`, etc.) updated to instruct: "Read `STACK_CONTEXT` from dispatch prompt — do NOT re-read manifest.yml."

**Done when.**
- [ ] N=6 autopilot run produces zero `Read` tool calls on `manifest.yml` from build/explore/plan agents (verifiable in `tool-history.ndjson`).
- [ ] `tests/integration/test_stack_context_propagation.py` GREEN.

### M4 · Stale "x3" claim correction [§10.7 Clean Code · §13 hard rules]

**Why.** P4 — single-character correctness fix that closes a 32-agent interpretive blast radius.

**What.**
- Edit `.claude/agents/ai-autopilot.md:3`: change "verify+guard+review x3" to "verify+guard+review (single round, fail-loud)".
- Re-mirror to `.codex/`, `.gemini/`, `.github/` via `scripts/sync_mirrors/core.py`.
- Add `tests/architecture/test_agent_description_contract.py` enforcing: no occurrence of "x3", "×3", "3 rounds" in any agent description that conflicts with `phase-quality.md:3` single-round contract.

**Done when.**
- [ ] `grep -rE "(verify\\+guard\\+review x3|verify\\+guard\\+review ×3)" .claude/ .codex/ .gemini/ .github/` returns 0 matches.
- [ ] `tests/architecture/test_agent_description_contract.py` GREEN.

### M5 · Hook hot-path budget enforcement [§10.1 KISS · §10.5 TDD]

**Why.** P6, P7, P8, P9 — hooks fire on every tool call and currently do per-call I/O.

**What.**
- `prompt-injection-guard.py`: module-level LRU cache for IOC catalogue + decision-store, invalidated on mtime change.
- `instinct-observe.py`: batched writes (50-event buffer / 5s flush / SubagentStop flush).
- `runtime-stop.py`: skip convergence check when (a) last check < 30s ago AND (b) no git changes AND (c) Stop is SubagentStop cascade.
- `auto-format.py`: skip formatter when file mtime within `_AUTOFORMAT_DEBOUNCE_SEC` (default 1s) of last format.
- New env: `AIENG_HOOK_CACHE_TTL_SEC` (default 300), `AIENG_HOOK_BUDGET_PROFILE` (0/1 — log timing to NDJSON).

**Cross-IDE note.** Hook scripts live canonically under `.ai-engineering/scripts/hooks/` and are invoked verbatim by every active runtime surface via the `AIENG_HOOK_ENGINE` adapter pattern: Claude Code is the default; Codex sets `AIENG_HOOK_ENGINE=codex` and routes through [codex-hook-bridge.py](.ai-engineering/scripts/hooks/codex-hook-bridge.py); Gemini sets `AIENG_HOOK_ENGINE=gemini`. **M5 requires NO per-IDE wiring change** — the optimizations land once in the canonical scripts and propagate to all three engines automatically. Validate by running the timing test under each engine.

**Done when.**
- [ ] `prompt-injection-guard.py` measured: < 50ms p95 on cached call (vs ~300ms cold).
- [ ] `instinct-observe.py` measured: < 5ms p95 (buffered).
- [ ] `tests/unit/hooks/test_hot_path_budget.py` GREEN — measures actual hook timing under load with `AIENG_HOOK_ENGINE` set to each of `(default-claude, codex, gemini)`.
- [ ] `tests/unit/hooks/test_canonical_events_count.py` still GREEN (no event change).

### M6 · Runtime rotation wired to SessionEnd — three active runtime surfaces [§10.1 KISS · §10.4 DRY]

**Why.** P12, P13, P23 — retention policies exist but are unreachable on any IDE; wiring must reach all 3 active runtime surfaces or the rotation loop stays partial.

**What.**
- New script [.ai-engineering/scripts/hooks/runtime-rotate-throttled.py](.ai-engineering/scripts/hooks/runtime-rotate-throttled.py) (canonical, IDE-agnostic).
- Throttle: 1 hour minimum between runs (touch `.ai-engineering/runtime/.rotate-lastrun`).
- Update `runtime-session-end.py` to invoke NDJSON rotation when size/lines exceed thresholds.
- Add `state.db PRAGMA incremental_vacuum(1000)` when free pages > 1000.
- **Cross-IDE wiring (3 active surfaces):**
  | Surface | File | Event | Engine flag |
  |---------|------|-------|-------------|
  | claude-code | [.claude/settings.json](.claude/settings.json) | `SessionEnd` | (default) |
  | codex | [.codex/hooks.json](.codex/hooks.json) | `SessionEnd` (re-routed via [codex-hook-bridge.py](.ai-engineering/scripts/hooks/codex-hook-bridge.py)) | `AIENG_HOOK_ENGINE=codex` |
  | gemini-cli | [.gemini/settings.json](.gemini/settings.json) | Gemini end-of-session event (mapping verified during implementation — likely `AfterAgent` or session-stop equivalent) | `AIENG_HOOK_ENGINE=gemini` |
- **github-copilot:** N/A. `.github/hooks/hooks.json` is a git-lifecycle surface; Copilot has no runtime SessionEnd. Document the carve-out in the wiring test fixture.
- **opencode / cursor:** deferred — `.opencode/` and `.cursor/` directories do not exist. When those mirrors materialize in a separate spec, add equivalent wiring there.

**Done when.**
- [ ] A 100-tool-call session under **each** of `claude-code`, `codex`, `gemini-cli` triggers `runtime_rotate.py` execution at the respective SessionEnd-equivalent event.
- [ ] Throttle correctly skips a SessionEnd within 1 hour of last rotation (verified per engine).
- [ ] NDJSON rotates when `AIENG_NDJSON_MAX_LINES=100` test threshold is crossed.
- [ ] `tests/integration/test_runtime_rotation_lifecycle.py` GREEN — parametrized across the 3 engines.
- [ ] `tests/architecture/test_hook_wiring_parity.py` GREEN — asserts M6 wiring exists in all 3 active runtime configs (or is explicitly waived in fixture for Copilot).

### M7 · Deterministic spec verify + plan DAG [§10.6 SDD · §10.5 TDD]

**Why.** P21, P22 — replace LLM judgment with regex / parse where structural.

**What.**
- New CLI: `ai-eng spec verify --sections <path>` returns missing section headers.
- New CLI: `ai-eng plan dag-build <subdir>` returns wave assignment JSON.
- `/ai-brainstorm` calls `ai-eng spec verify --sections` BEFORE invoking the LLM validation pass (short-circuit on missing structure).
- `/ai-autopilot` Phase 3 calls `ai-eng plan dag-build` FIRST; LLM only when the script returns conflicts.

**Done when.**
- [ ] `ai-eng spec verify --sections fixtures/spec-missing-glossary.md` returns `["## 13"]`.
- [ ] `ai-eng plan dag-build fixtures/sub-specs-3-overlap/` returns valid topological JSON.
- [ ] `tests/unit/cli/test_spec_verify.py` + `test_plan_dag_build.py` GREEN.
- [ ] `/ai-brainstorm` measured: LLM section-validation pass skipped on missing sections.

### M8 · Determinism final-mile (commit + PR) [§10.4 DRY]

**Why.** P19, P20 — two avoidable LLM calls per spec-shipping cycle.

**What.**
- Update `/ai-commit`, `/ai-build`, `/ai-autopilot`, `/ai-pr` to pass `commit_compose.py --desc "<plan-task-title>"` always.
- Add mandatory `summary:` field to spec-schema (`/ai-brainstorm` blocks approval without it).
- Update `/ai-pr` to call `pr_body_compose.py` without `--bullets-prompt`.

**Done when.**
- [ ] No invocation of `commit_compose.py` without `--desc` in any skill.
- [ ] No invocation of `pr_body_compose.py --bullets-prompt` in any skill.
- [ ] `spec-schema.md` `summary:` field mandatory; validator rejects spec missing it.
- [ ] `tests/unit/skills/test_no_residual_llm_compose.py` GREEN — greps skills for forbidden invocations.

### M9 · CLAUDE.md reconciliation + tunables documentation [§10.7 Clean Code]

**Why.** P14, P15 — the documentation drift undermines all preceding milestones.

**What.**
- Update `CLAUDE.md` "Runtime Layer Tunables" section to add all new env vars (`AIENG_MAX_WAVE_AGENTS`, `AIENG_MAX_QUALITY_AGENTS`, `AIENG_MAX_THREAD_WORKERS`, `AIENG_HOST_PREFLIGHT_*`, `AIENG_HOOK_CACHE_TTL_SEC`, `AIENG_NDJSON_MAX_LINES`, `AIENG_NDJSON_MAX_BYTES`, `AIENG_AUTOFORMAT_DEBOUNCE_SEC`).
- Fix `AIENG_TOOL_OFFLOAD_BYTES` default — change `CLAUDE.md:162` from `4096` to `16384` to match code.
- Re-mirror to `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`.
- Add `tests/architecture/test_tunables_docs_match_code.py` (parses CLAUDE.md table, greps code defaults, asserts match).

**Done when.**
- [ ] Every `AIENG_*` env var found in code is documented in `CLAUDE.md`.
- [ ] Every documented `AIENG_*` env var has a matching code default.
- [ ] `tests/architecture/test_tunables_docs_match_code.py` GREEN.

---

## 7. Definition of Done

Single PR (#spec-135) lands with ALL of:

- [ ] **Concurrency cap effective** — `AIENG_MAX_WAVE_AGENTS=2` on the trigger machine causes Phase 2 to dispatch 2 agents at a time, not N. Verified by replaying an N=6 autopilot run with new event `wave_dispatch_batched` showing 3 batches of 2 instead of 1 batch of 6.
- [ ] **Host preflight active** — `ai-eng host probe` returns JSON; `host_capacity` event emitted before every wave; degradation to cap=1 verified by injection test (`AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT=10` on a busy machine).
- [ ] **Manifest reads eliminated from dispatched agents** — `STACK_CONTEXT` propagation reduces redundant `Read` calls to 0 in `tool-history.ndjson` for build/explore/plan agents.
- [ ] **No stale "x3"** — grep returns 0 matches in any committed file.
- [ ] **Hot-path budget met** — p95 hook timing on the trigger machine:
  - `prompt-injection-guard.py` < 50ms (cached)
  - `instinct-observe.py` < 5ms (buffered)
  - `auto-format.py` < 30ms (debounced)
  - `runtime-stop.py` convergence skipped on SubagentStop cascade
- [ ] **Runtime rotation triggers** — `SessionEnd` invokes `runtime-rotate-throttled.py`; NDJSON rotates above thresholds; `state.db` incremental vacuum runs.
- [ ] **Deterministic short-circuits** — `/ai-brainstorm` calls `ai-eng spec verify --sections` first; `/ai-autopilot` Phase 3 calls `ai-eng plan dag-build` first; LLM invoked only when deterministic path returns ambiguity.
- [ ] **No residual avoidable LLM compose calls** — `/ai-commit`, `/ai-pr` always pass `--desc` / read `summary:` frontmatter.
- [ ] **Tunables documented** — every new `AIENG_*` in `CLAUDE.md`; drift test green.
- [ ] **Tests** — every milestone passes:
  - `tests/architecture/test_concurrency_budgets.py` (new — 6 scenarios)
  - `tests/architecture/test_agent_description_contract.py` (new — no stale x3)
  - `tests/architecture/test_tunables_docs_match_code.py` (new — doc/code parity)
  - `tests/architecture/test_hook_wiring_parity.py` (new — M6 wired in `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json` or explicitly waived per surface in fixture)
  - `tests/integration/test_host_preflight.py` (new — 4 scenarios)
  - `tests/integration/test_stack_context_propagation.py` (new)
  - `tests/integration/test_runtime_rotation_lifecycle.py` (new — parametrized across `(default-claude, codex, gemini)`)
  - `tests/unit/hooks/test_hot_path_budget.py` (new — timing measurements per `AIENG_HOOK_ENGINE` value)
  - `tests/unit/cli/test_spec_verify.py` + `test_plan_dag_build.py` (new)
  - `tests/unit/skills/test_no_residual_llm_compose.py` (new)
  - `tests/unit/policy/test_orchestrator_max_workers.py` (new)
- [ ] **CHANGELOG** — `## [Unreleased]` populated: `### Added`, `### Changed`, `### Fixed`, `### BREAKING CHANGES`.
- [ ] **PR `spec-135`** — single branch, no force-push, Conventional Commits per §13.6, all CI green, single-round quality loop per §13.5.
- [ ] **Governance** — `ai-eng audit replay --session <impl-session-id>` shows zero blockers; `gate_findings` table clean for impl session.
- [ ] **Validation on the trigger machine** — operator runs `/ai-autopilot` on a spec with N=8 sub-specs on the same 16 GB M1 Pro that panicked. Memory pressure under `/usr/bin/top -l 1 -s 0 -n 0` stays below 60% throughout the run. No watchdog timeout. No kernel panic. Document the validation in the PR body.

---

## 8. Quality Stamps

| Principle | Anchor | Manifestation in this brief |
|-----------|--------|-----------------------------|
| **KISS** | §10.1 | M1 single global cap; M6 SessionEnd wire-up is one line; M4 single-character fix |
| **YAGNI** | §10.2 | No dynamic mid-wave re-throttle; no per-spec budgets; no telemetry surface that isn't load-bearing |
| **SOLID** | §10.3 | M2 host probe is a port; darwin/linux are adapters (single responsibility per platform) |
| **DRY** | §10.4 | M3 manifest read happens once, not per agent; M8 `commit_compose.py` consumes plan-derived data |
| **TDD** | §10.5 | Every M ships RED tests FIRST; hot-path budget asserted via timing tests, not eye-balling |
| **SDD** | §10.6 | This brief → `/ai-brainstorm` → spec → plan → build; M7 deterministic spec verify is the SDD substrate |
| **Clean Code** | §10.7 | M4 truth in description; M9 docs match code; concurrency knob has clear name |
| **Hexagonal** | §10.8 | M2 host port + platform adapters; hook-cache is a domain optimization, not a leak |

---

## 9. Risks + Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Concurrency cap of 2-3 makes autopilot feel "slow" on healthy hosts | MEDIUM | Auto-tune from host capacity — 32 GB / 16 cores → cap of 4-6; cap is per-host, not global |
| Host probe returns wrong values on macOS Sonoma / Sequoia | HIGH | Snapshot tests on multiple macOS versions; fail-open default (cap=auto fallback to 2) |
| `prompt-injection-guard.py` cache invalidation race | MEDIUM | mtime check is atomic syscall; cache is per-process not shared; worst case is one extra reload |
| `instinct-observe.py` buffering loses events on crash | LOW | SubagentStop is the natural flush point; persistence loss bounded to last 5s of one agent's tool calls; instinct data is advisory, not audit |
| `runtime-rotate-throttled.py` fires while autopilot is mid-run | MEDIUM | Throttle to 1 hour; SessionEnd in Claude Code only fires when conversation ends, not mid-tool-call |
| Deterministic plan DAG misses semantic conflicts | MEDIUM | Phase 3 LLM still runs when script returns ambiguity; script handles the 90% structural case; LLM handles the 10% semantic case |
| Forced `--desc` from task title produces poor commit messages | LOW | Task title in `plan.md` is human-written or `/ai-plan`-curated; quality bound by plan quality, not commit-time prose |
| Mandatory spec `summary:` field breaks existing specs | MEDIUM | Migration: `/ai-spec migrate` populates missing fields from spec title or owner prompt; one-time CLI pass |
| `state.db` incremental vacuum interferes with active session | LOW | Runs only at SessionEnd, never mid-session |
| Removing redundant manifest reads changes agent behavior | LOW | `STACK_CONTEXT` JSON payload is byte-equivalent to a manifest re-parse; integration test asserts equivalence |
| New tunables proliferate "knob soup" | MEDIUM | Every new tunable has a sensible default; `AIENG_HOST_PREFLIGHT_*` opt-out via single `AIENG_HOST_PREFLIGHT_DISABLED=1`; CLAUDE.md table sorted by relevance |
| 9 milestones in one PR overwhelms reviewers | MEDIUM | Atomic commits per milestone; CHANGELOG is the index; M1+M4 alone is the safety-critical subset and can ship first as a hotfix branch if needed |
| The kernel panic recurs despite this work | CRITICAL | Validation step in DoD: rerun the failing autopilot on the same machine post-merge; document outcome in PR |

---

## 10. Open Decisions for `/ai-brainstorm`

These become `D-NNN-NN` rows in the decisions table once spec is approved.

**D1 — Default `AIENG_MAX_WAVE_AGENTS` value.** Auto-compute from host (M1 recommendation), OR fixed default `3`, OR fixed default `2` (most conservative)?
> Recommendation: **auto with floor=2, ceiling=6**. Auto adapts to operator hardware; floor protects single-core / 8 GB hosts; ceiling prevents accidental fan-out on 64 GB workstations.

**D2 — Host preflight scope.** Apply to `/ai-autopilot` only (originating skill), OR also `/ai-build`, `/ai-review`, `/ai-verify`, `/ai-plan` (any skill that spawns subagents)?
> Recommendation: **all skills that dispatch ≥ 2 parallel subagents** — `/ai-autopilot`, `/ai-build`, `/ai-review`, `/ai-verify`. Skills that dispatch ≤ 1 (e.g., `/ai-explore` alone) skip the probe.

**D3 — Hot-path cache invalidation strategy.** mtime-based (file-level) OR content-hash (more correct, more expensive)?
> Recommendation: **mtime** — atomic, cheap, sufficient. False-positive invalidation is harmless (one extra reload); false-negative (stale cache) requires content tampering that the integrity hooks already cover.

**D4 — NDJSON rotation policy.** Archive + start fresh chain (current `reset-events` behavior), OR rolling N-file retention (e.g., 5 historical archives)?
> Recommendation: **archive + start fresh + retain 3 archives in `state/archives/`**. Audit chain is preserved (Constitution §13.1); old archives age out via `runtime_rotate.py`.

**D5 — Phase 3 DAG fallback semantics.** When `ai-eng plan dag-build` reports conflicts, abort and ask user, OR escalate to LLM Phase-3 reasoning automatically?
> Recommendation: **escalate to LLM** — preserves current behavior for the 10% ambiguous case; deterministic short-circuit handles the 90%.

**D6 — `summary:` frontmatter migration.** Block CI on specs missing `summary:` (hard requirement), OR warn and synthesize from spec title (soft requirement)?
> Recommendation: **soft initially, hard after 30 days** — gives existing specs a migration window. Hard cutover by spec-140 timeline.

**D7 — Tunable surface — env vars vs manifest knobs.** Some tunables are env-only, some are manifest-only, some are both. Standardize on "both" with env precedence?
> Recommendation: **both, env precedence**. Manifest captures project defaults; env overrides for one-off runs. Mirrors existing `AIENG_*` pattern.

**D8 — Validation on the trigger machine.** Synthetic reproduction (run autopilot with N=8 on the same hardware), OR real-world adoption period (ship, monitor, gather telemetry)?
> Recommendation: **both** — synthetic repro pre-merge (DoD step); 30-day monitoring post-merge (new dashboard from `host_capacity` events).

**D9 — Hexagonal placement of `host/probe.py`.** Under `src/ai_engineering/host/` (domain) OR `src/ai_engineering/adapters/host/` (adapter layer)?
> Recommendation: **adapter layer** — host inspection is a port to the operating system; domain is concurrency policy. Mirrors how `state/db.py` and `state/instincts.py` are organized.

**D10 — Backwards compatibility for the "x3" correction.** Hard rename (Constitution §13.3), OR add a one-release compatibility line?
> Recommendation: **hard rename** — per Constitution. The text drift was a bug, not a contract. CHANGELOG documents the breakage.

---

## 11. Hand-off Sequence

### What `/ai-plan` will consume

- This brief promoted to `.ai-engineering/specs/spec-NNN-framework-performance-hardening.md` after `/ai-brainstorm` approval.
- 10 Decision rows `D-NNN-01` through `D-NNN-10` written into `state.db decisions` table with recommended resolutions OR owner-overridden values.
- `plan.md` structured by Milestone M1-M9; each milestone broken into 3-6 atomic tasks per Constitution §3 (Surgical Changes); each task with TDD RED test first per §10.5.

### What `/ai-build` will execute

- **Safety-critical pass first**: M1 (concurrency cap) + M4 (stale x3 correction) land as the smallest possible safety hotfix. Even if remaining milestones are deferred, these two alone close the kernel-panic vector.
- **Observability pass**: M2 (host probe) + M9 (tunables docs) — operator now sees what the framework is about to do.
- **Hot-path pass**: M5 (hook caches) — reduces per-tool-call overhead; bounded by atomic-commit-per-script.
- **Determinism pass**: M3 (stack context) + M7 (spec verify + DAG) + M8 (commit/PR compose) — removes LLM calls from mechanical paths.
- **Retention pass**: M6 (runtime rotation wired) — closes the growth loop.
- **All tests RED → GREEN → REFACTOR** per §10.5. No test weakened.
- **Final quality loop** per Constitution §13.5: single round, fail-loud on blockers.

### What `/ai-pr` will surface

- PR `spec-135` body updated with all 9 milestones complete + green check matrix + before/after validation on the trigger machine.
- `CHANGELOG.md ## [Unreleased]` section populated: `### Added` (new tunables, host probe, deterministic CLIs), `### Changed` (concurrency cap default, hook hot-path optimizations, manifest read pattern), `### Fixed` (stale x3, tunables doc drift), `### BREAKING CHANGES` (spec `summary:` required, hooks now batched).
- `governance audit` report shows zero blockers.
- Commit history: ≤ 35 atomic commits, Conventional Commits prefix per §13.6, every commit on `spec-135/framework-performance-hardening`.
- No force-push. No hook bypass. No `--no-verify`.

---

## 12. References / Cross-Brief Coordination

### External references

- **Apple memory compressor architecture** — saturation behavior on Apple Silicon documented in `man vm_stat` and Apple Activity Monitor "Memory Pressure" calculation; pressure_pct ≥ 50% indicates the compressor cannot keep pace.
- **macOS userspace watchdog (`watchdogd`)** — `/System/Library/LaunchDaemons/com.apple.watchdogd.plist`; triggers panic on missed check-ins from critical services. WindowServer is on the critical list.
- **Anthropic Claude Agent SDK** — `https://docs.claude.com/en/agents/sdk` — orchestration patterns; `https://www.anthropic.com/research/multi-agent-research-system` documents Anthropic's own concurrency considerations.
- **Python `concurrent.futures` ThreadPoolExecutor `max_workers`** — PEP 3148 + stdlib docs; recommended ceiling of `min(32, os.cpu_count() + 4)` for I/O-bound; for subprocess-spawning workloads, lower caps are appropriate.
- **`git-cliff`** — `https://github.com/orhun/git-cliff` — deterministic conventional-commits changelog generator (referenced for M8 determinism pass).
- **macOS `vm_stat` output parsing** — `man vm_stat`; pages are 16384 bytes on Apple Silicon (vs 4096 on Intel).

### Cross-brief coordination

| Predecessor | Relationship |
|-------------|--------------|
| `skills-agents-excellence-v2-brief.md` (spec-134) | **Orthogonal.** That brief addresses UX cohesion + naming. This brief addresses performance + memory. No file overlap expected. |
| `dx-excellence-refactor-brief.md` (spec-131 — shipped) | **Foundation.** Established the hot-path discipline (pre-commit < 1s, pre-push < 5s, CI for heavier work). This brief extends to the SubagentStop / Stop / PreToolUse / PostToolUse hot paths. |
| `cli-ux-overhaul-brief.md` (spec-132 — shipped) | **Reuses.** `ai-eng` CLI primitive established here; M2 (`host probe`), M7 (`spec verify`, `plan dag-build`) extend the CLI surface following the same conventions. |
| `cli-ux-cross-ide-rearch-brief.md` (spec-133 — shipped) | **Reinforces.** Surface Axioms A1/A2 hold for the new CLI subcommands. No skill-mirror payload changes. |
| (Future) `framework-observability-dashboard-brief.md` | **Anticipated.** A future brief may consume `host_capacity` events to build an operator dashboard. Out of scope here; the events emitted by M2 are the substrate. |

---

## 13. Glossary

**Memory compressor (macOS)** — Kernel subsystem that compresses pages in RAM before writing them to swap. "Segments" are the compressor's internal regions; 100% of segments means the compressor cannot accept new pages and the system must wait for swap I/O.

**Swapfile** — File-backed virtual memory page store (`/private/var/vm/swapfile*`). Healthy macOS systems run 1–5; double-digit counts indicate long-term sustained pressure.

**Watchdog timeout (userspace)** — `watchdogd` daemon expects critical services to check in periodically. Missed check-ins for > 60s trigger an "induced crash" of the misbehaving service; missed check-ins for > 90-180s trigger a kernel panic.

**WindowServer** — macOS UI compositor process; handles window drawing, mouse/trackpad events, animations. Critical service; loss of responsiveness manifests as a frozen desktop.

**Wave (autopilot)** — A Phase-4 implementation batch; a group of sub-specs whose dependencies allow parallel execution.

**Fan-out** — Number of concurrent subprocesses or subagents spawned from a single dispatch point.

**Concurrency budget** — Maximum number of agents / subprocesses permitted to run simultaneously at a given orchestration site.

**Hot path** — Code that executes on every tool call, commit, or push. Budget-bound (pre-commit < 1s, hook < 200ms, etc.) per Constitution / `dx-excellence-refactor-brief.md`.

**Host probe** — Synchronous capability check (RAM, cores, pressure, swap usage) executed before resource-intensive dispatch.

**NDJSON rotation** — Renaming a growing newline-delimited JSON log to an archive name and starting a fresh chain, preserving Article-III audit immutability.

**SubagentStop cascade** — When a parent agent's subagents all complete, a `Stop` event may fire for each, plus a parent-level `Stop`. Hooks that listen on Stop can fire 10+ times in quick succession at the end of a phase.

**Module-level cache (in hooks)** — A `dict` / value declared at module top scope, reused across multiple invocations of the same hook process. In Claude Code, hook scripts may be invoked as new subprocesses each time; the cache is per-process, not cross-process.

**Determinism opportunity** — A site in the code where an LLM is invoked for work that a deterministic script can do equally well (with equivalent or better quality, plus lower latency, lower cost, and zero hallucination risk).

**Article-III audit chain** — Constitution §13.1 governance contract: `framework-events.ndjson` is an immutable append-only log. Rotation must archive, never truncate.

**`AIENG_HOOK_ENGINE`** — Environment variable set per-IDE by the hook wiring file (claude-code = default unset; codex sets `=codex`; gemini-cli sets `=gemini`). Canonical hook scripts under `.ai-engineering/scripts/hooks/` read this to adapt their behavior (event-name mapping, output framing). The single canonical script body serves all 3 active runtime surfaces — the wiring file is what differs.

**Active runtime surface** — An IDE that ships a hook config file pointing at the canonical scripts AND has a materialized mirror directory on disk. As of this brief: claude-code, codex, gemini-cli are active. github-copilot is partially active (skill mirror exists; runtime hook surface is git-lifecycle only). opencode and cursor are declared in `manifest.yml surfaces.enabled` but their mirror directories do not exist.

---

## 14. Cross-IDE Mirror Coverage Matrix

The framework declares 6 surfaces in [.ai-engineering/manifest.yml](.ai-engineering/manifest.yml) `surfaces.enabled`: `claude-code`, `codex`, `gemini-cli`, `github-copilot`, `opencode`, `cursor`. The current materialization state of each mirror determines which milestones land where and which require explicit per-surface wiring.

### 14.1 — Materialization snapshot (verified pre-brief)

| Surface | Mirror directory | Hook config file | State |
|---------|------------------|------------------|-------|
| claude-code | `.claude/` | [.claude/settings.json](.claude/settings.json) | **Active** — source of truth |
| codex | `.codex/` | [.codex/hooks.json](.codex/hooks.json) | **Active** — bridges to canonical scripts via `AIENG_HOOK_ENGINE=codex` |
| gemini-cli | `.gemini/` | [.gemini/settings.json](.gemini/settings.json) | **Active** — Gemini-native event vocabulary (`BeforeAgent`, etc.) routed via `AIENG_HOOK_ENGINE=gemini` |
| github-copilot | `.github/` | [.github/hooks/hooks.json](.github/hooks/hooks.json) | **Partial** — skill/agent mirror present; runtime hook surface is git-lifecycle only (no conversational SessionEnd) |
| opencode | `.opencode/` | (n/a — absent) | **Declared, not materialized** |
| cursor | `.cursor/` | (n/a — absent) | **Declared, not materialized** |

### 14.2 — Per-milestone propagation

Propagation mechanisms: **auto-mirror** = `scripts/sync_mirrors/core.py` regenerates byte-equivalent skill/agent files; **universal** = the change lives in `src/ai_engineering/` or `.ai-engineering/scripts/` and is invoked identically by every IDE; **wire-per-surface** = each active surface needs an explicit edit to its hook config; **deferred** = applies once the mirror directory exists.

| Milestone | claude-code | codex | gemini-cli | github-copilot | opencode | cursor |
|-----------|-------------|-------|------------|----------------|----------|--------|
| M1 concurrency cap | auto-mirror | auto-mirror | auto-mirror | auto-mirror (skill body only — Copilot does not dispatch waves) | deferred | deferred |
| M2 host probe (`ai-eng host probe`) | universal | universal | universal | universal | universal | universal |
| M3 stack context | auto-mirror | auto-mirror | auto-mirror | auto-mirror | deferred | deferred |
| M4 stale "x3" fix | auto-mirror | auto-mirror | auto-mirror | auto-mirror | deferred | deferred |
| M5 hook hot-path | shared (canonical scripts; benefits all engines via `AIENG_HOOK_ENGINE`) | shared | shared | shared | n/a until materialized | n/a until materialized |
| M6 SessionEnd wire | **wire-per-surface** in `.claude/settings.json` | **wire-per-surface** in `.codex/hooks.json` | **wire-per-surface** in `.gemini/settings.json` (map to Gemini end-of-session event) | N/A (no runtime SessionEnd in `.github/hooks/`) | deferred | deferred |
| M7 deterministic CLIs | universal | universal | universal | universal | universal | universal |
| M8 commit/PR compose | auto-mirror | auto-mirror | auto-mirror | auto-mirror | deferred | deferred |
| M9 tunables docs | `CLAUDE.md` | `AGENTS.md` (codex canonical anchor) | `GEMINI.md` | `.github/copilot-instructions.md` | deferred | deferred |
| Python source (orchestrator caps, `src/`) | universal | universal | universal | universal | universal | universal |

### 14.3 — Parity enforcement test

New test `tests/architecture/test_hook_wiring_parity.py` asserts the cross-IDE wiring contract:

1. For every event NAME wired in `.claude/settings.json` that invokes a canonical hook script:
   - Equivalent wiring exists in `.codex/hooks.json` under the same event name, OR
   - Wiring is explicitly waived in the test fixture with a documented reason.
2. For `.gemini/settings.json`: equivalent wiring under the Gemini-native event vocabulary, looked up through a maintained mapping table (e.g., `SessionEnd → AfterAgent` or whatever the verified mapping is). Mapping table lives at `.ai-engineering/contexts/gemini-event-mapping.md`.
3. M6 specifically: the `runtime-rotate-throttled.py` invocation must be wired at the SessionEnd-equivalent of every active runtime surface (claude-code, codex, gemini-cli). github-copilot is waived in the fixture (no conversational SessionEnd).
4. opencode and cursor are tracked as "deferred" entries in the fixture — the test passes them silently until their mirror directories exist, at which point removing the deferred entry forces wiring or explicit waiver.

### 14.4 — Sync-mirror tooling responsibility split

| Layer | Tool | Responsibility |
|-------|------|----------------|
| Skill / agent bodies | `scripts/sync_mirrors/core.py` | Regenerates `.codex/skills/`, `.gemini/skills/`, `.github/skills/`, `.codex/agents/`, `.gemini/agents/`, `.github/agents/` byte-equivalent to `.claude/skills/` and `.claude/agents/` |
| Canonical mirrors at root | manual + linted | `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` carry identical canonical payload + IDE-extras fence (Surface Axiom A1 enforced by `tests/architecture/test_surface_parity.py` and `tools/skill_lint/checks/md_mirror.py`) |
| Hook scripts | (none — canonical) | `.ai-engineering/scripts/hooks/` is the single source; no mirror tool needed; IDE-specific behavior achieved via `AIENG_HOOK_ENGINE` env var |
| Hook wiring | manual (per-surface) | `.claude/settings.json`, `.codex/hooks.json`, `.gemini/settings.json` are authored independently because each IDE has its own event vocabulary and timeout conventions. Parity asserted by `test_hook_wiring_parity.py` (M6 DoD) |
| CLAUDE.md tunables docs | manual + lint | M9 updates all 4 root mirrors atomically (single commit); `test_tunables_docs_match_code.py` asserts code/doc parity but does not enforce mirror-to-mirror equivalence (that is `test_surface_parity.py`'s job) |

### 14.5 — Open Decision (cross-IDE specific)

**D11 — opencode / cursor wiring scope.** Land M6 wiring stubs in `.opencode/` and `.cursor/` now (creating the directories), OR wait until a separate spec materializes those mirror surfaces with their full skill/agent payload?
> Recommendation: **wait** — creating `.opencode/` with only a hook config and no skills/agents would violate Surface Axiom A1 (parity). The mirror directories should appear in a single coordinated spec that lands skills + agents + hook wiring together. This brief defers; CHANGELOG documents the deferral with a `BREAKING CHANGES` carve-out anticipating the future spec.

---

**End of brief.** Promote with `/ai-brainstorm` for spec generation and decision-row writing. Highest-priority subset for hot-fix branch (if scope must shrink): **M1 (concurrency cap) + M4 (stale x3 correction)** — these two alone close the kernel-panic class. Cross-IDE coverage is enforced by `test_hook_wiring_parity.py` (new in §7 DoD) across the 3 active runtime surfaces.
