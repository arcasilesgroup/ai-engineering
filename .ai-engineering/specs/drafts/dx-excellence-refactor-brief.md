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
| 1 | `/ai-commit` then `/ai-pr` feels like double-execution | **Confirmed.** `.claude/skills/ai-pr/SKILL.md:28-32` reads "READ `.claude/skills/ai-commit/SKILL.md` and execute steps 0-6 in full". The fix is workflow-level, not skill-level: the canonical chain stops mentioning `/ai-commit` (it's implicit inside `/ai-pr`). `/ai-commit` stays available as a **standalone** skill for the rare WIP-only case. | M4 |
| 2 | Two flow shapes coexist (`…→commit→pr` and `…→build→pr`) | Documented in `AGENTS.md` and `CLAUDE.md` Step 0 as *the* chain. The fix is workflow-level: chain stops mentioning `/ai-commit` (it's implicit inside `/ai-pr`). `/ai-autopilot` stays a separate user-invocable skill (different scope from `/ai-build`); the "two flows" perception goes away once docs show ONE chain. | M4 |
| 3 | AGENTS.md, CLAUDE.md, GEMINI.md, copilot-instructions.md must hold the same "how AI works" payload — Gemini CLI + Antigravity currently broken | **Reframed (final).** All four files are **mirror copies** carrying identical content (Karpathy + Boris + migrated AI-behaviour from CONSTITUTION.md). Each lives at its IDE-native path. No imports / no bridges / no cross-refs. Lint enforces sha256 equivalence; `make sync-md` rewrites the three mirrors from AGENTS.md. Delete `<repo>/.gemini/GEMINI.md` (Gemini CLI does not read in-repo `.gemini/`); never create `<repo>/.codex/AGENTS.md` (Codex reads root). | M2 |
| 3b | CONSTITUTION.md contains AI-behaviour content that does not belong there | CONSTITUTION = project-specific (what THIS project is). AI-behaviour migrates out into the four mirrors. `/ai-constitution` is refactored: it interviews the operator and produces project identity (mission, stakeholders, vocabulary, prohibitions, compliance gates), not engineering principles. | M2 |
| 4 | SOLID/KISS/DRY/YAGNI/TDD/SDD/clean-code/hex-arch live nowhere global | Scattered across `CONSTITUTION.md` Articles, individual SKILL.md "Workflow" sections, and `CLAUDE.md` "Hot-Path Discipline". No single global statement. | M2 |
| 5 | CONSTITUTION should be **project-specific**, not AI-behaviour | `/ai-constitution` keeps generating CONSTITUTION.md, but **with a redirected scope**: it interviews the operator about the project's identity (mission, stakeholders, vocabulary, prohibitions, compliance gates), not about engineering principles. The AI-behaviour content currently in CONSTITUTION.md migrates into the four canonical mirrors (AGENTS / CLAUDE / GEMINI / copilot-instructions). | M2 |
| 6 | Docs (README, getting-started, CONTRIBUTING) stale | `docs/getting-started*` does not exist (audit). `README.md:405` lines duplicates the skill list and seven-step chain from AGENTS.md. | M2 |
| 7 | Skills should have a deterministic preprocessor | Today only some skills (e.g. `/ai-cleanup`, `/ai-board`) have scripts. Most skills (e.g. `/ai-commit`, `/ai-cleanup`, `/ai-eval`, `/ai-prompt`, `/ai-research`) ask the LLM to gather evidence in-context — burns tokens, slower, less deterministic. | M3 |
| 8 | PowerShell parity for Windows | `.ai-engineering/scripts/scheduled/simplify-sweep.sh` lacks `.ps1` sibling. Hooks `_lib/*.sh` (`copilot-common.sh`, `copilot-runtime.sh`) have no `.ps1` equivalents. | M1 |
| 9 | `copilot-instinct-extract.sh` is a metaphor name | Confirmed. `instinct` is not an action verb; siblings (`guard`, `deny`, `agent`) use action verbs. Plus `copilot-instinct-observe.sh` makes the cluster worse. | M1 |
| 10 | Need a model/effort/dispatch brainstorm | Not currently formalised. Each skill picks its own model implicitly. | M5 |
| 11 | `/ai-plan` should be exhaustive, patch-ready (so `/ai-build` can use a cheap model) | Today plan.md has tasks but rarely concrete patches. `/ai-build` re-derives most of the design at execution time. | M5 |
| 12 | `/ai-autopilot` + `/ai-build` ceremonies feel heavy (per-task + final loop = double gate work) | **Final design**: drop per-task verify+review in BOTH skills (each task self-validates via TDD §10.5). Add ONE end-of-implementation quality loop, single round, in BOTH skills. ~90% gate-run reduction; ~13-19 min + ~1.3-1.8M tokens saved per 10-task spec. Fail-loud (STOP on blockers, no auto-retry). | M4 |
| 13 | `/ai-brainstorm` step 0 references `state/specs/<slug>.json` correctly | **Audit verdict: line is correct** (`.claude/skills/ai-brainstorm/SKILL.md:23-30`). False positive in raw feedback — note in M2 acceptance: clarify by example. | M2 |
| 14 | `.github/skills/ai-brainstorm/handlers/prompt-enhance.md` vs `.github/skills/ai-prompt/SKILL.md` | Partial overlap (not duplicate). Handler reimplements 2 of `/ai-prompt`'s 7 techniques. Should delegate to `/ai-prompt`. | M3 |
| 15 | `/ai-research` tier mechanism unclear vs `/ai-explore` | Audit verdict: functionally distinct (research = external evidence with citations; explore = codebase). But the descriptions don't make it obvious. | M1 / M2 |
| 16 | `prompt-injection-guard` blocks legit `rg/grep` from sub-agents, exits with empty stderr | **Confirmed root cause**: hook-integrity gate at `_lib/hook-common.py:526-529` exits non-zero with no stderr (only NDJSON). Claude shows it as "No stderr output". Also: `.claude/settings.json:19` `Bash(*--no-verify*)` is a substring glob (false-positives on env-var prefixes / unrelated args). Sub-agents not differentiated from main thread. | M6 |
| 17 | `keyring` DNS error during `uv sync` | **Informational only — operator was offline at the time, not a bug.** Investigation (kept for context, no action): `pyproject.toml:13` ships `keyring>=25.0,<26.0` as a core dep used only when `UV_KEYRING_PROVIDER=subprocess` is set (private feeds). Lockfile pins `keyring==25.7.0` with sha256 (`uv.lock:1209-1223`) → integrity intact under any DNS condition; the failure was strictly an availability symptom of the offline window. **No change requested.** | — (informational) |
| 18 | `/ai-explore` parallel dispatch errors (the trace pasted by user) | Same root cause as #16 — sub-agent's rg/grep blocked by integrity hook, then `AIENG_HOOK_INTEGRITY_MODE=off` prefix denied by overly-broad deny rule. | M6 |
| 18b | `/ai-start` slow + inconsistent across IDEs | Operator tested 4 IDE/model combos; each dispatched 6-10+ ad-hoc probes (manifest, LESSONS, decisions, gh project) instead of trusting `session_bootstrap.py`. Copilot RTK hook denied bash until rewritten. Claude hit `node: command not found`. Engram tool prefix doc mismatch (`mcp__engram__*` vs `mcp__plugin_engram_engram__*`). | M3 (preprocessor canary, see §2.4.1) + M6 (hook trusted-script lane + node fallback + engram doc fix) |
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
[brainstorm] → [plan] → [build] ──► [pr]      ← default chain (small/medium spec)
                                       ▲
                                       │ (commit pipeline runs INSIDE /ai-pr)

[brainstorm] → [autopilot] ─────────► [pr]    ← large/multi-concern spec; autopilot
                  │                              decomposes → DAG → waves → quality-loop;
                  │                              dispatches /ai-build agents per sub-spec
                  └─ Phase 4 dispatches ai-build agents internally

/ai-commit  ← standalone, off-chain. User-invoked only when WIP-only push is wanted.
```

**Two ENTRY shapes, ONE delivery surface (`/ai-pr`)**: small/medium specs go through `/ai-build` directly; large/multi-concern specs (≥3 concerns, ≥10 files) use `/ai-autopilot`. Both converge on `/ai-pr`. `/ai-build` and `/ai-autopilot` are SEPARATE skills with separate contracts (Single-Responsibility, §10.3) — `/ai-autopilot` *delegates* to `/ai-build` agents in its Phase 4, but the two skills are not interchangeable.

- `/ai-commit` **remains a standalone user-invocable skill** for the rare case where the operator wants to commit without opening a PR (e.g. WIP push, partial day-end save). It is **not part of the canonical chain** and is not invoked automatically. `/ai-pr` continues to run the commit pipeline internally as today (steps 0-6 from `ai-commit/SKILL.md`) — no `--commit-only` flag needed because `/ai-commit` exists separately.
- `/ai-autopilot` and `/ai-build` stay **separate skills** (different contracts: build = single approved plan; autopilot = decompose + DAG + waves + quality-loop). Autopilot *delegates* to build agents in Phase 4 — that's not fusion. Single-Responsibility (§10.3) keeps them apart.
- `/ai-cleanup` runs implicitly after `/ai-pr` merge. Manual invocation = explicit hygiene sweep.
- `/ai-verify` and `/ai-review` are gates — invoked by `/ai-build` per task and by `/ai-pr` pre-push. Manual invocation only when the operator wants an audit outside the chain.

### 2.3 Markdown Canon — Mirror Strategy

> **Architectural decision (operator-driven)**: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md` carry **identical content** — they are mirror copies, not refs. No `@import` bridges, no symlinks, no cross-references. Each lives at its IDE-native path with the full payload baked in. Sync is enforced by a lint, not by indirection.
>
> **Why**: every IDE's path-discovery quirks are eliminated. Claude Code reads CLAUDE.md and gets full content. Gemini CLI reads GEMINI.md and gets full content. Copilot reads `.github/copilot-instructions.md` and gets full content. Codex / Cursor / Windsurf / Antigravity read AGENTS.md and get full content. **No conditional reasoning at runtime.** The mirroring cost is paid once, in CI, by a deterministic lint.

**Native-path lookup table (verified primary sources)**

| IDE / Tool | Native path it reads | Primary source |
|---|---|---|
| Codex CLI | `<repo>/AGENTS.md` (+ override + nesting) | [OpenAI Codex docs](https://developers.openai.com/codex/guides/agents-md) |
| Claude Code | `<repo>/CLAUDE.md` (+ user/managed/local + nesting) | [Anthropic Claude Code memory](https://code.claude.com/docs/en/memory) |
| Gemini CLI | `<repo>/GEMINI.md` (+ `~/.gemini/` + parents/JIT) | [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md) |
| Antigravity (v1.20.3+) | `<repo>/GEMINI.md` (highest user priority) | [antigravity.codes](https://antigravity.codes/blog/user-rules) |
| GitHub Copilot | `<repo>/.github/copilot-instructions.md` | [GitHub Docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions) |
| Cursor / Windsurf | `<repo>/AGENTS.md` | agents.md (Linux Foundation) |

**Content shape — what goes inside the four mirrors**

The canonical content is "how the AI works in this repo" — distilled from:
- **Andrej Karpathy's CLAUDE.md** ([forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md)): four behaviour pillars — *Think Before Coding · Simplicity First · Surgical Changes · Goal-Driven Execution*.
- **Boris's CLAUDE.md gist** ([gist:hqman/e29cb6386c539d795767e8c3fd2c959b](https://gist.github.com/hqman/e29cb6386c539d795767e8c3fd2c959b)): six workflow rules — *Plan-Mode Default · Subagent Strategy · Self-Improvement Loop · Verification Before Done · Demand Elegance · Autonomous Bug Fixing* — plus six task-management steps and three core principles (*Simplicity First · No Laziness · Minimal Impact*).
- **Material currently misplaced in `CONSTITUTION.md`** that is universal AI behaviour, not project identity: SOLID / KISS / DRY / YAGNI / TDD / SDD / clean-code / hexagonal architecture; the seven-step canonical chain; hard rules; surface index (skills + agents).

**Canonical mirror content (target table of contents)**

```
# How AI works in this repo
## 0. Bootstrap (Step 0 of every session)
## 1. Think Before Coding   — Karpathy §1
## 2. Simplicity First       — Karpathy §2 + Boris core
## 3. Surgical Changes       — Karpathy §3 + Boris "Minimal Impact"
## 4. Goal-Driven Execution  — Karpathy §4 + Boris "Verification Before Done"
## 5. Plan-Mode Default      — Boris §1
## 6. Subagent Strategy      — Boris §2
## 7. Self-Improvement Loop  — Boris §3
## 8. Demand Elegance         — Boris §5
## 9. Autonomous Bug Fixing   — Boris §6
## 10. Engineering Principles — first-class section, see breakdown below
## 11. The Canonical Chain    — /ai-brainstorm → /ai-plan → /ai-build → /ai-pr (single flow per M4)
## 12. Surface Index          — skills (49) + agents (24) tables
## 13. Hard Rules             — secrets-gate, no compat shims, anonymous feedback, etc.
```

This file is **standalone** — every operator who opens it gets the full picture without chasing imports.

**§10 Engineering Principles — first-class subsections (mandatory in the canonical payload)**

Each principle is its own subsection with: (a) one-sentence definition, (b) 3-5 concrete rules an AI agent can verify, (c) anti-pattern list, (d) example. Every skill in `/ai-*` MUST invoke at least one of these principles in its `## Workflow` section.

| Sub-§ | Principle | One-sentence definition | Concrete rules (sample) |
|---|---|---|---|
| 10.1 | **KISS** (Keep It Simple, Stupid) | Pick the smallest design that solves the stated problem. | No premature abstraction · No flexibility for unknown future · Reject configurability not asked for · Reject framework hop. |
| 10.2 | **YAGNI** (You Aren't Gonna Need It) | Do not build for hypothetical needs. | No "nice-to-have" branches · No options without a current caller · Delete dead paths on sight (only your own dead paths, per §3). |
| 10.3 | **SOLID** | Five OO design rules: single-responsibility, open-closed, Liskov, interface segregation, dependency inversion. | One file = one reason to change · Extend by composition not modification · Subtypes substitute supertypes without surprise · Small focused interfaces · Depend on abstractions not concretes. |
| 10.4 | **DRY** (Don't Repeat Yourself) | One source of truth per fact. | Constants live in one module · Sync mirrors via generators not copy-paste · Schema definitions imported, not re-declared. |
| 10.5 | **TDD** (Test-Driven Development) | Write the failing test first; make it pass; refactor. | RED-GREEN-REFACTOR loop visible in every PR · No production code without a covering test (unless explicit waiver) · Coverage report attached to /ai-pr. |
| 10.6 | **SDD** (Spec-Driven Development) | Spec → plan → code in that order; never skip the spec. | `/ai-brainstorm` mints a spec record before any code · `/ai-plan` produces patch-ready tasks · `/ai-build` cannot run without an approved plan. |
| 10.7 | **Clean Code** | Code reads like prose; intent visible at every level. | Names by intent (`user_count` not `n`) · Functions ≤ 20 lines · Guard clauses over nested ifs · Comments only when WHY is non-obvious. |
| 10.8 | **Hexagonal Architecture** | Domain at the centre; adapters at the edge; dependency arrows point inward. | `tools/skill_domain/` has zero imports from `tools/skill_infra/` (CI-enforced) · Skills = ports, scripts = adapters · Side effects only in adapter layer. |

**Why each principle is first-class** (not just a one-line mention): operators ask "did the AI apply DRY?" and "did the AI run TDD?" — those questions need a verifiable surface to point at. The `## Workflow` section of every skill cites the principles it enforces, and `/ai-verify` can be extended to grep for the citations.

**Lint integration** (`tools/skill_lint/principles.py`, new):
- Every SKILL.md `## Workflow` cites at least one §10.x principle by anchor (`§10.1`, `§10.5`, etc.).
- `/ai-plan` output template includes a "Principles applied" line per task.
- `/ai-verify` runs a "principle adherence" check (text-only audit, advisory not blocking).

**Coverage matrix — where each principle lives in the chain**

| Principle | Step that enforces it most |
|---|---|
| KISS · YAGNI · Clean Code | `/ai-build` task execution + `/ai-simplify` sweep |
| SOLID · Hexagonal | `/ai-plan` patch design + layer-isolation test |
| DRY | `scripts/sync_mirrors/core.py` + `tools/skill_lint/md_mirror.py` |
| TDD | `/ai-test` (pre-build RED) + `/ai-build` (GREEN) + `/ai-verify` (coverage gate) |
| SDD | `/ai-brainstorm` (spec mint) + `/ai-plan` (decompose) + `/ai-build` refuses w/o approved plan |

**Strict content contracts (per file)**

| File | Authored by | Lives at | Contains |
|---|---|---|---|
| **`<repo>/AGENTS.md`** | framework | repo root | full canonical content (above) |
| **`<repo>/CLAUDE.md`** | framework | repo root | **identical** to AGENTS.md (mirror) |
| **`<repo>/GEMINI.md`** | framework | repo root | **identical** to AGENTS.md (mirror) |
| **`<repo>/.github/copilot-instructions.md`** | framework | `.github/` | **identical** to AGENTS.md (mirror) |
| **`<repo>/.gemini/GEMINI.md`** | — | — | **DELETE** (Gemini CLI does not read this in-repo path) |
| **`<repo>/.codex/AGENTS.md`** | — | — | **DO NOT CREATE** (Codex reads root AGENTS.md natively) |
| **`<repo>/.github/instructions/*.instructions.md`** *(optional)* | framework | `.github/instructions/` | scoped Copilot instructions only when a per-path need exists (YAGNI by default) |
| **`<repo>/.agent/rules/*`** *(optional)* | user | `.agent/rules/` | per-file Antigravity workspace overrides (only when needed) |
| **`CONSTITUTION.md`** | **USER**, generated by `/ai-constitution` interview | repo root | **project-specific identity** — what THIS project is: domain, mission, vocabulary, primary stakeholders, prohibitions specific to this codebase, regulated-industry constraints. **Not how AI works.** |
| **`README.md`** | framework | repo root | install, quick-start, value-prop, links to AGENTS.md and CONSTITUTION.md |
| **`CONTRIBUTING.md`** | framework | repo root | dev setup, PR process, test commands, repo layout in 1 paragraph |
| **`docs/getting-started.md`** *(new)* | framework | `docs/` | 3-minute path: install → `/ai-start` → first `/ai-brainstorm` → first PR |

**`/ai-constitution` redefined**

The skill stays as a **generator** — but its output target shifts. Instead of producing AI-behaviour articles (which now live in the four mirrors), it interviews the operator about **what the project IS**:

| Interview question | Resulting CONSTITUTION.md section |
|---|---|
| "What does this project do, in one sentence?" | `## Mission` |
| "Who is the primary user / customer?" | `## Stakeholders` |
| "What domain vocabulary should the AI use? (terms, abbreviations, banned synonyms)" | `## Vocabulary` |
| "What MUST NEVER happen in this codebase? (regulatory, contractual, security)" | `## Prohibitions` |
| "What gates are non-negotiable? (e.g. SOC2, HIPAA, PCI, FDA)" | `## Compliance gates` |
| "What's out of scope, on purpose? (anti-goals)" | `## Anti-goals` |
| "What is the relationship to upstream / downstream systems?" | `## Boundaries` |
| "Who owns escalation when an agent disagrees with these rules?" | `## Escalation` |
| "What language is the codebase written in (English / Spanish / mixed)?" | `## Language` |
| "What is the current spec lifecycle phase? (greenfield / evolving / freeze)" | `## Lifecycle phase` |

Result: CONSTITUTION.md is short, project-specific, and authored by the user (with skill assistance). It complements — does not duplicate — the four AI-behaviour mirrors.

**Sync enforcement — reuse the existing mirror plumbing**

We already ship `scripts/sync_mirrors/core.py` (1871 LoC, exposed via `scripts/sync_command_mirrors.py` shim). It currently writes:
- Surface 5.5 — root `CLAUDE.md` ← `templates/project/CLAUDE.md`
- Surface 7   — root `AGENTS.md` ← own template (`generate_agents_md`)
- Surface 7.5 — root `GEMINI.md` + `.gemini/GEMINI.md` ← `templates/project/GEMINI.md`
- Surface (8 / copilot) — `.github/copilot-instructions.md` ← `generate_copilot_instructions` (today: slim, with cross-ref to AGENTS.md at `core.py:1103`)

The refactor is **internal**, not additive:
1. Promote `templates/project/CANONICAL.md` (new) as the **single authoring template** carrying the full payload (TOC above).
2. Rewrite surfaces 5.5 / 7 / 7.5 / copilot to read CANONICAL.md and emit it **byte-equivalent** at the four IDE paths (frontmatter / IDE-name banner aside; payload identical).
3. Delete the slim copilot generator's cross-ref line at `core.py:1103` ("See [AGENTS.md](../AGENTS.md) for canonical cross-IDE rules") — mirrors mean every file is self-sufficient.
4. Drop the in-repo `.gemini/GEMINI.md` write from Surface 7.5 (Gemini CLI does not read this path).
5. **No new sync entry point.** `python scripts/sync_command_mirrors.py` (or the new `scripts.sync_mirrors.core.main()`) keeps being THE single sync command, invoked by `/ai-prompt --skill`, by CI, and by manual `--check`.

`tools/skill_lint/md_mirror.py` (new, ≤80 LoC) checks on every PR:
1. The four mirror files have identical sha256 of their canonical content payload.
2. No `@AGENTS.md` import in CLAUDE.md (we mirror, not bridge).
3. No `<repo>/.gemini/GEMINI.md` orphan.
4. No `<repo>/.codex/AGENTS.md` orphan.
5. CONSTITUTION.md does NOT contain section headers from the canonical AI-behaviour TOC (forbid: "Simplicity First", "Plan-Mode Default", etc.).
6. Re-running `python scripts/sync_command_mirrors.py --check` is a no-op (idempotency).

**`/ai-ide-audit` extension**

The audit, after this refactor, asserts for every supported IDE (Claude / Codex / Gemini / Copilot / **Antigravity**):
- the IDE-native path exists with the canonical content;
- no orphan duplicates;
- the `md_mirror` lint passes.

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

### 2.4.1 Worked example: `/ai-start` — single-script dashboard

**Operator-observed pain (4 IDEs, same `/ai-start` invocation)**:

| IDE / Model | Wall-clock | Bash dispatches | Re-probes | Hook errors |
|---|---|---|---|---|
| Copilot CLI / Sonnet 4.6 | slow | 7+ denied by RTK + ~10 retries | manifest 3×, lessons 4×, agents count 2× | RTK denies all `git`/`grep`/`wc` until rewritten as `rtk <cmd>` |
| Claude Code / Opus 4.7 | slow | several | LESSONS heading recount | `/bin/sh: node: command not found` (UserPromptSubmit hook); engram tool prefix doc says `mcp__engram__*` but actual is `mcp__plugin_engram_engram__*` |
| Copilot CLI / GPT 5.4 | very slow | 6+ (bootstrap + ruby+yaml + decision schema + gh issue + gh project + tempfile workaround) | manifest, LESSONS, CONSTITUTION re-read | gh project argv overflow → tempfile retry |
| Codex / GPT 5.5 | 1m 21s | similar | similar | — |

Each IDE/model dispatched a different ad-hoc probe set. `session_bootstrap.py` already exists but emits too little ⇒ agents do not trust it ⇒ they re-derive everything inline.

**Fix — single-script preprocessor**

1. **`scripts/start_collect.py`** (new, single Python entry; cross-platform, also `.ps1` sibling for parity per §2.5 R5). Internally calls git / yaml / sqlite / gh once each. Tolerates missing tools (gh offline → `board: null`). Always exits 0; surfaces errors as `warnings: [...]` inside the JSON.
2. **Output**: ONE JSON blob (~1.5-2 KB ceiling), e.g.:

   ```json
   {
     "schema_version": 1,
     "project": {"name": "ai-engineering", "branch": "feat/...", "head_commit": "e7d3c45b"},
     "active_spec": null,
     "plan_present": true,
     "manifest": {"skills": 47, "agents": 24},
     "lessons": {"count": 39, "last_updated": "2026-05-07"},
     "decisions": {"active": 0, "risks": 0},
     "events_7d": 518,
     "recent_commits": ["e7d3c45b chore(ci): ...", "..."],
     "board": {"provider": "github", "project": "arcasilesgroup/4", "total": 429, "by_status": {"Done": 405, "Backlog": 24}},
     "hooks": {"loaded": 21, "failures": []},
     "next_action_hint": "no active spec — run /ai-brainstorm",
     "warnings": []
   }
   ```

3. **SKILL.md procedure** (the only LLM-facing instruction):

   ```
   1. Run: python3 .ai-engineering/scripts/start_collect.py
   2. Render the JSON as the dashboard. Do not re-probe.
   ```

4. **Hook lane (M6 dependency)**: `start_collect.py` runs in a `trusted-script` lane that bypasses RTK rewriting and prompt-injection-guard re-evaluation of its internal git/grep/gh calls. The script is hash-pinned in the hook manifest (already supported by `_lib/hook-common.py`). Sub-agent Bash that invokes only this script triggers no IOC scan.
5. **`/ai-observe` activation**: invoked AFTER the dashboard renders, not in parallel with the bootstrap probes. Removes the source of "observation mode active" intermittent flag.

**Speed/token gain estimate (single `/ai-start` invocation)**

- Bash dispatches: 6-10 → **1**.
- Wall-clock: 30-90s → **≤5s** on warm repo.
- Tokens (LLM input): 12-18k of bash output → **≤2k** of JSON.
- Cross-IDE consistency: same dashboard body on Claude / Copilot / Codex / Gemini given identical repo state.

This is the **canary** for M3 — once `/ai-start` works this way, the same pattern is applied to every other skill in the registry.

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
5. `/ai-build` (or `/ai-autopilot` for ≥3-concern specs) → execute → PR opens. End.

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

### M2 — Markdown Canon Reset (Mirror Strategy)
- Author one canonical "how AI works" payload (≤300 lines target) distilled from Karpathy + Boris + the AI-behaviour content currently misplaced in CONSTITUTION.md. Contents per the TOC in §2.3.
- Mirror that payload as **four identical files**: `<repo>/AGENTS.md`, `<repo>/CLAUDE.md`, `<repo>/GEMINI.md`, `<repo>/.github/copilot-instructions.md`. **No imports, no symlinks, no cross-references** — each file is standalone.
- **Delete `<repo>/.gemini/GEMINI.md`** (dead path; Gemini CLI does not read it).
- **Do NOT create `<repo>/.codex/AGENTS.md`** (orphan; Codex reads root AGENTS.md).
- **Refactor `/ai-constitution`**: skill remains a generator, but the interview now produces a **project-specific** CONSTITUTION.md (mission, stakeholders, vocabulary, prohibitions, compliance gates, anti-goals, boundaries, escalation, language, lifecycle phase). Strip every AI-behaviour article currently in CONSTITUTION.md and migrate that content into the canonical mirror payload.
- Add `tools/skill_lint/md_mirror.py` (sha256-equivalence check on the four mirrors).
- **Reuse existing mirror plumbing**: refactor `scripts/sync_mirrors/core.py` surfaces 5.5 / 7 / 7.5 / copilot to read a single new template (`templates/project/CANONICAL.md`) and emit byte-equivalent payload across the four IDE paths. Delete the cross-ref line in `generate_copilot_instructions` at `core.py:1103`. Drop the in-repo `.gemini/GEMINI.md` write from Surface 7.5. **No new sync entry point** — `python scripts/sync_command_mirrors.py` stays canonical.
- Rewrite `README.md` (install + value-prop + links).
- Add `docs/getting-started.md` (5-frame onboarding).
- Update `CONTRIBUTING.md`.
- Extend `/ai-ide-audit` with **Antigravity** in its IDE matrix; per-IDE assertions are: native path exists with the canonical content, no orphan duplicates, mirror lint passes.
- ❑ `tools/skill_lint/md_mirror.py`: passes on the four mirrors (sha256 equivalence).
- ❑ `tools/skill_lint/principles.py`: every SKILL.md `## Workflow` cites at least one §10.x principle by anchor.
- ❑ Canonical mirror content includes §10.1–§10.8 as first-class subsections (KISS, YAGNI, SOLID, DRY, TDD, SDD, Clean Code, Hexagonal Architecture) with definition + concrete rules + anti-patterns + example each.
- ❑ `CONSTITUTION.md` contains zero AI-behaviour section headers (lint forbids "Simplicity First", "Plan-Mode Default", "KISS", etc.).
- ❑ Claude Code from repo root: `/memory` shows CLAUDE.md loaded with the full canonical content (no missing imports).
- ❑ Gemini CLI from repo root: GEMINI.md loaded with the full canonical content (no settings.json gymnastics required).
- ❑ Codex CLI from repo root: AGENTS.md loaded with the full canonical content.
- ❑ Antigravity v1.20.3+ loaded against the repo: GEMINI.md (highest) loaded with the full canonical content; AGENTS.md fallback also loaded with same content.
- ❑ Copilot loaded against the repo: `.github/copilot-instructions.md` loaded with the full canonical content.
- ❑ `python scripts/sync_command_mirrors.py --check` passes; running it twice produces no diff (idempotent).
- ❑ Every existing reference link still resolves.

### M3 — Deterministic Preprocessor Layer
- Apply Preprocessor Protocol (§2.4) to every skill missing one.
- For each: write `scripts/collect-context.sh` + `.ps1`, declare token budget in frontmatter (`effort:` + `budget_tokens:`).
- `/ai-brainstorm/handlers/prompt-enhance.md` deletes its inline rules; calls `/ai-prompt` instead (DRY).
- `tools/skill_lint/preprocessor.py` enforces: every SKILL.md declares budget; every script returns valid JSON within budget.
- **Priority skill #1: `/ai-start`** — see §2.4.1 below for the worked example. Operator-observed pain (4 IDEs, 4 different dispatch patterns) makes this the canary.
- ❑ Tested skills' average input tokens drop ≥30%.
- ❑ No skill exceeds 120 lines (Anthropic [SC] progressive-disclosure threshold; current ceiling already 120).
- ❑ Every SKILL.md has `## Quick start`, `## Workflow`, `## Examples`, `## Integration` sections (already enforced by spec-127 lint — keep).
- ❑ `/ai-start` SKILL.md: only one bash call (`python3 .ai-engineering/scripts/start_collect.py`). Zero re-probe of manifest / git / gh / state.db / LESSONS.md from the LLM. Wall-clock ≤5s on a warm repo.
- ❑ `/ai-start` produces an identical dashboard across Claude / Copilot / Codex / Gemini given the same repo state (string-equivalent dashboard body — only branding differs).

### M4 — Single Canonical Flow + Single Quality Loop
- The canonical chain stops mentioning `/ai-commit` (it's implicit inside `/ai-pr` as today). `/ai-commit` SKILL.md is preserved for standalone WIP-only invocation.
- `/ai-autopilot` and `/ai-build` stay **separate skills** with separate contracts. Single-Responsibility (§10.3) keeps them apart. Autopilot delegates to build agents in Phase 4 — that's the existing relationship; no fusion.
- **Drop per-task verify+review gates in BOTH skills.**
  - `/ai-build`: remove the post-task verify+review calls inside the task loop. Each task is responsible for self-validating via TDD (§10.5 RED-GREEN-REFACTOR — the build agent writes the failing test, makes it green, refactors, all within the task).
  - `/ai-autopilot` Phase 4: same — agents complete their sub-spec without per-task external gates.
- **Add ONE end-of-implementation quality loop in BOTH skills (single round, not max 3).**
  - `/ai-build` gains a new final phase before `/ai-pr`: dispatches verify + review on the full changeset once. Clean → /ai-pr. Blockers → STOP + escalate to user (no auto-retry).
  - `/ai-autopilot` Phase 5: trimmed from "max 3 rounds" to "single round". Verify + review + guard dispatched in parallel on full changeset once. Clean → Phase 6. Blockers → STOP + escalate.
- **Why single round**: fail-loud over fail-quiet. Auto-retry hides root causes; an honest STOP forces the operator to read the findings and fix intentionally. Multi-round loops are also where token budgets explode (3 rounds × ~70k tokens per gate ≈ 600k+ wasted on retries that often re-flag the same blocker).
- **Speed gain estimate** (10-task spec):
  - `/ai-build`: 20 gate runs → 2. ~90% reduction. ~13 min wall-clock saved. ~1.26M tokens saved.
  - `/ai-autopilot`: 29 gate runs → 3. ~90% reduction. ~19 min wall-clock saved. ~1.82M tokens saved.
- `/ai-cleanup`, `/ai-pr`, `/ai-brainstorm` gain shared `--consolidate-spec` action (delete finalised spec, append `_history.md`, leave slot ready).
- `/ai-cleanup` SKILL.md adds explicit `_history.md` rotation step (gap found in audit).
- AGENTS.md Step 0 reflects the single chain.
- ❑ Search the codebase: zero references to "/ai-commit then /ai-pr" or twin paths in canonical-chain documentation.
- ❑ AGENTS.md / CLAUDE.md / GEMINI.md / copilot-instructions.md canonical chain reads `brainstorm → plan → build → pr` (no `commit` step in the chain).
- ❑ Operator runs `/ai-pr` from a clean branch and gets commit + push + PR in one shot, no warnings.
- ❑ `/ai-build` SKILL.md: zero references to per-task verify+review; one final-quality-loop phase exists; single-round (not multi-round) explicitly stated.
- ❑ `/ai-autopilot/SKILL.md`: Phase 4 contains zero per-task verify+review references; Phase 5 is single-round; "round<3 → fix and re-assess" language removed.
- ❑ Telemetry confirms ~90% reduction in `verify_dispatch` and `review_dispatch` event counts per spec on the dogfood corpus.
- ❑ `/ai-commit` SKILL.md still exists as a user-invocable standalone (no deprecation warning). Documented as off-chain, for WIP-only commits.

### M5 — Models, Effort & Dispatch Economics
- Sub-brainstorm session (`/ai-brainstorm "model dispatch policy"`) produces sub-spec.
- Add `effort:` and `model_tier:` to every SKILL.md frontmatter.
- `/ai-plan` upgraded to **exhaustive patch-ready mode**: outputs concrete diffs per task (not just descriptions). Plan checklists self-tick when tasks complete (already partly implemented).
- `/ai-build` reads plan → dispatches cheap-tier model when patches are present, mid-tier when judgment needed.
- *(moved to M4: see `/ai-autopilot` ceremony trim. M5 keeps only the model/dispatch policy work.)*
- ❑ Token-per-PR median drops ≥40% on the dogfood corpus.

### M6 — Hooks & Robustness
- `prompt-injection-guard.py`: surface integrity failures to **stderr** (one-line reason + remediation), distinct exit code (3=integrity, 2=injection).
- `_lib/hook_context.py`: add `agent_kind` (main vs subagent) by reading transcript_path / parent session.
- Sub-agent policy lane: relaxed integrity mode, positive allow-list for read-only commands (`rg`, `grep`, `find`, `ls`, `cat` without redirect) evaluated **before** the IOC pattern loop.
- Replace `Bash(*--no-verify*)` glob with token-aware shlex matcher.
- **Add `trusted-script` lane**: scripts hash-pinned in `hooks-manifest.json` and invoked as a single argv (`python3 scripts/start_collect.py` etc.) bypass RTK rewriting and IOC re-evaluation of their internal subprocesses. Closes the `/ai-start` cross-IDE pain (operator-observed: 4 IDEs, 4 dispatch patterns; see §1 row 18b).
- **Fix Claude Code `UserPromptSubmit` hook node-missing path**: the hook script must detect missing Node and either fall back gracefully or fail with a clear stderr line — not "Failed with non-blocking status code: /bin/sh: node: command not found".
- **Fix Engram tool-prefix doc drift**: hook documentation references `mcp__engram__*` but the running surface is `mcp__plugin_engram_engram__*`. Pick one prefix; update the bootstrap docs and hook-emitted ToolSearch hints.
- ❑ Sub-agent runs `rg "anything"` from any path → succeeds.
- ❑ `python3 scripts/start_collect.py` runs in any IDE without RTK rewriting or IOC denial; total wall-clock ≤5s on a warm repo.
- ❑ Claude `/ai-start` does not emit a node-missing UserPromptSubmit hook error.
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
