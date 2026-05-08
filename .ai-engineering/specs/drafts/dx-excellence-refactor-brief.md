# DX Excellence Refactor — Master Feedback Brief

> **Audience**: `/ai-brainstorm` → `/ai-plan` → `/ai-build` (or `/ai-autopilot`).
> **Branch**: `feat/spec-126-hook-ndjson-lock-parity`.
> **PR**: [#506](https://github.com/arcasilesgroup/ai-engineering/pull/506) (active — this work ships inside it).
> **Authoring lens**: Staff Principal Architect, IQ-200 calibration. KISS · YAGNI · DRY · SOLID · SDD · TDD · Clean Code · Hexagonal Architecture.
> **Authoring standard for skills**: Anthropic `skill-creator` SKILL.md (canonical reference). Cited inline as `[SC]`.
> **Status**: feedback distilled from raw operator notes + parallel evidence sweep (`ai-explore` audit, `general-purpose` debug investigation, Anthropic web research, NotebookLM context).

---

## 0. North Star (the picture every wave must hold)

> A first-time engineer types `/ai-start`, sees one canonical chain, and reaches a merged PR without ever asking "which command?". Every skill self-describes. Every script is deterministic before the LLM thinks. Every IDE behaves identically. Every governance file owns one job and one job only.

The framework currently fails this test on six axes — each one is a milestone below.

```
                ┌──────────────────────────────────────────────────────────┐
                │  /ai-start  →  one chain  →  one PR  →  one source-of-truth │
                └──────────────────────────────────────────────────────────┘
                                         │
        ┌────────────┬─────────────┬─────┴──────┬──────────────┬────────────────┐
        ▼            ▼             ▼            ▼              ▼                ▼
   M1 Naming   M2 MD Canon   M3 Det. Layer   M4 Flow      M5 Models &     M6 Quality &
   & Surface   (CONSTITUTION  (skill = port,  (single       Dispatch         Hooks
   Ergonomics  / AGENTS / *)   script = port)  chain, no    economics       hardening
                                               twin paths)
```

---

## 1. Operator Pains (verbatim signals → diagnosed root cause)

| # | Operator signal | Diagnosed root cause | Owning milestone |
|---|---|---|---|
| 1 | `/ai-commit` then `/ai-pr` feels like double-execution | **Confirmed.** `.claude/skills/ai-pr/SKILL.md:28-32` reads "READ `.claude/skills/ai-commit/SKILL.md` and execute steps 0-6 in full". Running both = duplicate work. | M4 |
| 2 | Two flow shapes coexist (`…→commit→pr` and `…→build→pr`) | Documented in `AGENTS.md` and `CLAUDE.md` Step 0 as *the* chain, but `/ai-autopilot` is a parallel mega-mode and `/ai-build` already chains commit+pr after the last task. Three flows in three files. | M4 |
| 3 | Codex only has `AGENTS.md`, no companion / Gemini CLI + Antigravity broken | **Reframed after research.** Codex reads root `AGENTS.md` natively — no companion needed (no GAP). The real defect is Gemini CLI + Antigravity discovery: they read **root** `GEMINI.md` (and `~/.gemini/GEMINI.md` user-global), NOT `.gemini/GEMINI.md` inside the repo. Today the framework duplicates the file at root + `.gemini/`, but the in-repo `.gemini/GEMINI.md` is non-canonical for both tools. AGENTS.md is README-style today; Boris/Karpathy reference: AGENTS.md should be IA-optimised, terse, machine-first. | M2 |
| 4 | SOLID/KISS/DRY/YAGNI/TDD/SDD/clean-code/hex-arch live nowhere global | Scattered across `CONSTITUTION.md` Articles, individual SKILL.md "Workflow" sections, and `CLAUDE.md` "Hot-Path Discipline". No single global statement. | M2 |
| 5 | CONSTITUTION should be **user-defined**, not auto-generated | `/ai-constitution` (`.claude/skills/ai-constitution/SKILL.md`) currently generates and rewrites Articles I-XIII from a template. That violates user authorship of the non-negotiables. | M2 |
| 6 | Docs (README, getting-started, CONTRIBUTING) stale | `docs/getting-started*` does not exist (audit). `README.md:405` lines duplicates the skill list and seven-step chain from AGENTS.md. | M2 |
| 7 | Skills should have a deterministic preprocessor | Today only some skills (e.g. `/ai-cleanup`, `/ai-board`) have scripts. Most skills (e.g. `/ai-commit`, `/ai-cleanup`, `/ai-eval`, `/ai-prompt`, `/ai-research`) ask the LLM to gather evidence in-context — burns tokens, slower, less deterministic. | M3 |
| 8 | PowerShell parity for Windows | `.ai-engineering/scripts/scheduled/simplify-sweep.sh` lacks `.ps1` sibling. Hooks `_lib/*.sh` (`copilot-common.sh`, `copilot-runtime.sh`) have no `.ps1` equivalents. | M1 |
| 9 | `copilot-instinct-extract.sh` is a metaphor name | Confirmed. `instinct` is not an action verb; siblings (`guard`, `deny`, `agent`) use action verbs. Plus `copilot-instinct-observe.sh` makes the cluster worse. | M1 |
| 10 | Need a model/effort/dispatch brainstorm | Not currently formalised. Each skill picks its own model implicitly. | M5 |
| 11 | `/ai-plan` should be exhaustive, patch-ready (so `/ai-build` can use a cheap model) | Today plan.md has tasks but rarely concrete patches. `/ai-build` re-derives most of the design at execution time. | M5 |
| 12 | `/ai-autopilot` ceremonies feel heavy | Phase 5 (QUALITY LOOP) re-runs verify+guard+review on the full changeset *after* Phase 4's per-task gates. Distinction (per-task vs integration) not stated in SKILL.md. | M4 |
| 13 | `/ai-brainstorm` step 0 references `state/specs/<slug>.json` correctly | **Audit verdict: line is correct** (`.claude/skills/ai-brainstorm/SKILL.md:23-30`). False positive in raw feedback — note in M2 acceptance: clarify by example. | M2 |
| 14 | `.github/skills/ai-brainstorm/handlers/prompt-enhance.md` vs `.github/skills/ai-prompt/SKILL.md` | Partial overlap (not duplicate). Handler reimplements 2 of `/ai-prompt`'s 7 techniques. Should delegate to `/ai-prompt`. | M3 |
| 15 | `/ai-research` tier mechanism unclear vs `/ai-explore` | Audit verdict: functionally distinct (research = external evidence with citations; explore = codebase). But the descriptions don't make it obvious. | M1 / M2 |
| 16 | `prompt-injection-guard` blocks legit `rg/grep` from sub-agents, exits with empty stderr | **Confirmed root cause**: hook-integrity gate at `_lib/hook-common.py:526-529` exits non-zero with no stderr (only NDJSON). Claude shows it as "No stderr output". Also: `.claude/settings.json:19` `Bash(*--no-verify*)` is a substring glob (false-positives on env-var prefixes / unrelated args). Sub-agents not differentiated from main thread. | M6 |
| 17 | `keyring` DNS error during `uv sync` | **Informational only — operator was offline at the time, not a bug.** Investigation (kept for context, no action): `pyproject.toml:13` ships `keyring>=25.0,<26.0` as a core dep used only when `UV_KEYRING_PROVIDER=subprocess` is set (private feeds). Lockfile pins `keyring==25.7.0` with sha256 (`uv.lock:1209-1223`) → integrity intact under any DNS condition; the failure was strictly an availability symptom of the offline window. **No change requested.** | — (informational) |
| 18 | `/ai-explore` parallel dispatch errors (the trace pasted by user) | Same root cause as #16 — sub-agent's rg/grep blocked by integrity hook, then `AIENG_HOOK_INTEGRITY_MODE=off` prefix denied by overly-broad deny rule. | M6 |
| 19 | `/ai-cleanup` should consolidate finalised specs (delete spec, append `_history`, leave slot ready) | Audit: `/ai-cleanup` reaps DRAFT specs but does **not** rotate `_history.md` (`/ai-cleanup` SKILL.md never references `_history.md`). | M4 |
| 20 | `/ai-brainstorm`, `/ai-pr`, `/ai-cleanup` need a "spec consolidation" quick action | New: a single `--consolidate` flag/handler shared across the three. | M4 |

---

## 2. Final Architecture (the picture)

### 2.1 Hexagonal layout (one diagram, both for skills and the framework runtime)

```
                ┌────────────────────────────────────────────────────────┐
                │                 USER (engineer at terminal)            │
                └──────────────────────┬─────────────────────────────────┘
                                       │ slash command
                          ┌────────────┴────────────┐
                          │  IDE adapter (port)     │  ← Claude / Codex / Gemini / Copilot
                          │  .claude/.codex/.gemini │
                          └────────────┬────────────┘
                                       │ canonical SKILL.md
                                       ▼
        ┌─────────────────────── DOMAIN (skill kernel) ─────────────────────────┐
        │                                                                      │
        │   tools/skill_domain/    ← pure logic, no I/O                        │
        │   tools/skill_app/       ← orchestration, calls ports                │
        │                                                                      │
        └────────┬────────────────────────────────────┬────────────────────────┘
                 │                                    │
                 ▼                                    ▼
       ┌───────────────────┐                ┌──────────────────────┐
       │ tools/skill_infra │                │ deterministic        │
       │ (filesystem, git, │                │ preprocessors        │
       │ network, NDJSON)  │                │ (per skill scripts/) │
       └───────────────────┘                └──────────────────────┘
```

Layer-isolation test (`test_layer_isolation.py`) already enforces domain ⊥ infra — we extend the principle to **every skill**: each skill is a port; its `scripts/` directory is the deterministic adapter that emits compact context the LLM consumes.

### 2.2 The single canonical chain (no twin paths)

```
/ai-start
   │
   ▼
[brainstorm] → [plan] → [build] ──────────────► [pr]
                          │                       ▲
                          └─ (autopilot mode) ────┘
                              decompose → wave-N → quality-loop
```

- `/ai-commit` becomes an **internal phase** of `/ai-pr` (dispatch-only, never user-facing). Operators who only want a commit invoke `/ai-pr --commit-only`.
- `/ai-autopilot` is a **mode** of `/ai-build` (`/ai-build --autopilot`), not a parallel skill. Same kernel, decomposition wrapper.
- `/ai-cleanup` runs implicitly after `/ai-pr` merge. Manual invocation = explicit hygiene sweep.
- `/ai-verify` and `/ai-review` are gates — invoked by `/ai-build` per task and by `/ai-pr` pre-push. Manual invocation only when the operator wants an audit outside the chain.

### 2.3 Markdown Canon — strict content contracts

> **Convention map (verified against primary sources, 2026-05)**: `AGENTS.md` is the open cross-IDE standard stewarded by the Agentic AI Foundation (Linux Foundation). **However, no IDE except Antigravity and Copilot reads AGENTS.md as a *primary* lookup** — Claude Code, Gemini CLI, and Codex each have their own native filename. The bridge pattern is to import AGENTS.md from each native file (or symlink) so the cross-tool SSOT propagates without duplication.

**Canonical lookup — primary sources verbatim**

| IDE / Tool | Native lookup (default, no config) | Reads AGENTS.md natively? | Bridge to AGENTS.md | Primary source |
|---|---|---|---|---|
| **Codex CLI** | `AGENTS.override.md` → `AGENTS.md` (walked from git root down to cwd; "at most one file per directory"; "files closer to your current directory override earlier guidance") | ✅ **Yes — AGENTS.md *is* the native filename** | n/a | [`developers.openai.com/codex/guides/agents-md`](https://developers.openai.com/codex/guides/agents-md) |
| **Claude Code** | Managed policy → `~/.claude/CLAUDE.md` → `<repo>/CLAUDE.md` or `<repo>/.claude/CLAUDE.md` → `<repo>/CLAUDE.local.md` → nested `CLAUDE.md` in subdirs (JIT). `.claude/rules/*.md` loads at launch unless `paths:` frontmatter is set | ❌ **No. Verbatim Anthropic: "Claude Code reads `CLAUDE.md`, not `AGENTS.md`."** | `CLAUDE.md` with `@AGENTS.md` import (5-hop limit), or `ln -s AGENTS.md CLAUDE.md` (Unix; Windows requires Admin) | [`code.claude.com/docs/en/memory`](https://code.claude.com/docs/en/memory) |
| **Gemini CLI** | `~/.gemini/GEMINI.md` (global) → `<repo>/GEMINI.md` + parent dirs up to trusted root → JIT in accessed subdirs | ❌ Default no — but configurable | `.gemini/settings.json`: `{ "context": { "fileName": ["AGENTS.md","GEMINI.md"] } }` | [`google-gemini/gemini-cli` docs/cli/gemini-md.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md) |
| **Antigravity** (Google IDE, v1.20.3+, 2026-03-05) | System Rules → `GEMINI.md` (highest user) → `AGENTS.md` → `.agent/rules/*`. Global at `~/.gemini/` (note: collides with Gemini CLI per [issue #16058](https://github.com/google-gemini/gemini-cli/issues/16058)) | ✅ Yes (since v1.20.3) | n/a | [antigravity.codes/blog/user-rules](https://antigravity.codes/blog/user-rules) |
| **GitHub Copilot** | `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md` + `AGENTS.md` + `CLAUDE.md`/`GEMINI.md` (all loaded together; precedence is personal > repo > org for *types*, not for *files*) | ✅ Yes (added 2025-08-28) | n/a | [GitHub Docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions) |
| **Cursor / Windsurf** | `AGENTS.md` per Linux Foundation standard | ✅ Yes | n/a | agentsmd.org compatibility list |

**Implications (corrected from prior draft)**

1. ❌ **Wrong before**: "Claude Code reads root AGENTS.md as a fallback." Anthropic's docs state the opposite verbatim. **Right**: Claude Code requires `CLAUDE.md` with `@AGENTS.md` import or a symlink.
2. ❌ **Wrong before**: "Codex needs no companion." **Right** *and unchanged*: Codex uses `AGENTS.md` directly — the cross-tool SSOT IS Codex's native file. So the file at `<repo>/AGENTS.md` does double duty.
3. ❌ **Wrong before**: "Gemini CLI doesn't read `.gemini/GEMINI.md` in-repo." **Right (verified)**: Gemini CLI walks from `~/.gemini/GEMINI.md` (user) → `<repo>/GEMINI.md` (root + parents up to trusted root) → JIT subdirs. It does **not** read `<repo>/.gemini/GEMINI.md`. Today's duplicate at `<repo>/.gemini/GEMINI.md` is dead weight.
4. **Antigravity quirk**: its global rules at `~/.gemini/GEMINI.md` collide with Gemini CLI's user-global file. Mitigation: keep workspace `GEMINI.md` at repo root and avoid editing the user-global file from this framework.
5. **Copilot reads everything**: the slim `.github/copilot-instructions.md` we keep today is fine, but Copilot will also read the project-root AGENTS.md and CLAUDE.md if present.

**Strict content contracts (per file)**

| File | Authored by | Audience | MUST contain | MUST NOT contain |
|---|---|---|---|---|
| **`<repo>/AGENTS.md`** | framework + user, machine-first (Karpathy/Boris style) | Codex (native), Antigravity (cross-tool), Copilot (cross-tool), Cursor, Windsurf, plus the *imported target* of CLAUDE.md and (optionally) GEMINI.md | global engineering principles (SOLID/KISS/DRY/YAGNI/TDD/SDD/clean-code/hex-arch), the canonical chain, surface index (skills + agents tables), Step 0 bootstrap, hard rules | IDE-specific config, READMEs, marketing copy, install instructions |
| **`<repo>/CLAUDE.md`** | framework | Claude Code only | `@AGENTS.md` import as the first non-frontmatter line + Claude-specific extras (hot-path budgets, `.claude/settings.json` policy, hooks wiring, runtime layer tunables) | content already in AGENTS.md (must point, not duplicate) |
| **`<repo>/GEMINI.md`** | framework | Gemini CLI + Antigravity | first lines = "this file mirrors AGENTS.md; see `<repo>/AGENTS.md` for the cross-tool source of truth" + Gemini/Antigravity-specific extras (`.gemini/settings.json` notes, native command list). May `cat AGENTS.md` content inline since Gemini CLI does not support `@import`; keep in sync via lint. | duplication beyond the inlined AGENTS.md content |
| **`<repo>/.gemini/settings.json`** *(new)* | framework | Gemini CLI runtime config | `{ "context": { "fileName": ["AGENTS.md", "GEMINI.md"] } }` so Gemini CLI also reads AGENTS.md natively, eliminating the inline-copy maintenance burden | — |
| **`<repo>/.gemini/GEMINI.md`** | — | **DELETE.** Gemini CLI does not read this path. Today's duplicate is dead weight. | — | — |
| **`<repo>/.github/copilot-instructions.md`** | framework | Copilot only | repo-wide instructions, native pointer "for the cross-tool SSOT see AGENTS.md"; current 33-line shape stays | duplication |
| **`<repo>/.github/instructions/*.instructions.md`** *(optional)* | framework | Copilot path-specific | scoped instructions per directory (only if a real per-path need exists; YAGNI by default) | — |
| **`<repo>/.agent/rules/*`** *(optional)* | user | Antigravity supplement | per-file workspace overrides (only when needed) | — |
| **`CONSTITUTION.md`** | **USER** (not framework) | every agent at Step 0 | project-specific non-negotiables: identity, mission, principles operator picks, prohibitions, gates, boundaries | engineering principles (those live in AGENTS.md), workflow steps, framework defaults |
| **`README.md`** | framework | humans on github.com | install, quick-start, value-prop, links to AGENTS.md and CONSTITUTION.md | skill list, agent list, seven-step chain (link to AGENTS.md) |
| **`CONTRIBUTING.md`** | framework | external contributors | dev setup, PR process, test commands, repo layout in 1 paragraph | duplication of AGENTS.md content |
| **`docs/getting-started.md`** *(new)* | framework | first-time users | 3-minute path: install → `/ai-start` → first `/ai-brainstorm` → first PR | ceremony, theory, internals |

**Bridge protocol (the only thing that keeps this DRY)**

1. `AGENTS.md` is THE source of truth.
2. `CLAUDE.md` opens with `@AGENTS.md` (5-hop import limit; OK).
3. `GEMINI.md` either (a) inlines AGENTS.md content with a CI lint that re-syncs on every commit, or (b) lives as a 5-line pointer + the framework ships `.gemini/settings.json` that adds AGENTS.md to `context.fileName`. **Option (b) is preferred** — pure DRY, no sync.
4. `.github/copilot-instructions.md` stays a 30-line pointer + Copilot-specific notes; Copilot already loads AGENTS.md natively.
5. `/ai-ide-audit` extended with **Antigravity** in its IDE matrix and verifies (a) AGENTS.md exists at root, (b) CLAUDE.md imports `@AGENTS.md`, (c) `.gemini/settings.json` lists AGENTS.md (or GEMINI.md inlines content), (d) no `.gemini/GEMINI.md` in-repo orphan, (e) no `.codex/AGENTS.md` in-repo (would be confusing dead weight).

**Strict content contracts (per file)**

| File | Authored by | Audience | MUST contain | MUST NOT contain |
|---|---|---|---|---|
| **`<repo>/AGENTS.md`** | framework + user, machine-first (Karpathy/Boris style) | Codex, Cursor, Windsurf, Copilot (fallback), Antigravity (fallback), and as concatenated context for Claude/Gemini | global engineering principles (SOLID/KISS/DRY/YAGNI/TDD/SDD/clean-code/hex-arch), the canonical chain, surface index (skills + agents tables), Step 0 bootstrap, hard rules | IDE-specific config, READMEs, marketing copy, install instructions |
| **`<repo>/CLAUDE.md`** | framework | Claude Code only | Claude-specific extras: hot-path budgets, `.claude/settings.json` policy, hooks wiring, runtime layer tunables, native pointer "read AGENTS.md first" | content already in AGENTS.md (must point, not duplicate) |
| **`<repo>/GEMINI.md`** | framework | **Gemini CLI + Antigravity** (single file serves both) | Gemini-specific extras: `.gemini/settings.json` config, native command list, Antigravity priority note, native pointer "read AGENTS.md first" | duplication of AGENTS.md content |
| **`<repo>/.gemini/GEMINI.md`** | — | **DELETE.** Gemini CLI does not read this path inside the repo (only the user-global `~/.gemini/GEMINI.md`). Today's duplicate is dead weight and confuses the maintainer. | — | — |
| **`<repo>/.github/copilot-instructions.md`** | framework | Copilot only | repo-wide instructions, native pointer "read AGENTS.md for global rules"; current 33-line shape stays | duplication |
| **`<repo>/.github/instructions/*.instructions.md`** *(optional)* | framework | Copilot path-specific | scoped instructions per directory (only if a real per-path need exists; YAGNI by default) | — |
| **`<repo>/.agent/rules/*`** *(optional)* | user | Antigravity supplement | per-file workspace overrides (only when needed) | — |
| **`CONSTITUTION.md`** | **USER** (not framework) | every agent at Step 0 | project-specific non-negotiables: identity, mission, principles operator picks, prohibitions, gates, boundaries | engineering principles (those live in AGENTS.md), workflow steps, framework defaults |
| **`README.md`** | framework | humans on github.com | install, quick-start, value-prop, links to AGENTS.md and CONSTITUTION.md | skill list, agent list, seven-step chain (link to AGENTS.md) |
| **`CONTRIBUTING.md`** | framework | external contributors | dev setup, PR process, test commands, repo layout in 1 paragraph | duplication of AGENTS.md content |
| **`docs/getting-started.md`** *(new)* | framework | first-time users | 3-minute path: install → `/ai-start` → first `/ai-brainstorm` → first PR | ceremony, theory, internals |

**The "AGENTS.md first" pattern** (applied in CLAUDE.md, GEMINI.md, copilot-instructions.md): each IDE-native file's first action is *"Read `<repo>/AGENTS.md` before anything else; this file only adds IDE-specific extras."* This is exactly what the framework's `GEMINI.md:1-10` already does — extend that pattern uniformly.

**`/ai-ide-audit` extension**: today the audit covers Claude / Codex / Gemini / Copilot. Add **Antigravity** discovery to its IDE matrix; the audit then verifies for each IDE that (a) its native primary file exists at the correct path, (b) AGENTS.md exists at root, (c) no orphan duplicates (e.g. the dead `.gemini/GEMINI.md`).

`/ai-constitution` skill **changes role**: it no longer generates Articles. It becomes a guided interview that helps the user write *their* CONSTITUTION.md (10 questions, fill-the-blank). The framework ships a *template* CONSTITUTION.md, not a generated one.

### 2.4 Deterministic Preprocessor Protocol (every skill, every IDE)

```
┌──────────────────────────────────────────────────────────────┐
│ Skill: /ai-<name>                                            │
│ Layout (mandatory):                                          │
│   .claude/skills/ai-<name>/SKILL.md      ← the port           │
│   .claude/skills/ai-<name>/scripts/                           │
│       collect-context.{sh,ps1}            ← the adapter       │
│   .claude/skills/ai-<name>/handlers/                          │
│       <step>.md                            ← LLM micro-prompts │
│   .claude/skills/ai-<name>/references/                        │
│       <topic>.md                           ← progressive disclosure (Anthropic [SC]) │
└──────────────────────────────────────────────────────────────┘
```

`collect-context` contract:

- **Input**: env vars only (`AIENG_TASK`, `AIENG_SLUG`, `AIENG_SCOPE`).
- **Output**: stdout = compact JSON (`{ "context": {...}, "budget_tokens": <int> }`). Stderr = human warnings.
- **Exit codes**: 0 ok, 1 user error, 2 system error. Never silent fail (closes the M6 hook bug class).
- **Token budget**: each preprocessor declares a ceiling; CI test enforces ≤2 KB output by default.
- **Cross-platform**: every `.sh` MUST have a `.ps1` sibling. CI gate on parity.

The LLM consumes the JSON instead of running its own discovery. Concrete example (`/ai-cleanup`): the script lists merged branches, stale specs, runtime files past TTL, and emits one JSON blob — the LLM picks the action, no `git log` calls in-context.

### 2.5 Naming Convention (5 rules, mechanically enforceable)

| # | Rule | Linter check |
|---|---|---|
| R1 | Skills / agents always prefixed `ai-` (no exceptions). | regex on `(.claude\|.codex\|.gemini\|.github)/(skills\|agents)/.*` |
| R2 | Files under `scripts/hooks/` and `handlers/` use `<verb>-<noun>.<ext>` (verb is one of: `collect`, `verify`, `emit`, `extract`, `observe`, `guard`, `enforce`, `rotate`, `consolidate`). Metaphor nouns banned (`instinct`, `strategic`, `tactical`). | banned-word list + regex |
| R3 | Lifecycle verbs are paired and unambiguous: `start`/`end` for sessions, `open`/`close` for transactions, `enable`/`disable` for features. `stop` reserved for processes that can be `start`-ed. | grep audit |
| R4 | Multi-word slugs use `-` (kebab); never `_` or camelCase in user-facing surfaces. Underscore allowed only in Python identifiers. | path linter |
| R5 | Every `.sh` has a `.ps1` sibling under the same basename; every Python entrypoint declared in `pyproject.toml`. | CI parity gate |

Rename table (current → proposed):

| Current | Proposed | Reason |
|---|---|---|
| `copilot-instinct-extract.sh` | `copilot-observation-extract.sh` | metaphor → action |
| `copilot-instinct-observe.sh` | `copilot-observation-collect.sh` | metaphor → action; verb pair |
| `copilot-strategic-compact.sh` | `copilot-context-compact.sh` | drop unmotivated adjective |
| `copilot-mcp-health.sh` | `copilot-mcp-check.sh` | verb |
| `copilot-skill.sh` | `copilot-skill-dispatch.sh` | add verb |
| `copilot-error.sh` | `copilot-error-handle.sh` | add verb |
| `copilot-runtime-stop.sh` | `copilot-session-end.sh` *(merge target)* | unify lifecycle verbs |
| `copilot-agent.sh` | `copilot-agent-dispatch.sh` | add verb |
| `.github/agents/autopilot.agent.md` | `.github/agents/ai-autopilot.agent.md` | apply R1 |
| `.github/agents/build.agent.md` | `.github/agents/ai-build.agent.md` | apply R1 |
| `.github/agents/guard.agent.md` | `.github/agents/ai-guard.agent.md` | apply R1 |
| `reviewer-*.md` (no `.agent.md` suffix) | `reviewer-*.agent.md` | uniform suffix |
| `ai-skill-tune` | `ai-skill-improve` | self-describing verb |
| `ai-prompt` (when used as enhancer in brainstorm) | delegate, do not duplicate (see M3) | DRY |
| `simplify-sweep.sh` (no .ps1) | add `simplify-sweep.ps1` | R5 |
| `_lib/copilot-common.sh` | add `_lib/copilot-common.ps1` | R5 |

### 2.6 Models & Dispatch Economics (M5 cornerstone)

A separate sub-brainstorm — but the policy stub:

- **Cheap-tier (Haiku/Mini)**: deterministic execution where the plan is patch-ready (`/ai-build` post-`/ai-plan`, `/ai-commit`, `/ai-cleanup`, `/ai-board sync`).
- **Mid-tier (Sonnet)**: synthesis with judgment (`/ai-brainstorm`, `/ai-review`, `/ai-debug`, `/ai-explain`, `/ai-research` Tier 0-2).
- **High-tier (Opus / max-effort)**: deep architecture (`/ai-plan` exhaustive mode, `/ai-autopilot` decompose, `/ai-research` Tier 3 NotebookLM, `/ai-design`).
- **Effort levels** declared in SKILL.md frontmatter (`effort: cheap|mid|high`), CI gate that the dispatched model honours the declaration.
- `/ai-plan` is the key inversion: invest more there → cheaper everywhere downstream.

### 2.7 First-time user onboarding (5 frames)

1. `git clone … && ai-eng install` → asks 3 yes/no (telemetry, engram, IDE).
2. Open IDE → `/ai-start` → dashboard shows: branch, active spec, board state, "next action" arrow.
3. `/ai-brainstorm "I want to add X"` → 3-question interrogation → `spec.md` written.
4. `/ai-plan` → patch-ready plan with checklist; user types `apruebo`.
5. `/ai-build` (or `/ai-build --autopilot`) → execute → PR opens. End.

Hick's law: every prompt offers ≤3 choices. Norman: every command shows the next affordance. Tufte: dashboard is data, not chrome. Progressive disclosure: heavy content moved to `references/` per Anthropic [SC].

---

## 3. Anti-Goals (YAGNI, explicit)

1. **No new IDE adapter beyond Claude / Codex / Gemini / Copilot** in this refactor.
2. **No skill marketplace, no plugin store**, no remote skill fetch.
3. **No new agent persona** (the 24 agents already cover the spectrum; this refactor *removes* dead ones, not adds).
4. **No backwards-compat shims** for renamed files. Hard rename, update CHANGELOG, period (per `feedback_radical_simplification.md`).
5. **No CONSTITUTION auto-generation** ever again.

---

## 4. Roadmap — Milestones, Acceptance, Order

Order is total: each milestone is a hard gate.

### M0 — Lifecycle bootstrap *(this brief)*
- Spec record minted under `.ai-engineering/state/specs/dx-excellence-refactor.json`.
- Brief copied to `.ai-engineering/specs/drafts/` (this file).
- ❑ User runs `/ai-brainstorm` against this brief, approves spec.

### M1 — Naming & Surface Ergonomics
- Apply rename table (§2.5) across `.claude/`, `.codex/`, `.gemini/`, `.github/`, `.ai-engineering/scripts/`.
- Add 5-rule lint (`tools/skill_lint/naming.py`) wired into pre-commit.
- PowerShell parity gate for `.sh` → `.ps1` siblings (CI).
- ❑ Every script under `scripts/hooks/` passes the verb-noun rule.
- ❑ `simplify-sweep.ps1` and `_lib/copilot-common.ps1` exist and are tested.
- ❑ Skill IDs deduplicated; `ai-skill-tune` → `ai-skill-improve`.
- ❑ All four IDE mirrors (`.claude`/`.codex`/`.gemini`/`.github`) byte-equivalent for canonical content (frontmatter mirrors aside).

### M2 — Markdown Canon Reset
- Rewrite `AGENTS.md` as machine-first (Karpathy/Boris style): ≤200 lines, table-driven, contains global principles (SOLID/KISS/DRY/YAGNI/TDD/SDD/clean-code/hex-arch), the canonical chain, surface index, hard rules. **This file IS Codex's native instruction surface, Antigravity's cross-tool layer, and Copilot's AGENTS.md target — it does triple duty.**
- Trim `CLAUDE.md` to a single `@AGENTS.md` import + Claude-specific extras only. Verbatim Anthropic: "Claude Code reads `CLAUDE.md`, not `AGENTS.md`" — the import is mandatory to bridge.
- **Replace** the inline-content `GEMINI.md` strategy with the settings-based bridge: write `.gemini/settings.json` containing `{ "context": { "fileName": ["AGENTS.md", "GEMINI.md"] } }` so Gemini CLI reads AGENTS.md natively. Keep root `GEMINI.md` as a 5-line pointer ("see AGENTS.md") + Gemini/Antigravity-specific extras only.
- **Delete `<repo>/.gemini/GEMINI.md`** — Gemini CLI does not look at in-repo `.gemini/` (only at user-global `~/.gemini/GEMINI.md`). Today's copy is dead weight.
- Keep `.github/copilot-instructions.md` slim (current 33-line shape); first action = "for the cross-tool SSOT see AGENTS.md". Copilot loads AGENTS.md natively since 2025-08-28, so no bridge needed.
- **Do NOT create `<repo>/.codex/AGENTS.md`** — Codex CLI reads root `AGENTS.md` natively; an in-repo `.codex/` copy would confuse maintainers.
- Reframe `CONSTITUTION.md` as **user-authored template**: ship a 60-line template with TODO blanks; `/ai-constitution` becomes a 10-question interview that fills it.
- Rewrite `README.md` (focus install + value-prop + links).
- Add `docs/getting-started.md` (5-frame onboarding).
- Update `CONTRIBUTING.md`.
- Extend `/ai-ide-audit` with **Antigravity** in its IDE matrix; assert canonical lookup paths per the table in §2.3 (existence of AGENTS.md, presence of `@AGENTS.md` import in CLAUDE.md, AGENTS.md in `.gemini/settings.json` `context.fileName`, absence of `.gemini/GEMINI.md` orphan, absence of `.codex/AGENTS.md` orphan).
- ❑ `tests/governance/test_md_canon.py`: enforces line ceilings + forbidden duplications + per-IDE canonical-path existence + import/settings bridge presence.
- ❑ Running Claude Code from repo root: `/memory` lists CLAUDE.md and confirms AGENTS.md content was loaded via `@AGENTS.md` import.
- ❑ Running Gemini CLI from repo root: context loads AGENTS.md (via `.gemini/settings.json`) plus root GEMINI.md.
- ❑ Running Codex CLI from repo root: AGENTS.md loaded; `~/.codex/config.toml` untouched.
- ❑ Antigravity v1.20.3+ loaded against the repo: GEMINI.md (highest) + AGENTS.md (cross-tool) both apply.
- ❑ Copilot loaded against the repo: `.github/copilot-instructions.md` + AGENTS.md both apply.
- ❑ Every existing reference link still resolves.

### M3 — Deterministic Preprocessor Layer
- Apply Preprocessor Protocol (§2.4) to every skill missing one.
- For each: write `scripts/collect-context.sh` + `.ps1`, declare token budget in frontmatter (`effort:` + `budget_tokens:`).
- `/ai-brainstorm/handlers/prompt-enhance.md` deletes its inline rules; calls `/ai-prompt` instead (DRY).
- `tools/skill_lint/preprocessor.py` enforces: every SKILL.md declares budget; every script returns valid JSON within budget.
- ❑ Tested skills' average input tokens drop ≥30%.
- ❑ No skill exceeds 120 lines (Anthropic [SC] progressive-disclosure threshold; current ceiling already 120).
- ❑ Every SKILL.md has `## Quick start`, `## Workflow`, `## Examples`, `## Integration` sections (already enforced by spec-127 lint — keep).

### M4 — Single Canonical Flow
- `/ai-commit` becomes internal: `/ai-pr` is the user surface; `/ai-pr --commit-only` is the rare carve-out.
- `/ai-autopilot` becomes `/ai-build --autopilot` (one skill, two modes); old slash command becomes alias for one release, then removed.
- `/ai-cleanup`, `/ai-pr`, `/ai-brainstorm` gain shared `--consolidate-spec` action (delete finalised spec, append `_history.md`, leave slot ready).
- `/ai-cleanup` SKILL.md adds explicit `_history.md` rotation step (gap found in audit).
- AGENTS.md Step 0 reflects the single chain.
- ❑ Search the codebase: zero references to "/ai-commit then /ai-pr" or twin paths.
- ❑ Operator runs `/ai-pr` from a clean branch and gets commit + push + PR in one shot, no warnings.

### M5 — Models, Effort & Dispatch Economics
- Sub-brainstorm session (`/ai-brainstorm "model dispatch policy"`) produces sub-spec.
- Add `effort:` and `model_tier:` to every SKILL.md frontmatter.
- `/ai-plan` upgraded to **exhaustive patch-ready mode**: outputs concrete diffs per task (not just descriptions). Plan checklists self-tick when tasks complete (already partly implemented).
- `/ai-build` reads plan → dispatches cheap-tier model when patches are present, mid-tier when judgment needed.
- `/ai-autopilot` Phase 5 (QUALITY LOOP) trimmed: distinguish per-task gates (Phase 4) from integration sweep (Phase 5) explicitly in SKILL.md, drop redundant guard pass.
- ❑ Token-per-PR median drops ≥40% on the dogfood corpus.

### M6 — Hooks & Robustness
- `prompt-injection-guard.py`: surface integrity failures to **stderr** (one-line reason + remediation), distinct exit code (3=integrity, 2=injection).
- `_lib/hook_context.py`: add `agent_kind` (main vs subagent) by reading transcript_path / parent session.
- Sub-agent policy lane: relaxed integrity mode, positive allow-list for read-only commands (`rg`, `grep`, `find`, `ls`, `cat` without redirect) evaluated **before** the IOC pattern loop.
- Replace `Bash(*--no-verify*)` glob with token-aware shlex matcher.
- ❑ Sub-agent runs `rg "anything"` from any path → succeeds.
- ❑ All 11 canonical hook events still emit telemetry.

> **Note on `keyring`**: investigated but **not in scope**. Operator was offline; lockfile already hash-pins (`uv.lock:1209-1223`); integrity intact. Captured in §1 row 17 as informational only.

### M7 — Documentation & Evangelism
- All MD docs updated and cross-linked.
- One end-to-end screencast script in `docs/`.
- CHANGELOG entry summarising every breaking rename (no compat shims, per anti-goal #4).
- ❑ `tests/docs/test_links.py` passes.

---

## 5. Evidence Index (file:line citations from the audit)

| Claim | Evidence |
|---|---|
| `/ai-pr` already executes `/ai-commit` 0-6 | `.claude/skills/ai-pr/SKILL.md:28-32` |
| `/ai-cleanup` does not rotate `_history.md` | `.claude/skills/ai-cleanup/SKILL.md` (full read; no mention) |
| Root `GEMINI.md` byte-identical to `.gemini/GEMINI.md` | both 59 lines, identical sections — `.gemini/GEMINI.md` is dead weight; primary source [`google-gemini/gemini-cli` docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md) confirms Gemini CLI does **not** look in `<repo>/.gemini/` (only `~/.gemini/`) |
| Codex CLI native filename = AGENTS.md | primary source [`developers.openai.com/codex/guides/agents-md`](https://developers.openai.com/codex/guides/agents-md): "Codex checks `AGENTS.override.md` first, then `AGENTS.md`" |
| **Claude Code does NOT read AGENTS.md** | primary source [`code.claude.com/docs/en/memory`](https://code.claude.com/docs/en/memory) verbatim: "Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If your repository already uses `AGENTS.md`, create a `CLAUDE.md` that imports it" — bridge via `@AGENTS.md` import or symlink |
| Antigravity priority order | `GEMINI.md` > `AGENTS.md` > `.agent/rules/` (v1.20.3, 2026-03-05); same root `GEMINI.md` serves both Gemini CLI and Antigravity |
| Copilot reads AGENTS.md natively | [GitHub Changelog, 2025-08-28](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/) |
| Gemini CLI configurable via `.gemini/settings.json` `context.fileName` | primary source: `geminicli.com/docs/reference/configuration/` — list filenames; setting `["AGENTS.md","GEMINI.md"]` makes Gemini CLI read AGENTS.md natively |
| `keyring` core dep, only used for private feeds *(informational, not a fix)* | `pyproject.toml:13,53-65` |
| `uv.lock` pins keyring with sha256 *(integrity intact under any DNS condition)* | `uv.lock:1209-1223` |
| Hook silent exit-2 path | `_lib/hook-common.py:526-529,488,458-475` |
| `Bash(*--no-verify*)` substring glob | `.claude/settings.json:19` |
| Hook lib has no subagent awareness | `_lib/hook_context.py:94,108-117` (zero matches for `subagent`) |
| `/ai-brainstorm` lifecycle bootstrap line is correct | `.claude/skills/ai-brainstorm/SKILL.md:23-30` |
| `prompt-enhance.md` reimplements 2 of 7 `/ai-prompt` techniques | `.github/skills/ai-brainstorm/handlers/prompt-enhance.md:1-25` vs `.github/skills/ai-prompt/SKILL.md:1-30` |
| `/ai-research` 4-tier model | `.claude/skills/ai-research/SKILL.md:28-35` |
| `/ai-explore` codebase-only | `.claude/agents/ai-explore.md` (137 lines, tools `[Read, Glob, Grep, Bash]`) |
| `simplify-sweep.sh` lacks `.ps1` sibling | `.ai-engineering/scripts/scheduled/simplify-sweep.sh` |
| 49 skills × 4 IDE mirrors | `.claude/skills/` (47), `.github/skills/` (46), `.codex/skills/` (47), `.gemini/skills/` (47) |
| Naming offenders (10 worst) | §2.5 rename table + audit §4 |

---

## 6. Hand-off Checklist (for `/ai-brainstorm` to consume)

- [ ] Read this brief end-to-end before any interrogation.
- [ ] Mint spec slug `dx-excellence-refactor` under `.ai-engineering/state/specs/`.
- [ ] Treat M1-M7 as 7 sub-specs; decompose via `/ai-autopilot` Phase 1 if accepted.
- [ ] Dispatch agents in parallel per wave (per operator's standing instruction `feedback_autonomous_execution.md`).
- [ ] Use Anthropic `skill-creator` standard `[SC]` as the conformance reference for any new SKILL.md authored.
- [ ] Use `context7` MCP for library docs, NotebookLM ID `b8a09700-2ce7-4d6c-84d7-82b89765ea53` for prior research, Engram for cross-session memory.
- [ ] Ship inside PR #506 — do not open a parallel PR.
- [ ] Every wave: re-anchor to §0 North Star before writing code.
- [ ] No backwards-compat shims (anti-goal #4).
- [ ] No CONSTITUTION auto-generation (anti-goal #5).

---

## 7. Source Discipline

This brief was synthesised from:
- Operator raw feedback (the prompt that triggered this work).
- Parallel `ai-explore` audit run on PR #506 HEAD (full skill / agent / MD inventory + naming + duplication checks).
- Parallel `general-purpose` debug investigation (hook + keyring root cause).
- Anthropic `skill-creator` SKILL.md (canonical authoring standard).
- Anthropic engineering blog on Agent Skills.
- Engram session memory (`spec-127 autopilot Phase 1 decompose complete`, obs #69).
- NotebookLM research notebook `b8a09700-2ce7-4d6c-84d7-82b89765ea53` (consulted via web reference; deeper extraction belongs in M5 sub-brainstorm).

Every claim above is anchored to a file:line or external citation. Operator preferences honoured: anonymous, no PII, no machine-specific paths in committed files, autonomous execution allowed once approved.
