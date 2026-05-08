# Skills + Agents Excellence Refactor — Pre-Chewed Roadmap

> **Status**: Draft brief — ready for `/ai-brainstorm` → `/ai-plan` → `/ai-autopilot`
> **Branch**: `feat/spec-126-hook-ndjson-lock-parity` (continuation)
> **Target PR**: **#506** (active)
> **Author lens**: Staff Principal Architect (IQ 200) + UX-for-engineers (`/ai-design`)
> **Architecture stamps**: KISS · YAGNI · DRY · SOLID · SDD · TDD · Clean Code · Hexagonal/Clean Architecture
> **Anchor research**: NotebookLM `b8a09700-2ce7-4d6c-84d7-82b89765ea53` + Anthropic skill-creator standard + Engram project memory
> **Mantra**: *less is more — endoskeleton, not exoskeleton — fast as if the framework wasn't there.*

---

## 0. North Star (the picture that must stay on the wall every commit)

A first-time engineer opens the repo, types `/ai-` and within **10 seconds** picks the right skill **without reading docs**, because:

1. **Names self-describe** (verb-noun, gerund, or imperative — no metaphors, no jargon).
2. **Descriptions trigger** on natural utterances ("Use when…" pattern, third person, ≤1024 chars, pushy).
3. **One canonical path per intent** — zero overlap clusters; if two skills touch the same surface, the boundary is *visible in the description itself*.
4. **Token-cheap by default** — every SKILL.md ≤ 500 lines (Anthropic hard rule), heavy detail in `references/` linked one level deep.
5. **Cohesive flow** — every skill that has a successor declares it in an `## Integration` section (`/ai-brainstorm` → `/ai-plan` → `/ai-dispatch` → `/ai-pr`).
6. **Hexagonal harness** — domain (skills' procedural intent) is decoupled from infrastructure (hooks, MCP, IDE adapters, telemetry). Renames or new IDEs cause **zero domain edits**.
7. **Speed-neutral** — pre-commit < 1s, pre-push < 5s, skill discovery cost ~100 tok/skill at L1, SKILL.md ≤ 5k tok at L2 (progressive disclosure).
8. **Self-improving** — `/ai-skill-evolve` + `/ai-prompt --skill <name>` + `/ai-instinct` → continuous compaction loop with eval gates.

If a change does not move the needle on **one of the eight axes above**, it is rejected from this PR.

---

## 1. Scope Boundary (what this refactor IS / IS NOT)

| In scope | Out of scope |
|---|---|
| `.claude/skills/` (50 skills) | `.ai-engineering/specs/` (untouched) |
| `.claude/agents/` (26 agents) | New product features |
| Cross-IDE mirrors via `sync_command_mirrors.py` | Hook bytes (`.ai-engineering/scripts/hooks/`) — only their *registration* of skills |
| Naming, descriptions, sections, length, integration links | Telemetry semantics |
| Architectural seams (ports/adapters split for IDE-mirrored layer) | Engram, NotebookLM, Context7 internals |
| Skill→agent dispatch contract | `/ai-engineering` CLI binary |

---

## 2. Diagnostic Snapshot (what we found)

Sourced from parallel-dispatch audit on 2026-05-07.

### 2.1 Skills inventory (50 total) — quality bar

| Bucket | Count | Examples |
|---|---|---|
| Grade A (CSO triggering, lean) | 28 | `ai-debug`, `ai-plan`, `ai-pr`, `ai-prompt`, `ai-design`, `ai-animation`, `ai-eval`, `ai-postmortem` |
| Grade B (mostly OK, missing edges) | 14 | `ai-verify`, `ai-test`, `ai-review`, `ai-write`, `ai-docs`, `ai-board-sync`, `ai-research`, `ai-start` |
| Grade C (vague triggers, weak boundary) | 6 | `ai-cleanup`, `ai-mcp-sentinel`, `ai-pipeline`, `ai-instinct` |
| Grade D (broken — implementation prose, no triggers) | 1 | `ai-entropy-gc` |
| **Skills with `## Examples`** | **0/50** | universal gap (Anthropic standard violation) |
| **Skills > 150 lines (progressive-disclosure risk)** | 5 | `ai-animation` 228, `ai-video-editing` 194, `ai-governance` 182, `ai-platform-audit` 181, `ai-skill-evolve` 179 |

### 2.2 Agents inventory (26 total) — quality bar

| Issue | Severity | Detail |
|---|---|---|
| `ai-autopilot` ↔ `ai-run-orchestrator` near-duplicate | **HIGH** | Both "6-phase orchestrators"; user cannot pick |
| `ai-guide` ↔ `ai-explore` shared identity ("read-only, reads everything") | MED | Boundary needs sharpening or merger |
| `reviewer-design` orphan | MED | Not in `ai-review` dispatch roster — dead code |
| `review-context-explorer` / `review-finding-validator` prefix mismatch | LOW | Sibling reviewers use `reviewer-`, these use `review-` |
| `reviewer-design` ↔ `reviewer-frontend` overlap | MED | Both UI-focused; merge or rename to design-system vs runtime-frontend |
| `ai-guard` ↔ `verifier-governance` mild overlap | LOW | One is advisory in-flight, other is dispatched — sharpen description |

### 2.3 Naming clusters that confuse first-time users

| Cluster | Skills/Agents | First-time-user hypothesis |
|---|---|---|
| **Execution trio** | `/ai-dispatch`, `/ai-run`, `/ai-autopilot` | "Which one runs my plan?" |
| **Quality trio** | `/ai-verify`, `/ai-review`, `/ai-release-gate` | "Which one tells me if it's mergeable?" |
| **Writing trio** | `/ai-write`, `/ai-docs`, `/ai-market` | "Where do I write a blog?" |
| **Visual quad** | `/ai-design`, `/ai-canvas`, `/ai-animation`, `/ai-slides` | "Which one for a poster?" |
| **Memory/learning trio** | `/ai-instinct`, `/ai-learn`, `/ai-note` | "Where does the lesson go?" |
| **Governance quad** | `/ai-governance`, `/ai-constitution`, `/ai-mcp-sentinel`, `/ai-platform-audit` | "Which one checks framework health?" |
| **Code trio** | `/ai-code`, `/ai-build`, `/ai-dispatch` (agent) | "Where does code actually get written?" |

### 2.4 Bottom-10 confusion-prone skills (P0 fix)

`ai-entropy-gc`, `ai-instinct`, `ai-mcp-sentinel`, `ai-canvas`, `ai-eval`, `ai-run`, `ai-platform-audit`, `ai-governance`, `ai-skill-evolve`, `ai-constitution`.

---

## 3. Conformance Bar (the grading rubric)

Every skill must, at PR-merge time, satisfy **all 10**:

1. Frontmatter has only `name` + `description`; both pass Anthropic hard validation (`^[a-z0-9-]{1,64}$`, no `claude`/`anthropic` substrings, ≤1024 chars, no XML).
2. Description is **third-person**, contains explicit `Use when …` clause with **≥3 trigger phrases** (lean *pushy*).
3. Description states **what NOT to use it for** when adjacent skills exist (negative scoping).
4. SKILL.md body ≤ **500 lines**; ≤ **5,000 tokens**.
5. Required sections present: `## Quick start`, `## Workflow`, `## Examples`, `## Integration`.
6. **`## Examples`** ≥ 2 invocations with expected output style.
7. References (>100 lines) live in `references/` one level deep with TOC at top.
8. ≥ 3 evals defined under `evals/<skill>.jsonl` (8 should-trigger + 8 near-miss).
9. Description optimized via `python -m scripts.run_loop --skill-path …` and result committed.
10. No anti-patterns: no metaphors in name, no first/second person, no time-stamped prose, no kitchen-sink, no nested refs, no voodoo constants in companion scripts.

Agents have a parallel rubric (frontmatter description CSO, tools whitelist explicit, model declared, dispatch source ≥1 reference, no orphan).

---

## 4. The Final Skill Surface (after refactor)

Target count: **46 skills** (down from 50) + **23 agents** (down from 26). Updated after the execution-stack deep-dive (see §12).

Reductions:
- **`/ai-run` skill ≡ `/ai-autopilot` skill** — true duplicate (identical 5-step pipeline; only intake source differs). Merge into `/ai-autopilot` with intake adapters: `--task`, `--backlog`, `--spec`. (−1 skill)
- **`/ai-dispatch` skill** is the legitimately distinct *human-in-the-loop* execution gateway. Rename → **`/ai-build`** (skill) for naming clarity (verb=action, paired with `ai-build` agent). The single canonical path from approved plan to merged code.
- Merge `ai-board-discover` + `ai-board-sync` → `/ai-board <discover|sync>` (−1 skill).
- Merge `ai-release-gate` into `/ai-verify --release` mode (−1 skill).
- Merge `ai-run-orchestrator` agent into `ai-autopilot` agent (−1 agent).
- Merge `reviewer-design` (orphan) into `reviewer-frontend` (−1 agent).
- Delete `ai-build` skill if it exists separately from `/ai-dispatch` rename — collapse to single canonical entry point. (−1 if duplicate exists.)

Renames (chosen for *self-description first, history second*):

| From | To | Reason |
|---|---|---|
| `/ai-dispatch` | **`/ai-build`** | Verb-noun, pairs with `ai-build` agent, matches Karpathy noun-as-body-of-knowledge naming. Single canonical "implement the approved plan" entry point. |
| `/ai-run` | **deleted** (merged into `/ai-autopilot --backlog`) | True duplicate — same pipeline, different intake. |
| `/ai-canvas` | **`/ai-poster`** | "Canvas" is a metaphor; "poster" is the artifact. (alt: `/ai-visual` if poster is too narrow — decide in spec phase) |
| `/ai-market` | **`/ai-gtm`** | Differentiates from `/ai-write` and `/ai-docs` cleanly |
| `/ai-mcp-sentinel` | **`/ai-mcp-audit`** | "Sentinel" implies daemon; this is on-demand |
| `/ai-entropy-gc` | **`/ai-simplify-sweep`** | Restates intent in user vocabulary |
| `/ai-instinct` | **`/ai-observe`** | Avoids metaphor; describes the action |
| `/ai-skill-evolve` | **`/ai-skill-tune`** | Closer to "improve"; matches `/ai-prompt` semantics |
| `/ai-platform-audit` | **`/ai-ide-audit`** | Disambiguates from infra "platform" |
| `review-context-explorer` (agent) | **`reviewer-context`** | Aligns prefix with siblings |
| `review-finding-validator` (agent) | **`reviewer-validator`** | Aligns prefix with siblings |
| `ai-run-orchestrator` (agent) | **deleted** (merged into `ai-autopilot`) | Eliminate near-duplicate |
| `reviewer-design` (agent) | **deleted** (merged into `reviewer-frontend`) | Orphan |

**Final canonical execution flow** (see §12 + §13 for detail):

```
/ai-brainstorm  →  /ai-plan  →  /ai-build  →  /ai-verify  →  /ai-review  →  /ai-commit  →  /ai-pr
   (spec)         (plan DAG)   (impl gateway)  (det. gates)    (judgment)     (det. fast)   (det. fast)

                                 ↑
                  /ai-autopilot --task|--backlog|--spec
                  (autonomous wrapper around the same flow)
```

Backward-compatibility: keep alias dispatch (`/ai-dispatch`, `/ai-run` → resolve to new targets) for one minor version. Removal scheduled in a follow-up PR.

---

## 5. Architecture Pattern: Hexagonal Harness for Skills + Agents

Today the framework already has hooks + MCP + IDE adapters; they are *almost* hexagonal but skills mix domain (procedural intent) with infrastructure (which IDE, which mirror, which hook). We finalize the seams.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  INTERFACE (drivers — left side)                                         │
│  Claude Code slash commands │ Codex/Gemini/Copilot mirrors │ MCP tools    │
└─────────┬────────────────────────────────────────┬───────────────────────┘
          │                                        │
          ▼                                        ▼
┌──────────────────────────────────┐   ┌─────────────────────────────────┐
│  APPLICATION (use cases)         │   │  PORTS                          │
│  Skill orchestration             │←──┤  SkillPort, AgentPort,          │
│  Agent dispatch contract          │   │  HookPort, BoardPort, MemoryPort│
│  Conformance rubric (linter)     │   │  TelemetryPort                  │
└─────────┬────────────────────────┘   └────────────────┬────────────────┘
          │                                              │
          ▼                                              ▼
┌──────────────────────────────────┐   ┌─────────────────────────────────┐
│  DOMAIN (zero deps)              │   │  INFRASTRUCTURE (adapters —     │
│  Skill = {name, description,     │   │  right side)                    │
│           examples, evals,       │   │  • Hook bytes manifest          │
│           integration[]}         │   │  • Engram MCP                   │
│  Agent = {name, role, tools,     │   │  • NotebookLM MCP               │
│           model}                 │   │  • Context7 MCP                 │
│  Conformance Rules (Anthropic    │   │  • GitHub Projects / ADO        │
│   skill-creator hard rules)      │   │  • Sync mirrors script          │
└──────────────────────────────────┘   └─────────────────────────────────┘
```

- **Domain layer** (new): `tools/skill_domain/` — pure-Python dataclasses + validators. *Zero* I/O.
- **Application layer**: orchestrators (linter, evaluator, optimizer) call only ports.
- **Infrastructure adapters**: existing hook scripts, mirror sync, MCP clients. Each implements one port.
- Custom `taste-invariants` linter blocks domain → infra imports (per NotebookLM "Taste Invariants as Code").

This means: when we add a new IDE (say, Cursor), we add an adapter implementing `SkillPort.publish(skill)` — **no skill content changes**.

---

## 6. Roadmap — 6 Milestones, KISS-ordered

> Each milestone is independently shippable. **TDD is mandatory**: every milestone opens with failing tests pinned to the conformance rubric.

### M1 · Conformance Rubric as Code  *(foundation)*

**Why**: nothing improves without a measurable bar. Today's audit was manual.

**What**:
- New `tools/skill_lint/` (in domain layer) — pure validator over `SKILL.md` frontmatter + body sections + length + ref nesting.
- New `pytest` suite `tests/conformance/test_skills_rubric.py` red-green-driven from §3.
- Bake `skill_lint --check` into pre-commit; fail-loud, ≤200ms budget (parallel walk).
- Generate `docs/conformance-report.md` artifact at CI for visibility.

**Done when**: full repo runs `skill_lint --check` and reports current score (baseline). No skill is fixed yet — only graded.

**SDD/TDD note**: spec written in `.ai-engineering/specs/<n>/spec.md`, tests written first, validator implementation last.

### M2 · Description CSO Pass + Examples Block  *(highest leverage, lowest risk)*

**Why**: descriptions are the single discovery signal; `## Examples` is the universal gap.

**What**:
- Run `/ai-prompt --skill <name>` over all 50 skills (script the loop).
- For Grade C/D and bottom-10: human-edit + run `scripts/run_loop` (skill-creator optimizer) with 16-eval set per skill.
- Add `## Examples` (≥2 invocations) and `## Integration` (link to predecessor + successor skills) to all 50.
- Re-grade with rubric from M1; target ≥95% Grade A.

**Done when**: rubric reports zero D, ≤2 C, all skills have Examples + Integration sections. Baseline → target diff in `docs/conformance-report.md`.

### M3 · Progressive-Disclosure Slim-Down  *(token diet)*

**Why**: 5 skills exceed the lean threshold; SKILL.md is system-prompt token cost on every triggering.

**What** (per skill in top-5 length list):
1. Identify "always-needed" lines (Quick start, Workflow summary, top-level decision matrix).
2. Move domain-specific reference, code blocks, full schemas to `references/<topic>.md` one level deep with TOC.
3. Cap each SKILL.md at **≤120 lines** as the project's tightened internal limit (Anthropic ceiling 500 — we aim half).

**Done when**: every SKILL.md ≤120 lines, every reference ≤300 lines with TOC, no nested ref→ref.

### M4 · Renames + Mergers + Cohesion Links  *(deduplicate)*

**Why**: confusion clusters cost users their first 10 seconds and credibility forever.

**What**:
- Apply renames from §4 via the IDE-adapter layer (single entrypoint update); legacy-alias dispatcher symlinks for one minor version.
- Merge `ai-board-discover` + `ai-board-sync` → `/ai-board`.
- Merge `ai-release-gate` into `/ai-verify --release` (verify gains a mode flag; release-gate becomes alias).
- Delete `ai-run-orchestrator` agent (functionality absorbed by `ai-autopilot` with a `--source <github|ado|local>` flag).
- Delete `reviewer-design` (frontend reviewer absorbs design-system rules from notebookLM section on UI legibility).
- Add Integration sections in 10 cohesion-gap skills (M2 covers this on the description side; M4 covers the body).
- Update `sync_command_mirrors.py` once; verify Codex/Gemini/Copilot mirrors still build.

**Done when**: skill count = 48, agent count = 24, dispatcher passes alias tests, mirrors green.

### M5 · Hexagonal Seams Made Explicit  *(architecture stamp)*

**Why**: today's `tools/` and `scripts/` mix domain + infra; future IDE additions cost too much.

**What**:
- Carve `tools/skill_domain/` (Skill, Agent, Conformance dataclasses + validators).
- Carve `tools/skill_app/` (use cases: lint, optimize, evolve, audit).
- Move existing hook/mirror/Engram/NotebookLM clients under `tools/skill_infra/` implementing explicit ports defined in `skill_app`.
- Add `tools/skill_infra/lints/test_no_domain_to_infra.py` — blocks cross-layer imports (Taste Invariant).
- Refactor `/ai-create`, `/ai-skill-tune` (renamed evolve), `/ai-prompt`, `/ai-platform-audit` to consume the application layer only.

**Done when**: `pytest tests/architecture/test_layer_isolation.py` green; importing infra from domain raises ImportError in test.

### M6 · Eval Harness + Self-Improvement Loop  *(close the loop)*

**Why**: NotebookLM-cited PEV Loop (Plan-Execute-Verify) demands measurable gates; without evals the framework drifts.

**What**:
- Each skill ships `evals/<skill>.jsonl` with ≥16 cases (8 should-trigger / 8 near-miss).
- `/ai-eval` gains a `--skill-set` mode running optimizer pass@k against the eval corpus.
- CI runs `skill_lint --check` (M1) + `eval --regression` (this) on every PR touching `.claude/skills/**`.
- `/ai-skill-tune` (renamed) consumes prior evals + Engram observations + `LESSONS.md` to propose description deltas; PR-only output, never auto-merge.

**Done when**: green CI, baseline pass@1 captured, `LESSONS.md` references at least 1 self-improvement cycle output.

---

## 7. Definition of Done — PR #506

The PR ships **all six milestones** in this branch (single PR, single review). Hard gates:

- [ ] `skill_lint --check` exit 0 across all 48 skills.
- [ ] All skills have ≥2 `## Examples` and an `## Integration` section.
- [ ] All SKILL.md ≤ 120 lines.
- [ ] No nested references (>1 level) anywhere under `.claude/skills/**/references/`.
- [ ] Renames live; legacy aliases pass dispatcher integration tests.
- [ ] Hexagonal layer-isolation test green.
- [ ] Eval pass@1 baseline captured for each skill; CI regression gate active.
- [ ] Mirrors regenerated for `.github/`, `.codex/`, `.gemini/`; their tests pass.
- [ ] `docs/conformance-report.md` shipped with before/after table.
- [ ] CHANGELOG entry; AGENTS.md + CLAUDE.md updated for new skill count + governance hooks.
- [ ] Pre-commit ≤ 1s, pre-push ≤ 5s budgets respected (benchmark in CI).

---

## 8. Quality Stamps — how each principle shows up in code

| Principle | Manifestation |
|---|---|
| **KISS** | Description = one paragraph, ≤1024 chars, third person, "Use when…" — that's it. |
| **YAGNI** | No "future-proof" frontmatter fields, no speculative ports. Add when a real adapter needs one. |
| **DRY** | Conformance rules live once in `skill_domain/rubric.py`; consumed by linter, optimizer, CI, `/ai-create`, `/ai-skill-tune`. |
| **SOLID** | One port per concern (Skill/Agent/Hook/Memory/Telemetry); single-responsibility per use case; open for new IDEs by adapter, not by edit. |
| **SDD** | Every milestone is a spec under `.ai-engineering/specs/<n>/`. No code without spec. |
| **TDD** | Conformance tests written first (M1); each subsequent milestone opens RED. |
| **Clean Code** | No metaphors in names, no time-sensitive prose, no kitchen-sink files. |
| **Hexagonal** | Domain pure-Python; infra (hooks, mirrors, MCP) is adapters; layer-isolation linted. |

---

## 9. Risks + Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Mass renames break user muscle memory | High | Legacy aliases for one minor version + announce in CHANGELOG. |
| 50 SKILL.md edits cause merge churn | High | Sequence M2 → M3 → M4 in the same PR but separate commits per skill cluster; conformance gate catches regressions. |
| Description optimizer over-fits | Medium | skill-creator's 60/40 train/test split + 3× stability loop is mandatory; bottom-10 also human-reviewed. |
| Hexagonal layering refactor leaks scope | Medium | M5 only moves files/imports; behavior-preserving. Behavior changes belong to M6 alone. |
| Cross-IDE mirrors drift | Medium | `sync_command_mirrors.py` runs in CI; manifest hash gate fails loud on stale mirrors. |
| `ai-release-gate` removal angers existing users | Low | Mode flag (`/ai-verify --release`) preserves output schema; alias for one version. |

---

## 10. Out-of-band Inputs (already gathered, attach to spec)

- **NotebookLM source IDs** (use as citation anchors, do not re-research):
  `7146c346`, `9d9b9ce9`, `86a9e7b3`, `c2740349`, `9a8958c4`, `80d9f910`, `c6e05de9`, `9c0fc69d`, `f562a7cc`, `a9a9a5a3`.
- **Anthropic skill-creator standard** distilled in §3 (conformance bar). Sources:
  `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`,
  `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`,
  local `~/.agents/skills/skill-creator/SKILL.md`.
- **Audit raw output** offloaded at `.ai-engineering/runtime/tool-outputs/2026-05-07T212105Z-995b26070b6b42e3863f303d1568335a.txt` and `2026-05-07T212139Z-e06c7adc2da542be8147731e218d1d1e.txt` — keep for spec phase.
- **Engram personal memory** (already in `~/.claude/projects/.../memory/MEMORY.md`):
  `feedback_radical_simplification`, `feedback_simplify_before_build`, `feedback_analyze_before_build`, `project_architecture_v3`, `project_full_ide_mirrors` — all align with this brief.

---

## 11. Hand-off Sequence

1. `/ai-brainstorm` — read this brief; emit `spec.md` per milestone (eight specs after Phase B additions: M0…M7) under `.ai-engineering/specs/<n>-skills-excellence-Mx/`.
2. `/ai-plan` — phased tasks per spec, agent assignments, gate criteria.
3. `/ai-build` (renamed from `/ai-dispatch`) — execute each spec; `/ai-autopilot` wraps multi-spec parallel waves.
4. `/ai-verify` + `/ai-review` between every wave; convergence gate.
5. `/ai-commit` + `/ai-pr` — single PR retarget #506 with the full body composed from §7 checklist.

**Do not deviate** from §0 (North Star) at any phase. If a step proposes work that doesn't move one of the eight axes, drop it.

---

# PHASE B — Deep Refactor Extensions (parallel-dispatch findings, 2026-05-08)

> Phase A above (sections 0–11) covers the conformance + naming + hexagonal foundation. Phase B addresses the **execution stack consolidation**, **hot-path determinism**, **AGENTS.md voice**, and the **canonical implementation gateway skill**. All findings come from a 9-agent parallel research dispatch (Boris CLAUDE.md, Karpathy CLAUDE.md, NotebookLM `b8a09700…` harness queries, codebase deep-dives).

---

## 12. Execution Stack Consolidation — Decisions Locked

**Finding**: parallel-dispatch evidence proves `/ai-autopilot` skill ≡ `/ai-run` skill (same 5-step pipeline, only intake differs) and `ai-autopilot` agent ≡ `ai-run-orchestrator` agent (same Opus orchestrator, same output contract).

**Locked decisions**:

| Surface | Decision | Rationale |
|---|---|---|
| `/ai-autopilot` skill | **Keep**. Add `--task`/`--backlog`/`--spec` intake adapters. Single autonomous wrapper. | KISS: one skill, three intake shapes. |
| `/ai-run` skill | **Delete**. Alias → `/ai-autopilot --backlog`. | True duplicate. NotebookLM `9a8958c4`: "One agent with full context outperformed 20 with partial context." |
| `/ai-dispatch` skill | **Rename → `/ai-build`** (skill). HITL plan-execute gateway. | Pairs with `ai-build` agent; verb-noun (Karpathy); single canonical entry from approved plan to code. |
| `ai-autopilot` agent | **Keep**. Sole orchestrator. Add `--source <github\|ado\|local>` flag. | Coordinator role per NotebookLM PEV. |
| `ai-run-orchestrator` agent | **Delete**. Merged. | True duplicate. |
| `ai-build` agent | **Keep monolith**. Add deterministic router (no LLM cost). | NotebookLM `9a8958c4`: Harness 20-subagent split = 40s nightmare; consolidation = 2× faster, 90% fewer tokens. |
| `ai-dispatch` agent (existing) | **Delete** if it exists outside the skill — function absorbed by `ai-build` skill + agent pair. | Eliminate naming collision. |

**Why we do NOT split `ai-build` into `code-writer` / `doc-writer` / `test-writer`**:

The user's intuition ("ai-build does too much, maybe worse implementer") is valid in theory, but NotebookLM cites Harness's empirical failure: domain-based agent splits caused **40s response times, 10× token bloat, inconsistent accuracy**. The fix is not splitting by artifact type — it is:

1. **Specialize by SDLC role** (planner / implementor / verifier), not by artifact type. `ai-plan` (no write) → `ai-build` (write) → `ai-verify` (read-only) is already the right axis.
2. **Extract domain routing as a deterministic Python pre-step** inside the `ai-build` agent's invocation. No LLM cost — a pattern table maps task path → adapter (TypeScript task uses TS conventions, SQL task uses migration-with-rollback template, etc.).
3. **Use isolated git worktrees** for parallel build tasks (`EnterWorktree` already shipped). Each implementor task runs in filesystem isolation.

```
ai-build agent invocation
        │
        ▼
┌───────────────────────────────┐
│ deterministic_router.py       │  ← <50ms, no LLM
│  read task path + spec stack  │
│  match adapter from rule table│
│  load language conventions    │
│  load TDD harness for stack   │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ ai-build agent (LLM)          │
│  receives: task + adapter +   │
│   conventions + TDD harness   │
│  writes code in isolated      │
│   worktree                    │
│  Ralph loop convergence       │
└───────────────────────────────┘
```

---

## 13. The Implementation Gateway Skill — `/ai-build`

> The user's request: *"a skill that, after spec and plan, hands off to implementation using the framework + language chosen in the manifest, with best practices, examples, governance, quality, security — but at native speed."*

This is the **canonical bridge**. After approval, ONE slash command takes the project from plan to merged PR.

**Surface**: `/ai-build` (replaces `/ai-dispatch`).

**SKILL.md outline (≤120 lines)**:

```markdown
---
name: ai-build
description: Use when an approved plan.md exists and execution should begin. Trigger for 'go', 'start building', 'execute the plan', 'implement it', 'let's do this', 'resume', 'continue'. Routes each task to the ai-build agent in its language/framework adapter (read from manifest.yml), applies KISS · YAGNI · DRY · SOLID · TDD · Clean Code · Hexagonal architecture as the prelude before code. Not for ambiguous specs (use /ai-brainstorm) or backlog autonomy (use /ai-autopilot --backlog).
---

# /ai-build — Plan → Implementation Gateway

## Quick start
1. Reads `.ai-engineering/specs/spec.md` + `plan.md`.
2. Resolves stack from `manifest.yml` (`stack.language`, `stack.framework`).
3. For each task in plan.md:
   a. `deterministic_router.py` picks adapter (TS/Python/Go/Rust/Swift…)
   b. `ai-build` agent invoked in isolated worktree with adapter context
   c. Ralph loop convergence (lint + test-collect)
   d. `/ai-verify` after each task; failure → reinject context, retry up to AIENG_RALPH_MAX_RETRIES
4. After last task: `/ai-review` → `/ai-commit` → `/ai-pr` (auto chain).

## Workflow (deterministic where possible)

| Step | Type | Tool |
|---|---|---|
| Stack detection | DET | `manifest_reader.py:resolve_stack()` |
| Task router | DET | `deterministic_router.py` |
| Adapter loading | DET | `adapters/<lang>/conventions.md` |
| Worktree setup | DET | `EnterWorktree` |
| Code write | LLM | `ai-build` agent |
| TDD enforcement | DET | language-native runner (`pytest`, `vitest`, `cargo test`, …) |
| Convergence | DET | Ralph loop (lint + test-collect, ≤5s budget) |
| Cross-task review | LLM | `/ai-review` after each |
| Commit | DET+LLM | `/ai-commit` (det. compose, LLM only for fuzzy summary) |
| PR | DET+LLM | `/ai-pr` (det. body from spec, LLM only for narrative bullets) |

## Adapters (`/.ai-engineering/adapters/<stack>/`)

Each adapter ships:
- `conventions.md` — naming, file layout, imports, error handling for that stack
- `tdd_harness.md` — how to write failing test first
- `security_floor.md` — must-pass rules (input validation, secrets, OWASP)
- `examples/` — 2-3 minimal patterns for that stack

Stacks: `typescript`, `python`, `go`, `rust`, `swift`, `csharp`, `kotlin`. Add by adapter, not by skill edit.

## Architecture clauses (always run BEFORE code, regardless of stack)

| Clause | What it blocks |
|---|---|
| KISS | "Smart" abstraction, generics for one call site |
| YAGNI | Speculative config, future-proofing flags |
| DRY | Copy-paste detection (jscpd / similar) |
| SOLID | God-class > 200 lines, dependency inversion violations |
| TDD | No code commits without preceding red test |
| Clean Code | Method > 20 lines, magic constants, ambiguous names |
| Hexagonal | Domain → Infra import (linted) |

## Examples
…
## Integration
- Predecessor: `/ai-plan`
- Successor: `/ai-verify` → `/ai-review` → `/ai-commit` → `/ai-pr`
- Wrapper: `/ai-autopilot --spec <id>` runs `/ai-build` autonomously
```

**Net effect**: `/ai-build` IS the framework's "endoskeleton-for-implementation". Without it, every plan's execution would be ad-hoc; with it, every task gets language-correct conventions + TDD + governance + Ralph convergence — *automatically, fast*.

---

## 14. Hot-Path Determinism — Speed Without Sacrifice

**Goal restated** (NotebookLM `9c0fc69d`): *"probabilistic inside, deterministic at the edges"*. Reserve LLM for genuine judgment; everything else = scripts.

### 14.1 Three reusable libs (build first — 60% of gains depend on them)

| Lib | Path | Used by |
|---|---|---|
| `manifest_reader.py` | `.ai-engineering/scripts/skills/_lib/manifest_reader.py` | ai-start, ai-pr, ai-commit, ai-standup, ai-cleanup, ai-build |
| `git_activity.py` | `.ai-engineering/scripts/skills/_lib/git_activity.py` | ai-standup, ai-start, ai-docs, ai-postmortem, ai-learn |
| `markdown_render.py` | `.ai-engineering/scripts/skills/_lib/markdown_render.py` | ai-start, ai-pr, ai-standup, ai-cleanup, ai-verify |

### 14.2 Top-15 L→D conversions (highest ROI on daily-driver path)

| Rank | Skill | New script | LLM remains for | ms saved |
|---|---|---|---|---|
| 1 | `/ai-start` | `session_bootstrap.py` (<300ms, JSON out) | 3-line welcome banner | ~4000 |
| 2 | `/ai-pr` | `pr-body-compose.py` | Summary bullets + Test Plan | ~3500 |
| 3 | `/ai-standup` | `standup-render.py` | Optional `--narrative` | ~3500 |
| 4 | `/ai-cleanup` | `cleanup-run.py` | Ambiguous "gone with dev" prompts | ~3500 |
| 5 | `/ai-docs` | `docs-changelog.py`, `docs-readme-sync.py` | solution-intent narrative | ~3500 |
| 6 | `/ai-autopilot` | `autopilot-fsm.py` (YAML transitions) | actual code-change steps | ~3000 |
| 7 | `/ai-resolve-conflicts` | `resolve-classify.py`, `resolve-lock.py` | true code conflicts only | ~3000 |
| 8 | `/ai-ide-audit` | extend `ai-eng doctor` JSON | remediation order synthesis | ~3000 |
| 9 | `/ai-verify` | extend gate orchestrator (Markdown out) | WARN remediation suggestions | ~2500 |
| 10 | `/ai-commit` | `commit-compose.py` | `<desc>` only when no `--force "msg"` | ~2500 |
| 11 | `/ai-board <discover\|sync>` | `board-discover.py`, `board-sync.py` | none | ~2500 |
| 12 | `/ai-governance` | `governance-eval.py` (OPA wrapper) | < 90 score narrative | ~2500 |
| 13 | `/ai-eval` | `eval-run.py`, `eval-scoreboard.py` | failure cluster analysis | ~2500 |
| 14 | `/ai-security` | `security-compose.py` | medium-severity triage | ~2500 |
| 15 | `/ai-slides` | `slides-validate.py` (headless 8 viewports) | content build only | ~2500 |

**Cumulative gain on the daily-driver chain (`/ai-start → /ai-commit → /ai-pr → /ai-cleanup`): ~50–70% wall-clock reduction**. The framework reaches "as if not installed" speed on the green-path 80% of invocations.

### 14.3 Hot-path budgets (locked)

| Surface | Budget | Hard ceiling |
|---|---|---|
| pre-commit hook | 1.0s | 1.5s |
| pre-push hook | 5.0s | 7.0s |
| `/ai-start` | 0.5s (banner) | 2.0s (`--full`) |
| `/ai-commit` (no manual edit) | 1.5s | 3.0s |
| `/ai-pr` (deterministic compose) | 8.0s | 15.0s |
| `/ai-verify` PASS path | 1.0s | 3.0s |
| `/ai-cleanup` | 1.5s | 3.0s |

CI enforces these via `tests/perf/test_hot_path_budgets.py`. Regression > 25% blocks the PR.

---

## 15. Spec Lifecycle Auto-Maintenance

**User pain**: spec workspace clutters; `_history.md` falls out of sync; `/ai-brainstorm` slowed by manual cleanup.

**Solution**: deterministic state machine + sidecar JSON truth source + idempotent transitions. Wired into `/ai-brainstorm` (start), `/ai-pr` (ship), `/ai-cleanup` (sweep).

### 15.1 State machine

```
              ┌──────────┐  /ai-plan        ┌───────────┐  /ai-build       ┌─────────────┐
   (none) ──▶ │  DRAFT   │ ───────────────▶ │ APPROVED  │ ──────────────▶ │ IN_PROGRESS │
              └──────────┘                  └─────┬─────┘                 └──────┬──────┘
                  │                              │ abandon                       │ /ai-pr merged
                  │ /ai-cleanup --specs          │                               ▼
                  │ (DRAFT > 14d, no plan.md)    ▼                          ┌──────────┐
                  ▼                          ┌───────────┐                  │ SHIPPED  │
              ┌──────────┐                   │ ABANDONED │                  └────┬─────┘
              │ABANDONED │ ◀──────────────── └─────┬─────┘                       │
              └────┬─────┘                         │                             │ next /ai-brainstorm
                   │                               │                             │ OR /ai-cleanup --specs
                   ▼                               ▼                             ▼
                                             ┌──────────────────────────────────────┐
                                             │             ARCHIVED                  │
                                             └──────────────────────────────────────┘
```

### 15.2 Script — `.ai-engineering/scripts/spec_lifecycle.py`

- **Stdlib only**, <500ms budget, idempotent, atomic writes.
- Source of truth: `.ai-engineering/state/spec-lifecycle.json` (NOT markdown — markdown is projection).
- Reuses `_lib/locking.artifact_lock` (spec-126 parity-tested) + `_lib/observability.append_framework_event`.
- API: `start_new(slug, title)`, `mark_shipped(spec_id, pr_number, branch)`, `archive(spec_id)`, `sweep()`, `status()`.
- All transitions emit `framework_event` NDJSON entries.

### 15.3 Wire-in points

| Skill | Hook point | Function | Failure posture |
|---|---|---|---|
| `/ai-brainstorm` | step 1 (before evidence sweep) | `start_new(slug, title)` (auto-archives prev SHIPPED) | fail-open |
| `/ai-pr` | post-merge confirmed | `mark_shipped(spec_id, pr, branch)` | fail-open; sweep heals |
| `/ai-cleanup` | new phase, flag `--specs` | `sweep()` | fail-open; report drift |

### 15.4 `_history.md` format (idempotent table)

```
| ID  | Title           | Status   | Created    | Shipped    | PR      | Branch         |
|-----|-----------------|----------|------------|------------|---------|----------------|
| 126 | Hook lock parity| shipped  | 2026-05-07 | 2026-05-08 | PR #432 | feat/spec-126… |
```

Idempotent key: `(ID, PR)`. Insertion: directly after header separator, newest first. Free-form retro sections below the `---` separator preserved verbatim.

---

## 16. `/ai-start` — Deterministic Bootstrap

**Today**: 7 of 9 steps are pure data shuffling routed through LLM (~5s wall-clock).
**Target**: <500ms banner + JSON dashboard, LLM only renders 3-line welcome.

### 16.1 Step classification (current ai-start)

| Step | Type today | Action |
|---|---|---|
| 1a (read CLAUDE.md/AGENTS.md) | DET-NOW | keep |
| 1b (count lessons/decisions/risks) | LLM-NOW → DET | regex count |
| 2 (start `/ai-instinct` observation) | LLM-NOW → DEAD | observation runs via hook, not skill — remove |
| 3a (parse `spec.md` YAML) | LLM-NOW → DET | 2 lines `yaml.safe_load` |
| 3b (count `[x]` in `plan.md`) | LLM-NOW → DET | regex |
| 3c (`git log` recent merges) | LLM-NOW → DET | `git log --oneline --since=7d` |
| 3d (board status `gh`/`az`) | LLM-NOW → DET | provider CLI + JSON parse |
| 3e (count `proposals.md`) | LLM-NOW → DET | line count |
| 4 (render dashboard) | LLM-NOW → DET | f-string template |

### 16.2 Proposed `session_bootstrap.py`

```python
# .ai-engineering/scripts/session_bootstrap.py
# stdlib only, <300ms, parallel git subprocesses, fail-open per field
# emits JSON to stdout

{
  "schema_version": 1,
  "elapsed_ms": 287,
  "branch": "feat/spec-126-...",
  "last_commit": {"sha": "7e6a004f", "subject": "fix(integration): provider alias"},
  "active_spec": {"id": "spec-126", "state": "IN_PROGRESS", "tasks_total": 18, "tasks_done": 14},
  "board": {"items_in_progress": 2, "items_in_review": 1},
  "recent_merges": [{"pr": 504, "title": "..."}, ...],
  "hooks_health": "ok",
  "instinct_observations_queued": 3,
  "next_action_hint": "resume /ai-build (4 tasks remaining)"
}
```

### 16.3 LLM responsibility shrinks to:

```
Hi — branch feat/spec-126-…, spec-126 14/18 tasks done.
Next: /ai-build (4 tasks left). 2 board items in flight, 3 instinct obs to consolidate.
```

3 lines. ~50 tokens. Done. Auto-invocation from `/ai-brainstorm` becomes invisible.

---

## 17. `/ai-commit` + `/ai-pr` — Speed-Neutral Governance

### 17.1 `/ai-commit` (today: 8 steps, 2 LLM calls; target: 1.5s)

Redesigned flow:

| Step | Today | New | LLM? |
|---|---|---|---|
| 0. branch | LLM proposes | `branch_slug.py` from spec.md frontmatter | NO |
| 1. stage | manual + LLM hint | manual; script suggests via `git status` map | NO |
| 2. format/lint | runs | runs (cached if pre-commit just ran) | NO |
| 3. gitleaks | runs | runs (already <200ms) | NO |
| 4. doc gate | LLM checks | `doc_gate.py` (regex on changed paths vs CHANGELOG/README) | NO unless gate fails |
| 5. message compose | LLM | `commit_compose.py` proposes; LLM ONLY for `<desc>` clause when `--force "msg"` absent | minimal |
| 6. commit | runs | runs | NO |
| 7. push (optional) | runs | runs | NO |

### 17.2 `/ai-pr` (today: 16 steps, 3 LLM calls + duplicate gates; target: 8s)

Cuts:
- **Step 8 duplicate `--review` rerun** → DELETED. Cache findings from `/ai-commit` step's gate.
- **Step 9 gate rerun** → cached unless commits added since last gate.
- **Step 7 3-lane dispatch** → only the lanes that changed paths (script decides from diff stat).
- **Step 11 PR body compose** → `pr-body-compose.py` generates 80% from spec.md/plan.md frontmatter; LLM fills only "Summary (2-3 bullets)" + "Test Plan checklist".
- **Step 16 watch-and-fix** → unchanged (genuine LLM judgment), but bounded by `AIENG_RALPH_MAX_RETRIES`.

### 17.3 Conflict resolution determinism

`/ai-resolve-conflicts` becomes mostly mechanical:

| Conflict type | Action | LLM? |
|---|---|---|
| Lock files (`*.lock`, `package-lock.json`, `uv.lock`, `poetry.lock`, `Cargo.lock`) | regenerate via package manager | NO |
| Generated files (header sentinel, `// AUTO-GENERATED`) | take theirs | NO |
| Migrations (path matches `migrations/`) | ask user (never auto) | NO |
| Config (YAML/TOML) | 3-way deterministic merge | NO unless ambiguity |
| Code | intent-aware merge | YES |

`resolve-classify.py` runs first; LLM only invoked when type=`code` (or rare `config-ambiguous`).

---

## 18. AGENTS.md / CLAUDE.md Voice Rewrite (Boris + Karpathy DNA)

**Goal**: when a developer installs ai-engineering, the first 30 seconds of reading AGENTS.md make them feel **faster + safer + governed**, not boxed in.

### 18.1 Voice rules (synthesized from Boris + Karpathy)

| Rule | Source | Manifestation |
|---|---|---|
| Imperatives in CAPS for non-negotiables | Boris | `STOP. Read the spec.` `OFFLOAD. Use a subagent.` |
| 4-6 word section openers, bold | Karpathy | `**Code first, prose second.**` |
| Bullets are constraints, not advice | Karpathy | `No abstractions for single-use code.` |
| Arrow notation for rewrites | Karpathy | `"Add validation" → "Write the test that fails first"` |
| Two-file state model | Boris | `tasks/todo.md` + `tasks/lessons.md` (we already have plan.md + LESSONS.md — surface this) |
| Codebase wins ties | Karpathy | "Match existing style. The repo's voice is the standard." |
| Diff is the contract | Karpathy | "Every changed line traces to the request. No drive-by edits." |
| Identity framing for agents | Boris | "You are a senior engineer who ships." |
| Closing falsifiability check | Karpathy | "You shipped this if: tests green, lint clean, spec satisfied, diff focused." |

### 18.2 Proposed AGENTS.md skeleton (≤80 lines for the cross-IDE root)

```markdown
# AGENTS.md

You are a senior engineer who ships. Match the repo's voice. Codebase wins ties.

## Step 0 — Always

STOP. Read CONSTITUTION.md. Read manifest.yml. Run /ai-start.
That's the bootstrap. No exceptions.

## Hard rules

- **TDD**: red test before code. No exceptions.
- **KISS · YAGNI · DRY · SOLID**: applied before each task, checked at /ai-verify.
- **Hexagonal layering**: domain ↛ infra. Linted.
- **Diff is the contract**: every line traces to the spec.
- **Hot-path budgets**: pre-commit < 1s, pre-push < 5s. Profile before adding.

## Skills (the verbs)

`/ai-brainstorm` `/ai-plan` `/ai-build` `/ai-verify` `/ai-review` `/ai-commit` `/ai-pr`
That is the canonical chain. Anything else is a tool, not a step.

## Agents (the writers)

`ai-build` writes code. `ai-verify` checks evidence. `ai-review` judges quality.
Coordinator: `ai-autopilot`. No domain-specialist write agents — Harness proved it doesn't work.

## Lessons + Plans live here

`tasks/plan.md` — what's next.
`tasks/lessons.md` — what we learned.
Update both. They are the contract with future-you.

## You shipped this if

- Tests green
- Lint clean
- Spec satisfied
- Diff focused
- LESSONS.md updated if learning happened
```

### 18.3 CLAUDE.md overlay (Claude-Code-specific) keeps current content but reorders: hot-path discipline → Step 0 → tooling rules. Voice converted to imperative-bold.

---

## 19. Updated Roadmap — 8 Milestones

> M0 + M7 added; M3 expanded with hot-path determinism.

| # | Milestone | Why | Ships |
|---|---|---|---|
| **M0** | AGENTS.md / CLAUDE.md voice rewrite + spec_lifecycle.py | Onboarding fast; spec workspace self-cleaning | Boris+Karpathy DNA AGENTS.md (≤80 lines), CLAUDE.md overlay reordered, `spec_lifecycle.py` + `_history.md` 7-col format, brainstorm/pr/cleanup wired |
| **M1** | Conformance Rubric as Code | Measurable bar | `tools/skill_lint/`, conformance pytest, pre-commit ≤200ms, CI report |
| **M2** | Description CSO + `## Examples` + `## Integration` | Discovery + cohesion | `/ai-prompt --skill <name>` over all 50; bottom-10 human-edited; ≥95% Grade A |
| **M3** | Progressive disclosure + **hot-path determinism** | Token + wall-clock diet | All SKILL.md ≤120 lines; refs one level deep; **`session_bootstrap.py`, `pr-body-compose.py`, `standup-render.py`, `cleanup-run.py`, `commit-compose.py`, `resolve-classify.py`, plus the 3 shared libs**; CI perf budgets enforced |
| **M4** | Renames + mergers + cohesion links | Single canonical path | `/ai-dispatch` → `/ai-build`, `/ai-run` deleted, `ai-run-orchestrator` deleted, `reviewer-design` deleted; aliases for one minor version; mirrors regenerated |
| **M5** | Hexagonal seams + `ai-build` deterministic router | Architecture stamp | `tools/skill_domain/`, `tools/skill_app/`, `tools/skill_infra/`; `deterministic_router.py` for ai-build agent; layer-isolation lint green |
| **M6** | Eval harness + self-improvement loop | Continuous verification | ≥16 evals per skill; CI regression gate; `/ai-skill-tune` consumes evals + LESSONS.md |
| **M7** | Adapter library for `/ai-build` | Stack-correct implementation by default | `.ai-engineering/adapters/{typescript,python,go,rust,swift,csharp,kotlin}/` with conventions + TDD harness + security floor + examples |

---

## 20. Updated Definition of Done — PR #506

Phase A checks (from §7) PLUS:

- [ ] AGENTS.md ≤ 80 lines, Boris+Karpathy voice applied
- [ ] CLAUDE.md hot-path-first reorder applied
- [ ] `spec_lifecycle.py` ships; idempotent transitions tested; wired into brainstorm/pr/cleanup
- [ ] `_history.md` 7-col layout with backward-compat read
- [ ] `session_bootstrap.py` ships; `/ai-start` < 500ms p95 in CI perf test
- [ ] Three shared libs (`manifest_reader`, `git_activity`, `markdown_render`) ship under `_lib/`
- [ ] `/ai-build` (renamed) ships with adapter routing for ≥3 stacks (TS, Python, Go) at minimum
- [ ] `deterministic_router.py` ships; `ai-build` agent receives pre-routed context
- [ ] `pr-body-compose.py` + `commit-compose.py` ship; `/ai-pr` < 8s p95, `/ai-commit` < 1.5s p95
- [ ] `resolve-classify.py` ships; lock-file/gen-file conflicts auto-resolve in CI fixture tests
- [ ] CI perf budgets test (`tests/perf/test_hot_path_budgets.py`) green
- [ ] Skill count = 46, agent count = 23
- [ ] Aliases tested: `/ai-dispatch` → `/ai-build`, `/ai-run` → `/ai-autopilot --backlog`

---

## 21. Updated Out-of-band Inputs

NotebookLM source IDs to cite (verbatim quotes already extracted in `.ai-engineering/runtime/tool-outputs/2026-05-07T220114Z-963a616b89c74bb997d6f7ae81d4a9b4.txt`):

- `9c0fc69d` — *"probabilistic inside, deterministic at the edges"*; computational vs inferential tracks; PEV loop
- `9a8958c4` — *"One agent with full context outperformed twenty with partial context"* (Harness anti-pattern)
- `976df657` — taste invariants as hard CI failures; verifier rejection as structured retry context
- `9d9b9ce9` — implementor isolation via git worktrees; subagents as context firewalls
- `65ccf1ff` — decoupling brain/hands/session; planner-coder split; sandbox boundaries
- `e34fd3e2` — golden path "security and observability come for free"
- `eed86d8c` — golden path is NOT a mandate; make the paved route the obvious choice
- `e358d2da` — developer role shifts from doing work to designing systems that govern work
- `7146c346` — predictive naming as foundational metadata; ambient affordances; UX of intent

External voices:
- Boris CLAUDE.md gist `hqman/e29cb6386c539d795767e8c3fd2c959b` — terse imperatives, two-file state, 50-line ceiling
- Karpathy CLAUDE.md `forrestchang/andrej-karpathy-skills` — bold openers, bullets-as-constraints, arrow rewrites, codebase wins ties

---

## 22. Skill / Agent Split Contract — DRY Boundary

**Problem found**: 5 skill+agent name-pairs duplicate the 6-phase / N-step narrative across two files. Today's pairs (skill lines + agent lines):

| Pair | Skill lines | Agent lines | Total | Issue |
|---|---|---|---|---|
| `ai-autopilot` | 132 | 145 | **277** | 6-phase narrative duplicated; skill over ≤120 target |
| `ai-verify` | 153 | 50 | 203 | skill over target; agent already lean |
| `ai-review` | 136 | 42 | 178 | skill over target; agent already lean |
| `ai-plan` | 117 | 117 | 234 | both repeat phase logic |
| `ai-guide` | 90 | 113 | 203 | mode tables duplicated |

Total bloat across 5 pairs: **1,095 lines**. Target after split: **~750** (~32% reduction). Net DRY gain on the most-loaded surfaces.

### 22.1 Ownership rules (the contract)

| Concern | Lives in skill | Lives in agent | Lives in handler |
|---|---|---|---|
| Trigger description (CSO) | YES (frontmatter) | NO | NO |
| When / when-not | YES | NO | NO |
| Procedure summary (≤1 paragraph per phase) | YES | NO | NO |
| Detailed phase logic | NO | NO | YES (`handlers/phase-*.md`) |
| State machine table | YES (read by both) | NO | NO |
| Flags | YES | NO | NO |
| Identity (1 paragraph) | NO | YES | NO |
| Capabilities bullet list | NO | YES | NO |
| Boundaries (NEVER/ONLY) | NO | YES | NO |
| Escalation protocol | NO | YES | NO |
| Tool whitelist | NO | YES (frontmatter) | NO |
| Model selection (`opus`/`sonnet`) | NO | YES (frontmatter) | NO |
| Self-Challenge questions | NO | YES | NO |
| Subagent dispatch table | YES (summary) | YES (operational) | NO |
| Failure recovery table | YES (user-visible) | NO | NO |
| Examples | YES | NO | NO |
| Integration links | YES | NO | NO |

**Hard rule**: agent file links to skill via `## See also: ../../skills/<name>/SKILL.md`. Agent never restates phase logic. Skill never restates identity.

### 22.2 Inline-vs-Subagent dispatch rule (must be in skill)

Every skill that has a paired agent must declare the dispatch threshold in its `## When to Use` section. Default rule:

```python
# pseudocode in skill body
if (git_diff_files > 50
    OR sub_spec_count > 5
    OR session_token_budget_remaining < 40%
    OR explicit --isolated flag):
    Task(subagent_type="<name>")   # fresh context
else:
    run_inline(read handlers/, dispatch leaf subagents)
```

This rule prevents agent files from being dead weight when main thread can run inline cheaply. It also gives users a knob (`--isolated`) when they know main context is loaded.

### 22.3 Per-pair targets (after split)

| Pair | Skill target | Agent target | Total target | Saved |
|---|---|---|---|---|
| `ai-autopilot` | ≤120 | ≤60 | 180 | −97 |
| `ai-verify` | ≤120 | ≤50 | 170 | −33 |
| `ai-review` | ≤120 | ≤50 | 170 | −8 |
| `ai-plan` | ≤100 | ≤50 | 150 | −84 |
| `ai-guide` | ≤80 | ≤50 | 130 | −73 |
| **Total** | **540** | **260** | **800** | **−295** |

### 22.4 Agent-only files (no skill counterpart)

`ai-build`, `ai-explore`, `ai-guard`, `ai-simplify`, plus the renamed reviewers (`reviewer-*`). These stay agent-only because they are pure subagent dispatch targets — no user-facing slash command. `ai-build` skill (renamed from `/ai-dispatch` per §4) becomes the user surface; `ai-build` agent is the writer it dispatches to.

Targets:
| Agent | Today | Target |
|---|---|---|
| `ai-build.md` | 196 | ≤120 (move adapter routing to `deterministic_router.py`, NOT into agent body) |
| `ai-explore.md` | 137 | ≤80 |
| `ai-guard.md` | 102 | ≤70 |
| `ai-simplify.md` | 110 | ≤70 |

### 22.5 Validation (CI gate)

`tools/skill_lint/` (M1) extends with pair-aware checks:

| Check | Rule |
|---|---|
| Pair detection | If `skills/<name>/SKILL.md` AND `agents/<name>.md` exist → pair |
| No phase-narrative duplication | Diff agent body vs skill body; if ≥3 consecutive headings or steps appear in both → fail |
| Dispatch threshold present | Skill body must contain a numeric threshold rule |
| Agent links back to skill | Agent body must contain `skills/<name>/SKILL.md` reference |
| Length caps | Per §22.3 table |
| Frontmatter split | Skill has `description` (CSO); agent has `description` + `model` + `tools` + `color` |

Failure of any of these blocks the PR.

### 22.6 Wire-in to milestones

- **M3 (progressive disclosure)** absorbs the per-pair length cuts (§22.3).
- **M4 (renames + mergers)** runs the rename pass and clears `ai-dispatch` references in pair files.
- **M5 (hexagonal seams)** introduces the dispatch threshold rule under `tools/skill_app/dispatch_policy.py` so it lives in code, not just prose.
- **M1 (rubric as code)** lint extension covers §22.5 checks.

---

*End of Phase B. Brief now ready for `/ai-brainstorm` → 8 specs (M0…M7). North Star (§0) is the only document anyone needs to keep open during execution.*

