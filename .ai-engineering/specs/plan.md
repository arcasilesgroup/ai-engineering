# Plan: spec-127 Skills + Agents Excellence Refactor (Umbrella)

## Pipeline: full
## Phases: 11
## Tasks: 115 (build: 92, verify: 20, guard: 3)

## Architecture

**Pattern**: Hexagonal Architecture (Ports & Adapters).

**Justification**: spec D-127-09 mandates a clean split between
domain (skill/agent dataclasses + conformance rubric, zero I/O),
application (linter, evaluator, optimizer, audit use cases calling
ports), and infrastructure (hook bytes, mirror sync, MCP clients,
GitHub/ADO board, Engram, NotebookLM, Context7, IDE adapters). The
spec's "When to use" criteria for hexagonal map exactly: multiple
external integrations (4 IDE mirrors + 3 MCP servers + 2 board
providers), need for swap-in adapters when adding a new IDE without
touching domain, layer-isolation enforced by
`tests/architecture/test_layer_isolation.py`. Repo precedent
already supports this — `src/ai_engineering/state/` shows
in-flight port-style decoupling between core and observability.

## Design

Skipped — refactor scope is rename / reorganize / dedupe of
skills + agents + tooling. No new UI surface, no design-intent
artifact. `/ai-canvas → /ai-visual`, `/ai-animation`, `/ai-slides`,
`/ai-design` are skill renames / cohesion edits, not new UI work.

## Decomposition Note

This plan is the **umbrella orchestration**. `/ai-autopilot --spec
spec-127` decomposes Phases 2-9 into child specs under
`.ai-engineering/specs/spec-127/M{0..7}/spec.md` with their own
plan.md files. Tasks below are deliverable-grained (1 task =
1 file / test / script / commit). Implementation detail lives in
child plans created during Phase 1.

---

### Phase 0: Pre-flight & Bootstrap

**Gate**: spec-126 archived, branch confirmed, baseline metrics
captured.

- [ ] T-0.1: Verify `.ai-engineering/specs/archive/spec-126-lock-parity/{spec.md,plan.md}` present (agent: verify)
- [ ] T-0.2: Update `.ai-engineering/specs/_history.md` row for spec-126 → status `shipped` once PR #506 merges; add row for spec-127 with status `in-progress` (agent: build)
- [ ] T-0.3: Capture hot-path baseline timings via `scripts/perf-baseline.py --commit HEAD` into `tests/perf/baseline.json` (agent: build)
- [ ] T-0.4: `/ai-guard` pre-dispatch check on the umbrella spec — confirm no constitutional violations (agent: guard)

---

### Phase 1: Autopilot Decomposition (M0 enabler)

**Gate**: 8 child specs exist with status `draft`; per-milestone
`plan.md` stubs present.

- [ ] T-1.1: Invoke `/ai-autopilot --spec spec-127 --decompose-only`; produces `.ai-engineering/specs/spec-127/M{0..7}/spec.md` + stub plan.md (agent: build)
- [ ] T-1.2: Verify each child spec passes `spec-schema.md` validation (agent: verify)
- [ ] T-1.3: Verify each child plan.md has Phases + Gate placeholders ready for `/ai-plan` per-milestone refinement (agent: verify)
- [ ] T-1.4: `/ai-guard` on each child spec — flag any inherited constitutional drift (agent: guard)

---

### Phase 2: M0 Foundations + M1 Conformance Rubric (parallel)

**Gate**: `skill_lint --check` runs in CI green against current 50
skills (baseline grade); `spec_lifecycle.py` idempotent transitions
proven in tests; AGENTS.md + CLAUDE.md voice updated.

#### M0 — Spec lifecycle + voice updates

- [ ] T-2.1: Write failing tests `tests/unit/specs/test_spec_lifecycle.py` for `start_new`, `mark_shipped`, `archive`, `sweep`, `status` (agent: build)
- [ ] T-2.2: Implement `.ai-engineering/scripts/spec_lifecycle.py` (stdlib only, <500ms, atomic writes, reuses `_lib/locking.artifact_lock`) — DO NOT modify test files from T-2.1 (agent: build)
- [ ] T-2.3: Wire `start_new` into `/ai-brainstorm` step 1; `mark_shipped` into `/ai-pr` post-merge; `sweep()` into `/ai-cleanup --specs` (agent: build)
- [ ] T-2.4: Update `_history.md` to 7-column layout `(ID, Title, Status, Created, Shipped, PR, Branch)`; preserve backward-compat read of legacy 6-col rows (agent: build)
- [ ] T-2.5: Failing test `tests/unit/docs/test_canonical_docs_consistency.py` (agent: build)
- [ ] T-2.6: Update AGENTS.md to ≤80 lines, Boris+Karpathy voice, two-file state pattern; reference 46 skills + 23 agents post-rename (agent: build)
- [ ] T-2.7: Update CLAUDE.md hot-path-first reorder; add governance hooks section enumerating skill_lint, layer_isolation, eval gate, perf budgets (agent: build)
- [ ] T-2.8: Verify `tests/unit/docs/test_canonical_docs_consistency.py` green (agent: verify)

#### M1 — Conformance rubric as code

- [ ] T-2.9: Scaffold `tools/skill_domain/__init__.py` + `tools/skill_app/__init__.py` + `tools/skill_infra/__init__.py` (Python pkg, underscore per D-127-13) (agent: build)
- [ ] T-2.10: Failing tests `tests/conformance/test_skills_rubric.py` covering brief §3 ten rules (agent: build)
- [ ] T-2.11: Failing tests `tests/conformance/test_agents_rubric.py` covering parallel rubric (frontmatter CSO, tools whitelist, model declared, dispatch ref, no orphan) (agent: build)
- [ ] T-2.12: Implement `tools/skill_domain/rubric.py` — pure-Python validator dataclasses; DO NOT modify test files from T-2.10/T-2.11 (agent: build)
- [ ] T-2.13: Implement `tools/skill_lint/cli.py` exposing `skill_lint --check` and `--baseline` (agent: build)
- [ ] T-2.14: Add `skill_lint --check` to pre-commit (≤200ms parallel walk) (agent: build)
- [ ] T-2.15: Run `skill_lint --baseline` over current 50 skills; generate `docs/conformance-report.md` baseline section; commit as `docs(conformance): baseline grade pre-refactor` (agent: build)
- [ ] T-2.16: Verify `pytest tests/conformance/` green at baseline grades (agent: verify)

---

### Phase 3: M2 Description CSO Pass + Examples + Integration

**Gate**: All 46 final skills + 23 agents grade A on rubric; zero
Grade D, ≤2 Grade C; every skill has ≥2 `## Examples` and an
`## Integration` section.

> Note: tasks in this phase run in 5-skill batches as parallel
> autopilot waves. Each batch is a single ai-build invocation
> processing 5 skills end-to-end.

- [ ] T-3.1: Wave A — `/ai-prompt --skill` over Grade D + bottom-10 (10 skills): ai-entropy-gc, ai-instinct, ai-mcp-sentinel, ai-canvas, ai-eval, ai-run, ai-platform-audit, ai-governance, ai-skill-evolve, ai-constitution (agent: build)
- [ ] T-3.2: Wave B — Grade C cluster (6 skills): ai-cleanup, ai-pipeline, ai-mcp-sentinel companions (agent: build)
- [ ] T-3.3: Wave C — Grade B (14 skills) (agent: build)
- [ ] T-3.4: Wave D — Grade A (28 skills) — minor polish only (agent: build)
- [ ] T-3.5: For each of 50 skills, append `## Examples` (≥2 invocations) section. Batched 5/wave (agent: build)
- [ ] T-3.6: For each skill with predecessor/successor, append `## Integration` section linking adjacent skills. Batched 5/wave (agent: build)
- [ ] T-3.7: Apply parallel agent rubric pass — every agent file gets frontmatter `description` (CSO third-person), explicit `tools` whitelist, `model` declared, dispatch-source comment (agent: build)
- [ ] T-3.8: Re-run `skill_lint --check`; expected zero D, ≤2 C (agent: verify)
- [ ] T-3.9: `pytest tests/conformance/test_skills_rubric.py tests/conformance/test_agents_rubric.py` green (agent: verify)

---

### Phase 4: M3 Progressive-Disclosure Slim-Down

**Gate**: every SKILL.md ≤120 lines; every reference ≤300 lines
with TOC; no nested ref→ref.

- [ ] T-4.1: Identify top-5 over-length skills: ai-animation 228, ai-video-editing 194, ai-governance 182, ai-platform-audit 181, ai-skill-evolve 179 (agent: verify)
- [ ] T-4.2: Slim ai-animation → ≤120 lines; move detail to `references/` (agent: build)
- [ ] T-4.3: Slim ai-video-editing → ≤120 lines (agent: build)
- [ ] T-4.4: Slim ai-governance → ≤120 lines (agent: build)
- [ ] T-4.5: Slim ai-platform-audit → ≤120 lines (agent: build)
- [ ] T-4.6: Slim ai-skill-evolve → ≤120 lines (agent: build)
- [ ] T-4.7: Apply skill/agent split contract per brief §22 — pair files (ai-autopilot, ai-verify, ai-review, ai-plan, ai-guide) reduce duplication, declare dispatch threshold in skill body (agent: build)
- [ ] T-4.8: Verify no nested ref via `tools/skill_lint/checks/no_nested_refs.py`; new test `tests/conformance/test_no_nested_refs.py` green (agent: verify)
- [ ] T-4.9: Run `skill_lint --check` — assert all SKILL.md ≤120 lines (agent: verify)

---

### Phase 5: M4 Renames + Mergers

**Gate**: skill count = 46, agent count = 23; renames live across
all four IDE surfaces; no legacy alias dispatcher exists; mirror
parity tests green.

> Note: D-127-04 hard rule — pure delete-and-rename, no aliases.
> Single commit per rename keeps each rollback unit clean.

- [ ] T-5.1: `/ai-dispatch` → `/ai-build` (skill rename + agent pair). Update `.claude/skills/ai-build/`, `.claude/agents/ai-build.md`, mirrors in `.github/`, `.codex/`, `.gemini/`. Delete `.claude/skills/ai-dispatch/` (agent: build)
- [ ] T-5.2: `/ai-run` deleted; `--backlog` flag added to `/ai-autopilot` skill body (agent: build)
- [ ] T-5.3: `ai-run-orchestrator` agent deleted; functionality absorbed by `ai-autopilot` agent with `--source <github|ado|local>` flag (agent: build)
- [ ] T-5.4: `/ai-canvas` → `/ai-visual` (skill rename + description rewrite per D-127-05) (agent: build)
- [ ] T-5.5: `/ai-market` → `/ai-gtm` (agent: build)
- [ ] T-5.6: `/ai-mcp-sentinel` → `/ai-mcp-audit` (agent: build)
- [ ] T-5.7: `/ai-entropy-gc` → `/ai-simplify-sweep` (agent: build)
- [ ] T-5.8: `/ai-instinct` → `/ai-observe` (agent: build)
- [ ] T-5.9: `/ai-skill-evolve` → `/ai-skill-tune` (agent: build)
- [ ] T-5.10: `/ai-platform-audit` → `/ai-ide-audit` (agent: build)
- [ ] T-5.11: `review-context-explorer` agent → `reviewer-context` (agent: build)
- [ ] T-5.12: `review-finding-validator` agent → `reviewer-validator` (agent: build)
- [ ] T-5.13: `reviewer-design` agent deleted; design-system rules absorbed into `reviewer-frontend` agent body (agent: build)
- [ ] T-5.14: Merge `ai-board-discover` + `ai-board-sync` → `/ai-board <discover|sync>` subcommand pattern (agent: build)
- [ ] T-5.15: Merge `ai-release-gate` → `/ai-verify --release` mode flag; delete release-gate skill dir (agent: build)
- [ ] T-5.16: Update `/ai-help` to matchback-suggest new name on legacy-name typo (≤30 LOC addition) (agent: build)
- [ ] T-5.17: Re-run `python .ai-engineering/scripts/sync_command_mirrors.py`; verify `.github/`, `.codex/`, `.gemini/` regenerated (agent: build)
- [ ] T-5.18: Failing test `tests/mirrors/test_count_parity.py` (agent: build)
- [ ] T-5.19: Verify `tests/mirrors/test_count_parity.py` green; skill count 46, agent count 23 (agent: verify)
- [ ] T-5.20: Update CHANGELOG.md with rename table + deletion list (agent: build)

---

### Phase 6: M5 Hexagonal Seams Made Explicit

**Gate**: `tests/architecture/test_layer_isolation.py` green; no
behavior change (file moves + import rewrites only); per-commit
diff size cap respected.

- [ ] T-6.1: Failing test `tests/architecture/test_layer_isolation.py` — assert `import tools.skill_infra` from any `tools.skill_domain` module raises `ImportError` (agent: build)
- [ ] T-6.2: Move pure-Python skill/agent dataclasses + validators into `tools/skill_domain/` (zero deps); DO NOT modify test files from T-6.1 (agent: build)
- [ ] T-6.3: Move use-case orchestrators (linter, evaluator, optimizer, audit) into `tools/skill_app/` calling only ports (agent: build)
- [ ] T-6.4: Define ports in `tools/skill_app/ports/`: SkillPort, AgentPort, HookPort, BoardPort, MemoryPort, TelemetryPort (agent: build)
- [ ] T-6.5: Move existing hook bytes / mirror sync / MCP clients / Engram / NotebookLM / Context7 / GitHub-ADO board into `tools/skill_infra/` adapter modules implementing one port each (agent: build)
- [ ] T-6.6: Refactor `/ai-create`, `/ai-skill-tune`, `/ai-prompt`, `/ai-ide-audit` to consume application layer only (no infra imports) (agent: build)
- [ ] T-6.7: Verify `pytest tests/architecture/test_layer_isolation.py` green (agent: verify)
- [ ] T-6.8: Verify per-commit `git diff --stat` ≤200 LOC for each M5 commit (size cap CI gate) (agent: verify)

---

### Phase 7: M6 Eval Harness + Self-Improvement Loop

**Gate**: each of 46 skills ships ≥16 evals (8 should-trigger / 8
near-miss); CI regression gate active on `.claude/skills/**`;
baseline pass@1 captured.

> Note: per D-127-07, LLM-generated + human review on top-10
> near-miss confusion cases per skill. Total review budget ≈
> 50 minutes operator time.

- [ ] T-7.1: Implement `scripts/run_loop_skill_evals.py` driving `skill-creator` optimizer over each skill's description (agent: build)
- [ ] T-7.2: Generate `evals/<skill>.jsonl` with 16 cases × 46 skills (LLM pass) (agent: build)
- [ ] T-7.3: Generate near-miss trigger phrases per skill via `git log --grep` over 12 months of user commit messages — feed into eval generator as adversarial prompts (agent: build)
- [ ] T-7.4: Operator review of top-10 near-miss cases per skill (manual gate; output committed) (agent: build)
- [ ] T-7.5: Failing test `tests/integration/test_eval_regression_gate.py` — asserts `>5%` pass@1 regression fails CI (agent: build)
- [ ] T-7.6: Implement `/ai-eval --skill-set` mode running optimizer pass@k against eval corpus; DO NOT modify test files from T-7.5 (agent: build)
- [ ] T-7.7: Add CI workflow step: on PR touching `.claude/skills/**`, run `ai-eval --skill-set --regression`; fail loud on >5% pass@1 regression (agent: build)
- [ ] T-7.8: Update `/ai-skill-tune` to consume prior evals + Engram observations + LESSONS.md and propose description deltas as PR-only output (no auto-merge) (agent: build)
- [ ] T-7.9: Capture baseline pass@1 in `evals/baseline.json`; commit; verify `pytest tests/integration/test_eval_regression_gate.py` green (agent: verify)

---

### Phase 8: M7 Adapter Library for /ai-build

**Gate**: 7 adapter dirs present with all 4 required files
non-empty; per-stack fixture green; deterministic_router.py
routes a sample task per stack.

> Note: D-127-06 — hand-authored adapters using
> `contexts/languages/` + `contexts/frameworks/` as reference
> material. 28 file deliverables (7 stacks × 4 files).

- [ ] T-8.1: Failing test `tests/adapters/test_adapter_scaffolding.py` — file existence + minimum line count per adapter (agent: build)
- [ ] T-8.2: Author `.ai-engineering/adapters/typescript/{conventions.md,tdd_harness.md,security_floor.md,examples/}` using `contexts/languages/typescript.md` + `contexts/frameworks/{nextjs,react,nodejs,bun}.md` as reference; DO NOT modify test files from T-8.1 (agent: build)
- [ ] T-8.3: Author `.ai-engineering/adapters/python/` referencing `contexts/languages/python.md` + `contexts/frameworks/{django,api-design,backend-patterns}.md` (agent: build)
- [ ] T-8.4: Author `.ai-engineering/adapters/go/` referencing `contexts/languages/go.md` (agent: build)
- [ ] T-8.5: Author `.ai-engineering/adapters/rust/` referencing `contexts/languages/rust.md` (agent: build)
- [ ] T-8.6: Author `.ai-engineering/adapters/swift/` referencing `contexts/languages/swift.md` + `contexts/frameworks/ios.md` (agent: build)
- [ ] T-8.7: Author `.ai-engineering/adapters/csharp/` referencing `contexts/languages/csharp.md` + `contexts/frameworks/aspnetcore.md` (agent: build)
- [ ] T-8.8: Author `.ai-engineering/adapters/kotlin/` referencing `contexts/languages/kotlin.md` + `contexts/frameworks/android.md` (agent: build)
- [ ] T-8.9: Each `conventions.md` opens with a header pinning source-revision: `<!-- source: contexts/languages/<stack>.md @ <git-sha> -->` (agent: build)
- [ ] T-8.10: Per-stack fixture: `tests/adapters/test_<stack>_fixture.py` exercises a minimal task (lint + test runner invocation) using the adapter prose (agent: build)
- [ ] T-8.11: Failing test `tests/unit/router/test_deterministic_router.py` covering all 7 stacks (agent: build)
- [ ] T-8.12: Implement `tools/skill_app/deterministic_router.py` — task path + spec stack → adapter; <50 ms; DO NOT modify test files from T-8.11 (agent: build)
- [ ] T-8.13: Wire router into `/ai-build` skill body before `ai-build` agent invocation (agent: build)
- [ ] T-8.14: Verify all adapter scaffolding + fixture tests green (agent: verify)

---

### Phase 9: Hot-Path Determinism + Integration

**Gate**: hot-path budgets test green; daily-driver L→D conversions
shipped for top-15 skills per brief §14.2; `/ai-start` <500ms p95.

- [ ] T-9.1: Failing test `tests/perf/test_hot_path_budgets.py` covering all 7 surfaces from brief §14.3 (agent: build)
- [ ] T-9.2: Implement shared libs under `.ai-engineering/scripts/skills/_lib/`: `manifest_reader.py`, `git_activity.py`, `markdown_render.py`; DO NOT modify test files from T-9.1 (agent: build)
- [ ] T-9.3: Implement `session_bootstrap.py` (<300ms, JSON out, parallel git subprocs); rewire `/ai-start` to render 3-line banner from JSON (agent: build)
- [ ] T-9.4: Implement `pr-body-compose.py` for `/ai-pr`; LLM only for narrative bullets + Test Plan (agent: build)
- [ ] T-9.5: Implement `commit-compose.py` for `/ai-commit`; LLM only for `<desc>` clause when `--force "msg"` absent (agent: build)
- [ ] T-9.6: Implement `standup-render.py`, `cleanup-run.py`, `docs-changelog.py`, `docs-readme-sync.py` (agent: build)
- [ ] T-9.7: Implement `autopilot-fsm.py` (YAML transitions); rewire `/ai-autopilot` non-code-change steps through it (agent: build)
- [ ] T-9.8: Implement `resolve-classify.py` + `resolve-lock.py` for `/ai-resolve-conflicts`; LLM only on true code conflicts (agent: build)
- [ ] T-9.9: Implement `governance-eval.py` (OPA wrapper) for `/ai-governance` (agent: build)
- [ ] T-9.10: Implement `eval-run.py`, `eval-scoreboard.py` for `/ai-eval` (agent: build)
- [ ] T-9.11: Implement `security-compose.py` for `/ai-security` (agent: build)
- [ ] T-9.12: Implement `slides-validate.py` (headless 8 viewports) for `/ai-slides` (agent: build)
- [ ] T-9.13: Implement `board-discover.py`, `board-sync.py` for `/ai-board` (agent: build)
- [ ] T-9.14: Verify `pytest tests/perf/test_hot_path_budgets.py` green; regressions ≤25% vs baseline (agent: verify)

---

### Phase 10: Definition of Done + PR

**Gate**: full DoD from spec Goals satisfied; PR #506 body composed
from spec checklist; CHANGELOG entry; `/ai-pr` ready to invoke.

- [ ] T-10.1: Final pass — run `skill_lint --check` over all 46 skills, expect exit 0 zero D ≤2 C (agent: verify)
- [ ] T-10.2: Final pass — run all conformance + architecture + adapter + perf + mirror tests; collect summary (agent: verify)
- [ ] T-10.3: Update `docs/conformance-report.md` with after-table; diff baseline → final (agent: build)
- [ ] T-10.4: Update CHANGELOG.md with full rename + deletion + addition table; cite spec-127 milestones (agent: build)
- [ ] T-10.5: Verify hot-path budgets test green vs `tests/perf/baseline.json` (agent: verify)
- [ ] T-10.6: `/ai-guard` final advisory check before `/ai-pr` invocation (agent: guard)
- [ ] T-10.7: Update `_history.md` row spec-127 → status `shipped` once PR #506 merges (manual or via spec_lifecycle.py `mark_shipped`) (agent: build)

---

## Phase Dependency Graph

```
P0 (preflight) ─→ P1 (decompose) ─→ P2 (M0+M1) ─┬─→ P3 (M2)
                                                  ├─→ P4 (M3) (after P3)
                                                  ├─→ P5 (M4) (after P3)
                                                  ├─→ P6 (M5) (after P2)
                                                  ├─→ P7 (M6) (after P3)
                                                  └─→ P8 (M7) (after P2)
P3+P4+P5+P6+P7+P8 ─→ P9 (hot-path) ─→ P10 (DoD)
```

P3..P8 are parallelizable post-P2. `/ai-autopilot` runs them as
parallel waves; the dependency graph above is its DAG.

## TDD Pairing Note

RED→GREEN pairs in this plan: T-2.1→T-2.2, T-2.5→T-2.6/2.7,
T-2.10/2.11→T-2.12, T-6.1→T-6.2, T-7.5→T-7.6, T-8.1→T-8.2..T-8.8,
T-8.11→T-8.12, T-9.1→T-9.2..T-9.13. Each GREEN task carries the
constraint "DO NOT modify test files from the preceding RED task"
per ai-plan TDD enforcement rule.

## Done Conditions (rolled up from spec Goals)

- [ ] `tools/skill_lint --check` exit 0 across 46 skills
- [ ] Every skill has ≥2 `## Examples` + `## Integration` section
- [ ] Every SKILL.md ≤ 120 lines; refs ≤ 300 lines, no nesting
- [ ] Skill count = 46, agent count = 23
- [ ] Agent rubric green (frontmatter CSO, tools whitelist, model declared, dispatch ref, no orphan)
- [ ] All renames live in `.claude/`, `.github/`, `.codex/`, `.gemini/`; legacy names deleted; no alias dispatcher
- [ ] `tests/architecture/test_layer_isolation.py` green
- [ ] `evals/<skill>.jsonl` ≥16 cases per skill; CI regression gate active
- [ ] 7 adapter dirs with 4 files each; per-stack fixtures green
- [ ] Hot-path budgets per brief §14.3 met; regressions ≤25%
- [ ] Mirror parity tests green
- [ ] `docs/conformance-report.md` shipped with before/after diff
- [ ] AGENTS.md + CLAUDE.md updated; `test_canonical_docs_consistency.py` green
- [ ] CHANGELOG entry shipped with rename/deletion/addition table
