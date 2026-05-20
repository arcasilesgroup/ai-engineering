---
title: "Obvious by Default — Auditing ai-engineering Against 'A Process That Does the Obvious Becomes Safe'"
status: draft
audience: /ai-brainstorm
reader: framework maintainers
branch: TBD (assigned at /ai-brainstorm promotion)
length_estimate: "~350 lines"
authoring_style: "Staff Principal Architect — evidence-anchored, fail-loud, poka-yoke-driven, no hedging"
principles_required: [KISS, YAGNI, DRY, SOLID, SDD, TDD, clean-code, hexagonal]
delivery_mode: "Multi-wave, single-concern-per-PR / hard-rename / no-shim / Conventional Commits"
mantra: "Un proceso que hace lo obvio se vuelve seguro. The obvious reading of any surface MUST be the safe one — fail-loud, deterministic, single-path. Where the obvious reading is wrong, the surface is a trap."
---

> **READ FIRST.** This brief is a structured intake for `/ai-brainstorm`. It is the human-readable contract between the idea phase and the spec phase. It was authored from a codebase audit plus external prior-art sweep of the current workspace on 2026-05-20. Diagnostic claims carry repo-relative `file:line` citations; the highest-stakes contradictions were manually re-verified against source before inclusion. No implementation begins until this brief is promoted to `spec-NNN` and approved. Reader audience: framework maintainers.
>
> **The thesis, stated as a test.** A process "does the obvious" when a competent reader, looking only at the surface (a SKILL description, a doc line, a default flag, a CLI verb), predicts the behavior correctly. It "becomes safe" because nobody has to fight the design to be correct. The audit asked one question of every surface: *if a maintainer trusts the obvious reading, do they get burned?* In load-bearing safety machinery, the answer is currently **yes** — the framework that preaches fail-loud ships `_DEFAULT_MODE = "warn"`, and the doc that is the cited source-of-truth for agents points at a manifest key that does not exist.

---

## 1. Vision

ai-engineering is governance-grade: it gates secrets, bans suppression, enforces single-source-of-truth, and runs a bounded fail-loud quality loop. The machinery is real and mostly excellent. But a governance framework earns trust through one property above all others: **the safe behavior must be the obvious behavior, and the obvious reading must be the true one.** When the two diverge, every downstream user — human or agent — inherits a silent trap.

The vision is a framework where the obvious reading is always the safe one, expressed through four lenses the operator selected:

- **Predictability / determinism** — same input, same output; no hidden state; the documented default is the shipped default.
- **Simplification / deletion** — one obvious way to do each thing; no near-duplicate surface a reader must disambiguate.
- **Fail-loud safety** — when a gate cannot do its job, it says so and stops; it never exits 0 on a broken tool.
- **DX legibility** — names predict behavior; conventions are enforced by tests, not by hope.

This is poka-yoke (Shingo) applied to an agent framework: make the wrong action impossible or immediately visible, so the worker — here, a maintainer or a Claude agent — falls into the pit of success rather than climbing toward it.

---

## 2. Scope Boundary

### In scope

| Item | Reason |
|------|--------|
| Fail-open holes in gates and hooks (Wave 1) | A gate that silently passes on tool-absence is the exact failure the mantra forbids |
| Doc-vs-code contradictions (Wave 2) | The obvious reading of a doc is currently false in ≥3 load-bearing places |
| Duplicate / colliding skill + CLI surface (Wave 3) | "One obvious way" is violated by trigger collisions and twin commands |
| Non-deterministic "done" verdict (Wave 4) | LLM variance in the STOP decision makes shipping unpredictable |
| Convention enforcement via CI (Wave 5) | §10.x citation, naming, destructive defaults, suppression DEC-binding — poka-yoke them |

### Explicitly NOT in scope

| Item | Why excluded |
|------|--------------|
| Net-new skills or agents | This is a safety/legibility refactor, not a feature wave |
| Rewriting the persistence doctrine | The four-tier model is sound; only its violations are in scope |
| Performance / token budget tuning | Covered by `framework-performance-hardening-brief.md` |
| Mirror diet / token reduction | Covered by `skills-agents-excellence-v2-brief.md` |
| Changing the canonical chain semantics | Only its *legibility* (off-chain visibility) is touched |

---

## 3. Diagnostic Snapshot

Current-state evidence. Every "currently" sentence cites `file:line`.

### 3.1 The framework ships fail-OPEN where it documents fail-LOUD (CRITICAL)

Currently, hook integrity defaults to `warn`, not `enforce`. `.ai-engineering/scripts/hooks/_lib/integrity.py:40` declares `_DEFAULT_MODE = "warn"`, while the same file's docstring at `.ai-engineering/scripts/hooks/_lib/integrity.py:9` says "`enforce` (default, spec-120 follow-up)" and `.ai-engineering/scripts/hooks/_lib/integrity.py:18-21` narrates "The default flipped from `warn` to `enforce` after the spec-120 governance review." `CLAUDE.md:183` also lists `AIENG_HOOK_INTEGRITY_MODE # default enforce`. Three sources claim fail-closed; the shipped constant is fail-open. A hook whose bytes drifted from the committed manifest runs anyway, warning into a log nobody reads.

Currently, the suppression gate skips itself when its own dependency is missing. `src/ai_engineering/cli_commands/gate.py:138-140` catches `ImportError` on `no_suppression.cli`, emits `warning("no_suppression module not installed; skipping Article VII gate")`, and returns. A fresh install, a corrupted venv, or dependency drift silently disables the current no-suppression rule (`CONSTITUTION.md:66-69`, `CLAUDE.md:106-109`) — the gate exits clean while suppression markers go unchecked.

Currently, the secret scanner produces a clean verdict when its binary is broken. `src/ai_engineering/verify/service.py:53-54` runs gitleaks via a bare `subprocess.run` with no `FileNotFoundError` guard; `src/ai_engineering/verify/service.py:307-308` returns early when `returncode != 0` and stdout is empty (a crash, a missing config, a broken install all look like "clean"); `src/ai_engineering/verify/service.py:311-313` swallows a `JSONDecodeError` and returns. Broken tool equals green gate.

Currently, expired risk acceptances warn but do not block on the hot path. `src/ai_engineering/cli_commands/gate.py:167-195` (`_check_risk_inline`) surfaces expired DECs as `warning()` only, and the pre-commit / pre-push gate paths (`src/ai_engineering/cli_commands/gate.py:91-99`, `src/ai_engineering/cli_commands/gate.py:118-127`) never call it in strict mode. The OPA policy `.ai-engineering/policies/risk_acceptance_ttl.rego:19-25` correctly denies on `now_ns >= ttl_ns`, but it is not wired into `gate run`.

### 3.2 Silent fallbacks in config and hooks (HIGH)

Currently, a malformed manifest is indistinguishable from a missing one. `src/ai_engineering/config/loader.py:55-57` catches `(OSError, yaml.YAMLError)`, logs at `debug`, and returns `ManifestConfig()` — all defaults, no stderr, no non-zero exit. `src/ai_engineering/state/repository.py:48-50` repeats the pattern, returning `{}` on parse failure. `src/ai_engineering/cli_factory.py:239-245` wraps stack-drift detection in a bare `except Exception: return`, so any failure silently disables drift detection.

Currently, the highest-frequency hook swallows every formatter error. `.ai-engineering/scripts/hooks/auto-format.py:5` documents "All errors silently swallowed -- exit 0 always"; `.ai-engineering/scripts/hooks/auto-format.py:30-34` and `.ai-engineering/scripts/hooks/auto-format.py:242-249` wrap the auto-stage and re-stage in `contextlib.suppress(Exception)`. A formatter that rewrites a file then fails to re-stage leaves the tree inconsistent with no signal. `.ai-engineering/scripts/hooks/runtime-stop.py:21` lets checkpoint and resume-state writes "degrade silently," so the next session resumes from stale or absent state. `.ai-engineering/scripts/hooks/mcp-health.py:137-138` has a bare `except Exception: pass` on MCP state persistence; `.ai-engineering/scripts/hooks/no-verify-guard.py:70` documents fail-open parsing, and `.ai-engineering/scripts/hooks/no-verify-guard.py:80-86` returns `False` (allow) when `shlex.split` raises on malformed quoting — an unparseable command is treated as clean.

### 3.3 The obvious reading of the docs is factually wrong (HIGH)

Currently, CLAUDE.md cites a manifest key that does not exist. `CLAUDE.md:79-80` states the "9 first-class agents are listed in `.ai-engineering/manifest.yml` under `agents.registry`," while `.ai-engineering/manifest.yml:1-130` contains no `agents:` or `registry` key. A maintainer asking "where is the agent registry?" follows the doc to a dead end. The repo also carries internal review and verifier agent families alongside the `ai-*` family — for example `.claude/agents/review-context.md:1-3`, `.claude/agents/reviewer-security.md:1-3`, and `.claude/agents/verifier-deterministic.md:1-3` — so the doc does not give a single obvious source for "which agents count."

Currently, at least 8 behavior-changing env vars are read by hooks but absent from CLAUDE.md's tunables table: `AIENG_RALPH_DISABLED` (`.ai-engineering/scripts/hooks/runtime-stop.py:84`), `AIENG_RISK_ACCUMULATOR_DISABLED` (`.ai-engineering/scripts/hooks/prompt-injection-guard.py:63`, `.ai-engineering/scripts/hooks/runtime-guard.py:205`), `AIENG_INSTINCT_BATCH_DISABLED` (`.ai-engineering/scripts/hooks/instinct-observe.py:124`), `AIENG_HOOK_ENGINE` / `AIENG_HOOK_ENGINE_DEFAULT` (`.ai-engineering/scripts/hooks/_lib/hook_context.py:131`, `.ai-engineering/scripts/hooks/_lib/hook_context.py:147`), `AIE_MCP_HEALTH_FAIL_OPEN` (`.ai-engineering/scripts/hooks/mcp-health.py:473`, `.ai-engineering/scripts/hooks/mcp-health.py:514`), `AIE_MCP_URL_* / CMD_* / RECONNECT_*` (`.ai-engineering/scripts/hooks/mcp-health.py:334`, `.ai-engineering/scripts/hooks/mcp-health.py:348`, `.ai-engineering/scripts/hooks/mcp-health.py:383`), `AIENG_EVENT_SIDECAR_BYTES` (`.ai-engineering/scripts/hooks/_lib/audit.py:20`), `AIENG_TELEMETRY_DEBUG` (`.ai-engineering/scripts/hooks/_lib/audit.py:130`). `AIE_MCP_HEALTH_FAIL_OPEN=1` converts the MCP health gate from blocking to pass-through — a security gate disabled by an undocumented flag.

### 3.4 SSOT-per-datum violations (HIGH)

Currently, decisions are dual-written. `src/ai_engineering/state/repository.py:154-168` (`save_decisions`) calls both `upsert_decision_rows` (state.db) and `write_json_model(self.decision_store_path, ...)` (decision-store.json) on every write; the docstring says `state.db` is canonical and concedes the JSON "mirror remains until the 12 outstanding Decision view-model callers are migrated" (`src/ai_engineering/state/repository.py:157-163`). Worse, `src/ai_engineering/state/context_packs.py:35` lists `decision-store.json` in `_AUTHORITATIVE_CONTROL_PLANE`, and `src/ai_engineering/config/framework_defaults.py:25` injects it into session context. LLM sessions are fed the deprecated store as ground truth. `gate-findings.json` carries transitional dual-store pressure: `docs/persistence-doctrine.md:155-158` calls the JSON primary and the SQLite table non-primary, yet `src/ai_engineering/state/migrations/0002_seed_from_json.py:221-227` still seeds the SQLite table and `src/ai_engineering/state/control_plane.py:154-156` still treats the JSON path as state-plane residue. The spec phase must decide whether to keep JSON primary with explicit read/staleness rules or remove the transitional table/seed path later.

### 3.5 More than one obvious way (MEDIUM)

Currently, trigger phrases collide across skills with no deterministic discriminator:

- "write a blog post" fires both `ai-prose` (`.claude/skills/ai-prose/SKILL.md:3`) and `ai-marketing` (`.claude/skills/ai-marketing/SKILL.md:3`, which adds only "to publish").
- "pre-release" is claimed by `ai-verify` (`.claude/skills/ai-verify/SKILL.md:3`), `ai-governance` (`.claude/skills/ai-governance/SKILL.md:3`), and `ai-security` (`.claude/skills/ai-security/SKILL.md:3`).
- "architecture" is claimed by `ai-explore` (`.claude/skills/ai-explore/SKILL.md:3`), `ai-explain` (`.claude/skills/ai-explain/SKILL.md:3`), and `ai-onboard` (`.claude/skills/ai-onboard/SKILL.md:3`).
- "scan for security issues" is claimed by both `ai-verify` (`.claude/skills/ai-verify/SKILL.md:3`) and `ai-security` (`.claude/skills/ai-security/SKILL.md:3`).
- "implement this" (`.claude/skills/ai-code/SKILL.md:3`) versus "implement it" (`.claude/skills/ai-build/SKILL.md:3`) — a one-word differentiator on the canonical implementation gateway.

Currently, branch cleanup has two overlapping public entry points and orchestration paths: `ai-eng maintenance branch-cleanup` is registered at `src/ai_engineering/cli_factory.py:414` and delegates through `src/ai_engineering/cli_commands/maintenance.py:123-149`, while `ai-eng cleanup branches` is registered at `src/ai_engineering/cli_factory.py:426` and resolves/deletes targets inside `src/ai_engineering/cli_commands/cleanup.py:219-300`. And `ai-eng cleanup branches` with no flags silently activates `merged = True` at `src/ai_engineering/cli_commands/cleanup.py:257-260` — a destructive default with opt-in `--dry-run`.

### 3.6 "Done" is not deterministic (MEDIUM)

Currently, the bounded quality loop's STOP decision depends on LLM judgment. `.claude/skills/ai-build/handlers/quality.md:124-141` makes Step 2d eligibility ("does not require a product decision, architecture redesign, destructive migration...") an LLM call with no deterministic signal — the same diff can be judged eligible or not across runs. `.claude/skills/ai-verify/SKILL.md:44-58` places the LLM `verifier-acceptance` specialist (governance + feature compliance) inside `/ai-verify`, a surface that brands itself "evidence before claims," and the output contract at `.claude/skills/ai-verify/SKILL.md:62-64` does not tag findings as `deterministic` vs `llm`, so callers cannot threshold them differently.

### 3.7 Conventions exist but are not enforced (MEDIUM/DX)

Currently, the documented "every SKILL.md `## Workflow` cites a §10.x anchor" convention at `.ai-engineering/reference/principles.md:15-17` holds in only 7 of 53 skills by repository audit; 24 have no Workflow section and 22 have one without any §10.x citation. Naming grammar is not exposed as an enforceable rule: the surface mixes action-oriented names such as `.claude/skills/ai-build/SKILL.md:2-3` with noun-oriented names such as `.claude/skills/ai-animation/SKILL.md:2-3` without a cited discriminator. The suppression allowlist `.ai-engineering/suppression-allowlist.yml:64-641` carries 50+ entries with `dec_id: ""`, contradicting its own lifecycle guidance at `.ai-engineering/suppression-allowlist.yml:8-12`; the security-relevant `nosemgrep_hash` pattern is listed at `.ai-engineering/suppression-allowlist.yml:20-26` without a hard DEC-binding rule.

### 3.8 What is already healthy (do not touch)

The four-tier persistence doctrine is well-structured (`docs/persistence-doctrine.md:22-33`); the `_safe()` command error boundary is uniform and correct (`src/ai_engineering/cli_factory.py:199-201`); removed CLI verbs are registered as fail-loud stubs (`src/ai_engineering/cli_factory.py:277-303`); the OPA TTL policy logic is correct (only its wiring is missing, `.ai-engineering/policies/risk_acceptance_ttl.rego:19-25`); the autopilot Phase 5 STOP matrix is structurally sound at the condition level (`.claude/skills/ai-autopilot/handlers/phase-quality.md:183-187`). This is an excellence refactor on a healthy base, not a rescue.

---

## 4. Architecture

The change is organized into **five waves**, each mapped to one lens and one external principle. Waves are independent and ship as single-concern PRs; no wave blocks another except where noted.

```
                    "Un proceso que hace lo obvio se vuelve seguro"
                                       |
        +-------------+-------------+--+----------+-------------+
        |             |             |             |             |
     Wave 1        Wave 2        Wave 3        Wave 4        Wave 5
   Fail-loud     Docs match    One obvious   Determinis-   Poka-yoke
   the gates     the code      way            tic "done"   the rules
        |             |             |             |             |
   fail-fast     least         PEP 20 +      Bazel         Shingo +
   (Shore)       astonish-     Anthropic     hermeticity   pit-of-
                 ment + PEP20  tool design                 success
        |             |             |             |             |
   exit non-0    one true      collapse      tool-decided  CI tests make
   on broken     reading per   twins; one    STOP; tag     violation
   gate          surface       entry point   method        impossible
```

**Module boundaries touched:**

- **Hooks** (`.ai-engineering/scripts/hooks/`) — Waves 1, 2. Convert silent swallows to `hookSpecificOutput` warnings or hard refusals; flip the integrity default.
- **Gate / verify services** (`src/ai_engineering/cli_commands/gate.py`, `src/ai_engineering/verify/service.py`) — Waves 1, 4. Broken-tool-equals-block; wire risk TTL; split deterministic vs LLM verdicts.
- **Config / state** (`src/ai_engineering/config/`, `src/ai_engineering/state/`) — Waves 1, 2, 3. Loud config errors; finish the decision-store migration; pick one SSOT reader.
- **Skill + agent surface** (`.claude/skills/`, `.claude/agents/`, `CLAUDE.md`) — Waves 3, 5. Collapse collisions; reconcile the agent count; enforce conventions.
- **CLI** (`src/ai_engineering/cli_commands/`) — Waves 3, 5. One branch-cleanup; dry-run-by-default for destructive verbs.

Hexagonal note (§10.8): gate/verify logic is already a port-and-adapter shape (service layer + tool adapters). Wave 1 hardens the adapter boundary — a tool adapter that cannot run must raise into the port, not return a clean result.

---

## 5. Evidence Catalog

Consolidated `file:line` citations. Repo-relative paths; no machine-absolute paths.

| # | Finding | Lens | Severity | Evidence |
|---|---------|------|----------|----------|
| E-1 | Integrity default is `warn`, docs say `enforce` (3-way) | Pred / Fail-loud | CRITICAL | `.ai-engineering/scripts/hooks/_lib/integrity.py:9`, `.ai-engineering/scripts/hooks/_lib/integrity.py:18-21`, `.ai-engineering/scripts/hooks/_lib/integrity.py:40`, `CLAUDE.md:183` |
| E-2 | No-suppression gate skipped on `ImportError` | Fail-loud | CRITICAL | `src/ai_engineering/cli_commands/gate.py:136-140`, `CONSTITUTION.md:66-69`, `CLAUDE.md:106-109` |
| E-3 | gitleaks absent/crash = clean verdict | Fail-loud / Pred | CRITICAL | `src/ai_engineering/verify/service.py:53-54`, `src/ai_engineering/verify/service.py:307-308`, `src/ai_engineering/verify/service.py:311-313` |
| E-4 | Expired risk acceptance warns, never blocks | Fail-loud | HIGH | `src/ai_engineering/cli_commands/gate.py:91-99`, `src/ai_engineering/cli_commands/gate.py:118-127`, `src/ai_engineering/cli_commands/gate.py:167-195`, `.ai-engineering/policies/risk_acceptance_ttl.rego:19-25` |
| E-5 | Malformed manifest = silent defaults | Fail-loud / Pred | HIGH | `src/ai_engineering/config/loader.py:55-57`, `src/ai_engineering/state/repository.py:48-50` |
| E-6 | Stack-drift middleware swallows all | Fail-loud | HIGH | `src/ai_engineering/cli_factory.py:237-245` |
| E-7 | auto-format swallows all formatter errors | Fail-loud | HIGH | `.ai-engineering/scripts/hooks/auto-format.py:5`, `.ai-engineering/scripts/hooks/auto-format.py:30-34`, `.ai-engineering/scripts/hooks/auto-format.py:242-249` |
| E-8 | runtime-stop checkpoint write silent | Fail-loud | HIGH | `.ai-engineering/scripts/hooks/runtime-stop.py:15-21` |
| E-9 | mcp-health bare `except: pass` on state | Fail-loud | MEDIUM | `.ai-engineering/scripts/hooks/mcp-health.py:132-138` |
| E-10 | no-verify-guard fail-open on parse error | Fail-loud | MEDIUM | `.ai-engineering/scripts/hooks/no-verify-guard.py:70`, `.ai-engineering/scripts/hooks/no-verify-guard.py:80-86` |
| E-11 | CLAUDE.md cites nonexistent `agents.registry` | Pred / DX | HIGH | `CLAUDE.md:79-80`, `.ai-engineering/manifest.yml:1-130`, `.claude/agents/review-context.md:1-3`, `.claude/agents/reviewer-security.md:1-3`, `.claude/agents/verifier-deterministic.md:1-3` |
| E-12 | 8 undocumented behavior-changing env vars | Pred / DX | HIGH | `.ai-engineering/scripts/hooks/runtime-stop.py:84`, `.ai-engineering/scripts/hooks/prompt-injection-guard.py:63`, `.ai-engineering/scripts/hooks/runtime-guard.py:205`, `.ai-engineering/scripts/hooks/instinct-observe.py:124`, `.ai-engineering/scripts/hooks/_lib/hook_context.py:131`, `.ai-engineering/scripts/hooks/_lib/hook_context.py:147`, `.ai-engineering/scripts/hooks/mcp-health.py:334`, `.ai-engineering/scripts/hooks/mcp-health.py:348`, `.ai-engineering/scripts/hooks/mcp-health.py:383`, `.ai-engineering/scripts/hooks/mcp-health.py:473`, `.ai-engineering/scripts/hooks/mcp-health.py:514`, `.ai-engineering/scripts/hooks/_lib/audit.py:20`, `.ai-engineering/scripts/hooks/_lib/audit.py:130` |
| E-13 | Decisions dual-written to state.db + JSON | SSOT | HIGH | `src/ai_engineering/state/repository.py:154-168` |
| E-14 | Stale decision-store.json marked authoritative | SSOT / Pred | HIGH | `src/ai_engineering/state/context_packs.py:32-36`, `src/ai_engineering/config/framework_defaults.py:21-25` |
| E-15 | gate-findings transitional store pressure | SSOT | MEDIUM | `docs/persistence-doctrine.md:155-158`, `src/ai_engineering/state/migrations/0002_seed_from_json.py:221-227`, `src/ai_engineering/state/control_plane.py:154-156` |
| E-16 | "write a blog post" fires 2 skills | Simpl / DX | HIGH | `.claude/skills/ai-prose/SKILL.md:3`, `.claude/skills/ai-marketing/SKILL.md:3` |
| E-17 | "pre-release" claimed by 3 skills | Pred / DX | HIGH | `.claude/skills/ai-verify/SKILL.md:3`, `.claude/skills/ai-governance/SKILL.md:3`, `.claude/skills/ai-security/SKILL.md:3` |
| E-18 | "architecture" claimed by 3 read-only skills | Pred / DX | HIGH | `.claude/skills/ai-explore/SKILL.md:3`, `.claude/skills/ai-explain/SKILL.md:3`, `.claude/skills/ai-onboard/SKILL.md:3` |
| E-19 | "scan for security issues" claimed by 2 | Pred | HIGH | `.claude/skills/ai-verify/SKILL.md:3`, `.claude/skills/ai-security/SKILL.md:3` |
| E-20 | "implement it"/"implement this" twins | Simpl / Pred | MEDIUM | `.claude/skills/ai-build/SKILL.md:3`, `.claude/skills/ai-code/SKILL.md:3` |
| E-21 | brainstorm vs spec-draft chain visibility | Simpl / DX | MEDIUM | `.claude/skills/ai-spec-draft/SKILL.md:3`, `.claude/skills/ai-brainstorm/SKILL.md:3`, `CLAUDE.md:58-66` |
| E-22 | 3 learning skills, fuzzy boundaries | Simpl / DX | MEDIUM | `.claude/skills/ai-learn/SKILL.md:3`, `.claude/skills/ai-session-watch/SKILL.md:3`, `.claude/skills/ai-skill-improve/SKILL.md:3` |
| E-23 | Two branch-cleanup entry points/orchestrators | Simpl / DX | MEDIUM | `src/ai_engineering/cli_factory.py:414`, `src/ai_engineering/cli_factory.py:426`, `src/ai_engineering/cli_commands/maintenance.py:123-149`, `src/ai_engineering/cli_commands/cleanup.py:219-300` |
| E-24 | `cleanup branches` destructive default | Surprising default | MEDIUM | `src/ai_engineering/cli_commands/cleanup.py:257-260`, `src/ai_engineering/cli_commands/cleanup.py:297-300` |
| E-25 | Quality-loop STOP eligibility is LLM-judged | Determinism | MEDIUM | `.claude/skills/ai-build/handlers/quality.md:116-117`, `.claude/skills/ai-build/handlers/quality.md:124-141` |
| E-26 | verifier-acceptance LLM inside deterministic surface; no method tag | Determinism / DX | MEDIUM | `.claude/skills/ai-verify/SKILL.md:44-58`, `.claude/skills/ai-verify/SKILL.md:62-64` |
| E-27 | §10.x citation present in only 7/53 skills | DX / Pred | MEDIUM | `.ai-engineering/reference/principles.md:15-17`, `.claude/skills/ai-plan/SKILL.md:42`, `.claude/skills/ai-security/SKILL.md:1-6` |
| E-28 | No enforced naming-grammar rule | DX | MEDIUM | `.claude/skills/ai-build/SKILL.md:2-3`, `.claude/skills/ai-animation/SKILL.md:2-3`, `.claude/skills/ai-schema/SKILL.md:2-3` |
| E-29 | 50+ suppression entries with `dec_id: ""` | Fail-loud / Simpl | MEDIUM | `.ai-engineering/suppression-allowlist.yml:8-12`, `.ai-engineering/suppression-allowlist.yml:20-26`, `.ai-engineering/suppression-allowlist.yml:64-641` |
| E-30 | ai-advise/ai-guard identity confusion | DX | MEDIUM | `.claude/agents/ai-advise.md:14`, `.claude/agents/ai-build.md:67-70`, `.claude/agents/ai-verify.md:23-25` |
| E-31 | instinct-observe fires on all tools, both events | Hot-path / Simpl | LOW | `.claude/settings.json:104-121` |

---

## 6. Roadmap

Each milestone names its acceptance gate. Single-concern PR per wave (or per sub-wave for Wave 1, given blast radius).

### Wave 1 — Seal the fail-open gates (Fail-loud; principle: fail-fast / Shore)

- **M1.1** Flip `_DEFAULT_MODE` to `enforce` (E-1). Provide an explicit, documented `AIENG_HOOK_INTEGRITY_MODE=warn` dev escape hatch. *Gate:* unset-env hook run on a drifted script exits non-zero; test asserts the default.
- **M1.2** Broken-tool-equals-block (E-2, E-3). `ImportError` on `no_suppression` and `FileNotFoundError`/non-zero/empty-stdout/`JSONDecodeError` on gitleaks all raise a BLOCKER finding and exit non-zero. *Gate:* a test that hides the binary asserts a blocked verdict, not a clean one.
- **M1.3** Wire risk-acceptance TTL into the hot path (E-4). `gate_pre_push` calls `_check_risk_inline(strict=True)`; expired DEC → exit 1. *Gate:* expired-DEC fixture blocks push.
- **M1.4** Loud config errors (E-5, E-6). Malformed YAML → one-line stderr + exit 1; reserve silent defaults for genuinely absent files. Stack-drift middleware narrows its except to expected types. *Gate:* corrupted-manifest fixture exits 1 with a named error.
- **M1.5** Convert silent hook swallows to visible signals (E-7..E-10). Formatter failure, checkpoint-write failure, MCP-state failure → `hookSpecificOutput` warning JSON; no-verify-guard blocks on unparseable input. *Gate:* fault-injection tests assert a surfaced signal.

### Wave 2 — Reconcile docs with code (Predictability; principle: least astonishment + PEP 20 explicit)

- **M2.1** Reconcile the agent contract (E-11). Either add an `agents.registry` section to `manifest.yml` enumerating all agent files with role + dispatch parent, or rewrite `CLAUDE.md:79-80` to separate "9 user-facing `ai-*` agents" from the internal review/verifier agent families with a linked index. *Gate:* a test asserts the count in CLAUDE.md equals files on disk.
- **M2.2** Document the 8 escape-hatch env vars (E-12) in CLAUDE.md's Runtime table with defaults and a risk annotation on `AIE_MCP_HEALTH_FAIL_OPEN`. *Gate:* a test greps hooks for `os.environ`/`getenv` `AIENG_*`/`AIE_*` reads and asserts each appears in the table.

### Wave 3 — One obvious way (Simplification; principle: PEP 20 one-way + Anthropic tool design)

- **M3.1** De-collide skill triggers (E-16..E-20). Assign each contested phrase to exactly one skill; the rest cross-reference it. Apply Anthropic's rule: if a human cannot say which skill fires, neither can the agent.
- **M3.2** Collapse near-duplicates (E-21, E-22). Fold `ai-session-watch` into `ai-learn --session`; clarify `ai-code` vs `ai-build` (subcomponent vs gateway); make `ai-spec-draft` visible in the canonical chain as the optional pre-step.
- **M3.3** One branch-cleanup (E-23). Delegate `maintenance branch-cleanup` to the richer `cleanup branches` path; document the deprecation in CHANGELOG (hard-rename, no shim). *Gate:* `tests/architecture` asserts a single implementation import.

### Wave 4 — Deterministic "done" (Determinism; principle: Bazel hermeticity)

- **M4.1** Split the STOP decision (E-25). Deterministic layer (tool exit codes → BLOCKER/CRITICAL) auto-STOPs; advisory LLM layer escalates but does not silently pass or block without an explicit signal. *Gate:* same-diff replay yields the same STOP verdict.
- **M4.2** Tag every finding `method: deterministic|llm` in the `/ai-verify` output contract (E-26) so callers threshold tool findings and LLM findings differently. *Gate:* contract test asserts the field is present.

### Wave 5 — Poka-yoke the conventions (DX; principle: Shingo + pit-of-success)

- **M5.1** §10.x citation CI test (E-27), modeled on `tests/unit/hooks/test_canonical_events_count.py`. Backfill the 22 Workflow-but-no-citation skills first. *Gate:* test fails if any `## Workflow` lacks a §10.x anchor.
- **M5.2** Document the naming-grammar rule (E-28) in `ai-scaffold` + CONSTITUTION.md; normalize outliers via hard-rename.
- **M5.3** Dry-run-by-default for destructive CLI verbs (E-24). `cleanup branches` with no mode flag prints a plan and requires confirmation. *Gate:* no-flag invocation deletes nothing.
- **M5.4** Enforce DEC-binding on suppression entries (E-29). Allowlist load fails loud (or warns per-entry on every gate run) for any `dec_id: ""`; security-rule suppressions (`nosemgrep`) are hard-required to carry a DEC. *Gate:* load-time assertion.

---

## 7. Definition of Done

1. With all env vars unset, no gate exits 0 when its tool is absent, broken, or its input malformed (E-1..E-10).
2. Every doc claim about config/agents/env vars resolves to a real on-disk fact, asserted by CI (E-11, E-12).
3. Every datum has exactly one canonical writable store; the decision-store and gate-findings duals are either migrated or carry an in-code staleness contract referencing the doctrine (E-13..E-15).
4. No skill trigger phrase routes ambiguously; a human can name the single skill for any phrase in the descriptions (E-16..E-22).
5. One branch-cleanup implementation; destructive CLI verbs default to dry-run/confirm (E-23, E-24).
6. The STOP verdict for an identical diff is reproducible; findings are tagged deterministic vs LLM (E-25, E-26).
7. CI enforces §10.x citation, naming grammar, and suppression DEC-binding; backfill complete (E-27..E-29).
8. CHANGELOG documents every hard-rename and behavior change; no backwards-compat shims (`CONSTITUTION.md:70-73`, `CLAUDE.md:110-112`).

---

## 8. Quality Stamps

| Principle | How this brief honors it |
|-----------|--------------------------|
| §10.1 KISS | One obvious way per task; collapse twins (Wave 3) |
| §10.2 YAGNI | No new features; only removes traps and ambiguity |
| §10.4 DRY | One SSOT per datum (Wave 1/2); one branch-cleanup (Wave 3) |
| §10.3 SOLID | Single-responsibility skill triggers; tool adapter raises into the port (Wave 1, 4) |
| §10.5 TDD | Every milestone lands behind a failing-first CI test (Waves 1–5 gates) |
| §10.6 SDD | This brief precedes the spec; spec precedes code |
| §10.7 Clean Code | Names predict behavior (Wave 5 naming rule) |
| §10.8 Hexagonal | Gate/verify port boundary hardened — broken adapter cannot return a clean result (Wave 1) |

Contracts honored: `CONSTITUTION.md:64-73` / `CLAUDE.md:102-112` (secrets gate, no suppression, hard rename/no shims), `CLAUDE.md:116-119` (bounded fail-loud loop), and `CLAUDE.md:122-126` (SSOT per datum). No emojis; no machine-absolute paths.

---

## 9. Open Decisions

The spec phase must resolve these:

1. **Integrity default migration** — flipping to `enforce` (M1.1) may break dev workflows where hooks change without manifest regeneration. Ship with a loud first-run hint, or gate behind a one-release deprecation warning?
2. **Agent registry** — author a real `agents.registry` in `manifest.yml` (single source, more work) or fix the doc to point at `.claude/agents/` as the source (less work, leaves count split across 4 file families)?
3. **decision-store.json migration** — finish the 12-caller migration now (closes E-13/E-14 fully) or land a tracked staleness contract + CI caller-count ratchet as an interim?
4. **Skill collapse boundaries** — does `ai-session-watch` fold into `ai-learn`, or do both stay with sharpened triggers? Operator muscle memory vs. simplification.
5. **STOP determinism** — is the deterministic layer allowed to be the *sole* auto-STOP authority, or must an LLM-flagged blocker also be able to STOP (with operator confirm)?
6. **Suppression DEC-binding enforcement** — fail-loud at allowlist load (blocks the whole gate) or per-entry warning on every run (visible but non-blocking until expiry)?

---

## 10. Migration

Per `CONSTITUTION.md:70-73` and `CLAUDE.md:110-112`: hard rename, hard delete, hard migration — no backwards-compat shims.

- **Renames** (Wave 3/5): skill collapses and naming normalization are hard renames. CHANGELOG records old→new; no alias skills retained.
- **Behavior flips** (Wave 1): the integrity default and broken-tool-blocks are behavior changes; documented in CHANGELOG with the dev escape hatch called out explicitly.
- **Dual-store removal** (Wave 2/3): decision-store.json is removed from the authoritative control plane once the 12-caller migration lands; until then it carries a `# dual-write-pending` marker and a CI ratchet, not a shim.
- **CLI**: `maintenance branch-cleanup` becomes a thin delegation to `cleanup branches`; the deprecation is documented, not silently aliased.

No data migration is required for state.db (the canonical store already holds decisions); only the *reader* config in `context_packs.py`/`framework_defaults.py` changes.

---

## 11. Risks

Likelihood × Impact, with mitigations.

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Flipping integrity to `enforce` blocks dev sessions with drifted hooks | Medium | Medium | Loud first-run hint naming the `=warn` escape hatch + `regenerate-hooks-manifest.py` command |
| Broken-tool-blocks turns a missing binary into a hard CI failure | High | Medium | Intended — but ship with a crisp error naming the missing tool and install command (Anthropic "solve don't punt") |
| Skill trigger reassignment breaks operator muscle memory | Medium | Low | CHANGELOG + cross-references; no behavior loss, only routing clarity |
| decision-store migration touches 12 callers, risk of regression | Medium | High | Land behind the existing dual-write + CI caller-count ratchet; migrate incrementally, never increase the count |
| STOP-determinism split changes which work auto-escalates | Medium | Medium | Replay-test the verdict on a corpus of past diffs before cutover |
| §10.x backfill across 45 skills is churny | High | Low | Mechanical; one PR, behind the CI test that defines "done" |
| Suppression DEC-binding flips 50+ entries to blocking | Medium | High | Per-entry warning first (visible), hard-block only after DECs are authored or entries expire 2026-07-10 |

---

## 12. References

External prior art and explanatory references:

1. Poka-yoke — Shigeo Shingo, *Zero Quality Control: Source Inspection and the Poka-Yoke System* (1986). Prevention vs detection modes; the system absorbs error responsibility. https://en.wikipedia.org/wiki/Poka-yoke
2. Principle of Least Astonishment — behavior must match reasonable user expectation. https://en.wikipedia.org/wiki/Principle_of_least_astonishment
3. Fail Fast — James Shore, *IEEE Software*, Sept/Oct 2004. Visible early failure beats silent fallback. https://www.jamesshore.com/v2/blog/2004/fail-fast ; mirror https://martinfowler.com/ieeeSoftware/failFast.pdf
4. Pit of Success — Rico Mariani, popularized by Jeff Atwood: make the right way the easy way. https://blog.codinghorror.com/falling-into-the-pit-of-success/
5. The Zen of Python — Tim Peters, PEP 20: "Explicit is better than implicit"; "one obvious way"; "Errors should never pass silently." https://peps.python.org/pep-0020/
6. Anthropic, *Writing effective tools for AI agents*: "If a human engineer can't definitively say which tool should be used, an agent can't be expected to do better"; namespacing, no overlapping tools, "solve don't punt." https://www.anthropic.com/engineering/writing-tools-for-agents ; skill best practices https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
7. Bazel hermeticity: deterministic actions make builds reproducible, and reproducibility makes failures diagnosable. https://bazel.build/basics/hermeticity

Internal anchors: `CLAUDE.md:98-126` (Hard Rules), `CLAUDE.md:175-184` (Runtime Tunables), `CLAUDE.md:58-66` (§11 chain), `CONSTITUTION.md:60-78` (Prohibitions), `docs/persistence-doctrine.md:22-33` (four-tier model), `.claude/skills/ai-spec-draft/SKILL.md:41-59` (this skill's contract).

---

## 13. Glossary

- **Fail-open** — a gate that, when it cannot do its job (tool missing, parse error), allows the action and exits clean. The trap this brief targets.
- **Fail-loud / fail-fast** — surfacing an error immediately and visibly, refusing to proceed, rather than silently working around it.
- **Poka-yoke** — mistake-proofing: design that makes the wrong action impossible or immediately obvious.
- **Pit of success** — a design where the default, easiest path is the correct path.
- **SSOT (per datum)** — every datum has exactly one canonical writable store; caches are labelled and rebuildable (`CLAUDE.md:122-126`).
- **Derived cache** — a non-canonical store rebuilt from the SSOT on demand; must be explicitly labelled with its rebuild command.
- **Trigger collision** — two or more skill descriptions claiming the same trigger phrase with no deterministic discriminator.
- **Bounded quality loop** — `/ai-build` / `/ai-autopilot` Phase 5: one finding-scoped remediation pass, then a terminal reassessment; remaining blocker/critical/high STOP and escalate (`CLAUDE.md:116-119`).
- **No-suppression rule** — current `CONSTITUTION.md` prohibition and `CLAUDE.md` hard rule banning `noqa`/`nosec`/`ts-ignore`/`nolint`/`pragma: no cover`/`NOSONAR` (`CONSTITUTION.md:66-69`, `CLAUDE.md:106-109`).
- **DEC** — a recorded decision (e.g., risk acceptance) with an id and TTL; suppression entries must bind to one.
- **Control plane** — the set of files treated as authoritative configuration/state fed to sessions.
- **Hot path** — pre-commit (<1s) and pre-push (<5s) hook execution windows (CLAUDE.md Hot-Path Discipline).

---

## 14. Acceptance

Checklist form of the Definition of Done. Each item is independently verifiable.

- [ ] With all `AIENG_*`/`AIE_*` env vars unset, hook integrity defaults to `enforce` and a drifted hook exits non-zero (E-1).
- [ ] Hiding the gitleaks binary or the `no_suppression` module yields a BLOCKED gate, not a clean pass (E-2, E-3).
- [ ] An expired risk-acceptance DEC blocks `gate pre-push` (E-4).
- [ ] A malformed `manifest.yml` exits 1 with a named error rather than returning silent defaults (E-5, E-6).
- [ ] Formatter / checkpoint / MCP-state failures emit a surfaced warning; an unparseable command is blocked by no-verify-guard (E-7..E-10).
- [ ] CI asserts the agent count and that every read `AIENG_*`/`AIE_*` env var is documented (E-11, E-12).
- [ ] Decisions and gate-findings each have one canonical store or a marked, ratcheted staleness contract (E-13..E-15).
- [ ] No skill trigger phrase routes ambiguously; collapses landed (E-16..E-22).
- [ ] One branch-cleanup implementation; destructive CLI verbs default to dry-run/confirm (E-23, E-24).
- [ ] Identical-diff STOP verdict is reproducible; findings carry `method: deterministic|llm` (E-25, E-26).
- [ ] CI enforces §10.x citation, naming grammar, and suppression DEC-binding; backfill complete (E-27..E-29).
- [ ] CHANGELOG documents every hard-rename and behavior flip; zero backwards-compat shims (`CONSTITUTION.md:70-73`, `CLAUDE.md:110-112`).
