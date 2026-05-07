---
spec: spec-127
title: Skills + Agents Excellence Refactor (Umbrella)
status: approved
effort: large
refs:
  - .ai-engineering/specs/drafts/skills-agents-excellence-refactor.md
  - PR-506
---

# Spec 127 — Skills + Agents Excellence Refactor (Umbrella)

## Summary

The 50-skill / 26-agent surface fails the conformance bar derived from
Anthropic's skill-creator standard and from internal usability audit
(2026-05-07): 0/50 skills carry an `## Examples` block, 6 skills hit
Grade C / D for vague triggers, 5 SKILL.md files exceed the lean
≤120-line ceiling, two agent pairs are near-duplicates
(`ai-autopilot` ↔ `ai-run-orchestrator`, `reviewer-design` orphan),
and seven naming clusters confuse first-time discovery (e.g.
execution trio `/ai-dispatch | /ai-run | /ai-autopilot`). The current
shape also mixes domain (skill procedural intent) with infrastructure
(IDE adapters, hook bytes, MCP clients), so adding a new IDE costs N
skill edits instead of one adapter. This umbrella consolidates eight
milestones (M0–M7) that ship a measurable conformance rubric, slim
descriptions, deduplicated surface (46 skills + 23 agents), hexagonal
seams, deterministic hot-path scripts, evaluation harness, and the
canonical `/ai-build` implementation gateway with multi-stack
adapters projected from `.ai-engineering/contexts/`. After
decomposition by `/ai-autopilot`, each milestone ships as its own
child spec under `.ai-engineering/specs/spec-127/<Mx>/spec.md` with
its own plan, but the body of work delivers as a single PR (#506
reused per operator decision) — a single review surface for one
end-to-end refactor.

## Goals

- `tools/skill_lint --check` exits 0 across the final 46 skills with
  zero Grade D and ≤2 Grade C entries.
- Every skill carries `## Quick start`, `## Workflow`, `## Examples`
  (≥2 invocations), and `## Integration` sections; verified by
  `tests/conformance/test_skills_rubric.py`.
- Every SKILL.md ≤ 120 lines; references > 100 lines live one level
  deep under `references/` with TOC.
- Final surface counts: **46 skills** (down from 50) and **23 agents**
  (down from 26). Verified by registry-count test.
- Every agent passes the parallel rubric: frontmatter `description`
  (CSO third-person), explicit `tools` whitelist, `model` declared
  (`opus` or `sonnet`), at least one dispatch-source reference, no
  orphan agents (every agent file is dispatched by at least one
  skill or referenced in `AGENTS.md`). Verified by
  `tests/conformance/test_agents_rubric.py`.
- All renames live as the canonical name in
  `.claude/skills/<new>/`, `.github/`, `.codex/`, `.gemini/`; legacy
  names are deleted (no alias dispatcher).
- `tests/architecture/test_layer_isolation.py` green: any
  `tools/skill_domain` import of `tools/skill_infra` raises
  `ImportError`.
- `evals/<skill>.jsonl` ships with ≥16 cases (8 should-trigger / 8
  near-miss) for each of the 46 skills; CI regression gate active on
  PRs touching `.claude/skills/**`.
- `/ai-build` adapters hand-authored for 7 stacks (TypeScript,
  Python, Go, Rust, Swift, C#, Kotlin), each implementer using the
  matching `.ai-engineering/contexts/languages/<stack>.md` and
  relevant `frameworks/*.md` files as reference material. Per stack,
  all four files exist and are non-empty:
  `.ai-engineering/adapters/<stack>/conventions.md`,
  `tdd_harness.md`, `security_floor.md`, `examples/<≥2>.md`.
  Verified by `tests/adapters/test_adapter_scaffolding.py` (file
  existence + minimum line count) AND
  `tests/adapters/test_<stack>_fixture.py` per stack — a minimal
  task in each stack exercises the adapter end-to-end (lint + test
  runner invocation) to prove the prose translates to working
  conventions.
- Hot-path budgets enforced by `tests/perf/test_hot_path_budgets.py`
  per the complete brief §14.3 table: pre-commit ≤ 1.0 s
  (ceiling 1.5 s), pre-push ≤ 5.0 s (ceiling 7.0 s), `/ai-start`
  p95 ≤ 0.5 s banner / ≤ 2.0 s `--full`, `/ai-commit` p95 ≤ 1.5 s
  (ceiling 3.0 s), `/ai-pr` p95 ≤ 8.0 s (ceiling 15.0 s),
  `/ai-verify` PASS path ≤ 1.0 s (ceiling 3.0 s), `/ai-cleanup`
  ≤ 1.5 s (ceiling 3.0 s). Regressions > 25 % block the PR.
- Cross-IDE mirrors regenerated for `.github/`, `.codex/`,
  `.gemini/`; mirror tests pass.
- `docs/conformance-report.md` ships with before/after grade table
  and per-skill diff.
- AGENTS.md and CLAUDE.md updated. Verified by
  `tests/docs/test_canonical_docs_consistency.py`: skill count
  in both files matches the registry (46); the seven-step canonical
  chain `/ai-brainstorm → /ai-plan → /ai-build → /ai-verify →
  /ai-review → /ai-commit → /ai-pr` appears verbatim; legacy
  skill names from D-127-04 do not appear; agent count (23)
  matches; new section "Governance hooks" documents
  `skill_lint`, `test_layer_isolation`, eval regression gate,
  hot-path budgets test.

## Non-Goals

- Repair of the existing NDJSON chain break at index 105 of
  `framework-events.ndjson`. Out of scope; tracked as spec-126
  follow-up.
- New product features. The refactor preserves user-visible behavior
  except for renames.
- New IDE platform support beyond Claude Code, Codex, Gemini CLI, and
  GitHub Copilot.
- Hook bytes changes. Only skill registration entries are touched in
  `.claude/settings.json` and the hooks manifest.
- Telemetry semantics changes. Existing event names and fields stay.
- Engram, NotebookLM, or Context7 internals. Adapters only.
- `/ai-engineering` CLI binary changes outside the skill surface
  (e.g., `ai-eng audit` subcommands).
- Backwards-compatibility aliases for renamed skills. No alias
  dispatcher. The new name is the only name.
- Functional refactor of agent prompts. Only cohesion (frontmatter
  CSO, tools whitelist, model declaration, dispatch contract) and
  the ownership boundary contract from §22 of the brief.
- Repair of any in-flight `spec-126` artifacts. spec-126 is
  considered closed and archived to `.ai-engineering/specs/archive/`
  by this work.

## Decisions

### D-127-01: Reuse PR #506 (current spec-126 branch) for delivery

The refactor lands on `feat/spec-126-hook-ndjson-lock-parity` and
ships as part of PR #506. Lock-parity commits land first, refactor
commits stack after with clearly prefixed messages
(`refactor(skills): …`).

**Rationale**: operator-elected. The trade-off (review surface
bloat, mixed-concern rollback risk) was acknowledged before the
decision. Single-PR delivery preserves the operator's stated
intent of one end-to-end change set landing together.

### D-127-02: Umbrella spec + autopilot-decomposed child specs

This `spec.md` is the umbrella. `/ai-autopilot` decomposes the eight
milestones into child specs under
`.ai-engineering/specs/spec-127/M{0..7}/spec.md` and runs
parallel-wave implementation. Plan.md (produced by `/ai-plan`)
orchestrates the eight phases; child plans live under each
milestone directory.

**Rationale**: brainstorm contract emits a single spec; autopilot
contract decomposes into sub-specs. Aligning the two preserves both
contracts. Brief §11 explicitly proposes the sub-dir layout. One
approval gate (this umbrella) unblocks eight parallel waves rather
than requiring eight separate brainstorm sessions.

### D-127-03: spec-126 manually closed; spec.md slot reassigned

spec-126 (NDJSON lock parity) is treated as code-complete and
closed. Its artifacts move to
`.ai-engineering/specs/archive/spec-126-lock-parity/`. The canonical
`spec.md` and `plan.md` slots are reused for spec-127. `_history.md`
is updated to record spec-126 as `shipped` (entry pending PR #506
merge).

**Rationale**: operator confirmed spec-126 is finalized and should
have been closed. Single-slot lifecycle is preserved manually
because `spec_lifecycle.py` (M3 of the brief) ships in this PR but
is not yet authoritative. Manual close prevents two-spec ambiguity
during the refactor.

### D-127-04: No backwards-compatibility aliases on rename

`/ai-dispatch`, `/ai-run`, `/ai-canvas`, `/ai-market`,
`/ai-mcp-sentinel`, `/ai-entropy-gc`, `/ai-instinct`,
`/ai-skill-evolve`, `/ai-platform-audit`,
`review-context-explorer`, `review-finding-validator`,
`ai-run-orchestrator`, `reviewer-design` are deleted in the same
commit that introduces their replacement. No alias dispatcher, no
deprecation window.

**Rationale**: operator confirmed nobody is using the framework
externally; no breaking-change cost. Deleting aliases removes
implementation surface (≈ 1 dispatcher script, 13 alias entries,
13 mirror entries) and prevents muscle memory anchoring on legacy
names. CHANGELOG records the rename table for audit.

### D-127-05: `/ai-canvas` renames to `/ai-visual`

The skill that produces posters, banners, flyers, branding pieces,
cover art, and identity compositions becomes `/ai-visual`. Its
description carries the broader category framing.

**Rationale**: "canvas" is a metaphor (Figma canvas, HTML canvas,
literal canvas); "visual" is the category. `/ai-design` covers UI;
`/ai-visual` covers static visual artifacts. Symmetry holds the
visual quad together (`/ai-design`, `/ai-visual`,
`/ai-animation`, `/ai-slides`). `/ai-poster` was rejected as too
narrow — would miss "banner" and "cover art" trigger phrases.

### D-127-06: Adapter coverage = 7 stacks, hand-written using contexts/ as reference

`/ai-build` ships with adapter directories for TypeScript, Python,
Go, Rust, Swift, C#, and Kotlin. Each adapter is **hand-authored**
as expert per-stack prose by the implementing agent. The
implementer is given the matching
`.ai-engineering/contexts/languages/<stack>.md` and the relevant
`frameworks/*.md` files as reference material to anchor naming,
idioms, error handling, and security floor — then writes
`conventions.md`, `tdd_harness.md`, `security_floor.md`, and
`examples/` from scratch in adapter format. No projection script.

**Rationale**: projection from a reference doc to an adapter doc
discards the expert nuance the adapter needs (TDD harness specifics
per test runner, security floor specifics per stack ecosystem,
idiomatic error patterns, build-tool quirks). The contexts/ files
are reading material — they are designed to *inform a human*, not
to be *parsed by a script*. Hand-writing keeps the adapter prose
authoritative and stack-correct; supplying the contexts/ files as
reference removes the blank-page tax. The 28-file lift (7 stacks ×
4 files) is bounded; each adapter ships with a paired test fixture
that exercises a minimal task in that stack to prove the adapter
prose actually compiles to working conventions. Stacks beyond the 7
(C++, Java, Dart, PHP, Bash, SQL) remain candidates for follow-up
PRs once a real `/ai-build` task targets them.

### D-127-13: Python package naming uses underscore (PEP 8)

`tools/skill_domain/`, `tools/skill_app/`, `tools/skill_infra/` and
any sibling Python packages use the underscore separator. CLI- or
config-only paths under `.ai-engineering/`, `.claude/`, `.github/`,
`.codex/`, `.gemini/` continue to use dash.

**Rationale**: Python module names must match
`[a-zA-Z_][a-zA-Z0-9_]*` per the language grammar.
`from tools.skill-domain import …` is a `SyntaxError` because the
parser interprets `-` as the binary minus operator. The repo
already follows this split: `src/ai_engineering/` (underscore,
importable) versus `.ai-engineering/` (dash, CLI path). The new
hexagonal directories sit in `tools/`, which is on the Python
import path, therefore underscore is mandatory. This decision is
recorded so reviewers do not re-litigate the dash-vs-underscore
question per directory; the rule is "dash for paths, underscore
for Python packages, follow existing repo precedent".

### D-127-07: Eval corpus = LLM-generated + human review on top-confusion cases

For each of the 46 skills, `scripts/run_loop` (skill-creator
optimizer) generates 16 candidate eval cases (8 should-trigger / 8
near-miss) using the optimized description. The top-10 highest
near-miss-confusion cases per skill are reviewed by the operator
before commit; remaining cases land as-is.

**Rationale**: pure-LLM unattended risks false-positive regression
gates on synthetic cases; pure-human authorship is ~40 hours of
work. Hybrid keeps cost ≈ 50 minutes total review time while
catching the highest-impact near-miss patterns. Regression gate
still active because LLM-generated cases are deterministic — they
fail loud when descriptions drift away from intent.

### D-127-08: Conformance bar = 10 rules with ≤120-line ceiling

Every skill, at PR-merge time, must satisfy the brief's §3 ten
rules (frontmatter validation, third-person CSO description, ≥3
trigger phrases, negative scoping for adjacent skills, ≤500 lines
hard / ≤120 lines internal target, ≤5 000 tokens, required
sections, ≥2 examples, refs nesting, ≥3 evals defined, no
anti-patterns). Pre-commit runs `skill_lint --check` ≤ 200 ms.

**Rationale**: lint surface that is faster than typing prevents
regressions. The 120-line target sits below Anthropic's 500-line
hard ceiling — leaves headroom for future additions without
breaching the system-prompt token budget. The 10-rule bar is the
audit anchor; relaxing any rule requires a separate spec.

### D-127-09: Hexagonal layer-isolation enforced via test, not lint

`tools/skill_domain/` (zero deps), `tools/skill_app/` (use cases
calling ports), `tools/skill_infra/` (adapters per port). Layer
isolation is enforced by
`tests/architecture/test_layer_isolation.py` which imports each
domain module and asserts no infra symbol is reachable. Test-level
enforcement, not custom lint plugin.

**Rationale**: tests are cheaper to maintain than custom AST
linters and catch the same import violations. The taste-invariant
philosophy from NotebookLM `976df657` ("invariants as hard CI
failures") is satisfied. Test-only also keeps the domain layer
deployable to other Python tooling without project-specific lint
configs.

### D-127-10: Final surface = 46 skills + 23 agents

Skills go from 50 to 46: `−1` `/ai-run` (merged into
`/ai-autopilot --backlog`), `−1` `/ai-board-discover` +
`/ai-board-sync` (merged into `/ai-board <discover|sync>`), `−1`
`/ai-release-gate` (merged into `/ai-verify --release`), `−1`
`/ai-dispatch` rename to `/ai-build` collapses any duplicate.
Agents go from 26 to 23: `−1` `ai-run-orchestrator` (merged into
`ai-autopilot`), `−1` `reviewer-design` (merged into
`reviewer-frontend`), `−1` `ai-dispatch` agent if duplicate (per
brief §4).

**Rationale**: each merger is justified by either true duplication
(same pipeline, different intake) or by the boundary becoming a
mode flag rather than a new skill. Counts are the regression
anchor; if a future change inflates either count, the operator is
forced to justify why a new entry is not a mode flag on an
existing skill.

### D-127-11: `/ai-build` is the canonical implementation gateway

`/ai-dispatch` skill renames to `/ai-build` and pairs with the
`ai-build` agent. Approved plan → `/ai-build` reads
`spec.md` + `plan.md`, resolves stack from `manifest.yml`,
deterministic-routes each task to the adapter, dispatches the
`ai-build` agent in an isolated worktree, runs Ralph convergence
+ `/ai-verify` after each task, and chains
`/ai-review → /ai-commit → /ai-pr` after the last.

**Rationale**: brief §13. Single canonical entry from approved plan
to merged code. Verb-noun naming (Karpathy convention). Pairs
1:1 with the agent. Deterministic router keeps LLM cost out of
adapter selection. `/ai-autopilot --spec <id>` wraps `/ai-build`
for autonomous mode.

### D-127-12: `/ai-autopilot` is the single autonomous wrapper

`/ai-autopilot` keeps the 6-phase pipeline. Three intake adapters
land as flags: `--task` (single task), `--backlog` (replaces
`/ai-run`), `--spec` (umbrella spec, decomposes into child specs).
The `ai-autopilot` agent is the sole orchestrator;
`ai-run-orchestrator` is deleted.

**Rationale**: brief §12. NotebookLM `9a8958c4`: "one agent with
full context outperformed twenty with partial context". Three
intake shapes share the same pipeline; separating them by skill
duplicated the orchestrator. Mode-flag approach matches the
KISS / one-canonical-path-per-intent stamp.

## Risks

- **PR #506 review surface bloat** — spec-126 (small, narrow lock
  parity) and spec-127 (large, broad refactor) on the same PR makes
  the diff hard to review. *Mitigation*: spec-126 commits land
  first and are squash-mergeable independently of refactor commits;
  refactor commits use `refactor(skills): …` prefix; PR body
  splits the two concerns into separate review check-lists.
- **Mass renames without aliases break user muscle memory** —
  operator accepted the trade-off. *Mitigation*: CHANGELOG ships
  with rename table; `/ai-help` (existing) updated to
  matchback-suggest the new name when a deleted name is typed
  (single-line addition, ≤ 30 LOC).
- **LLM-generated eval bias** — the corpus may share blind spots
  with the description it was generated from, missing real-user
  trigger phrasing. *Mitigation*: each skill's near-miss set draws
  trigger phrases from `git log --grep` over the last 12 months of
  user-written commit messages; human review focuses on the
  near-miss tail; first user-reported false-positive becomes a
  permanent eval case.
- **Hexagonal refactor scope creep into behavior changes** — M5 is
  meant to be file moves + import rewrites only. *Mitigation*:
  `test_layer_isolation.py` is the only behavior change in M5;
  every other diff in M5 must be import-only or file-move
  (verified by per-commit `git diff --stat` size cap in CI).
- **Hand-written adapter prose drifts over time** — without a
  generator, conventions in `.ai-engineering/adapters/<stack>/` can
  drift from the canonical `contexts/languages/<stack>.md` reference
  as the language evolves (new test runner default, new security
  advisory, new idiom). *Mitigation*: M7 ships per-stack adapter
  fixtures (`tests/adapters/test_<stack>_fixture.py`) that exercise
  the adapter against a minimal task — broken adapter prose fails
  the fixture; CHANGELOG-style entry at the top of each
  `conventions.md` records the source `contexts/` doc revision used
  as reference, making drift detectable in review;
  `/ai-skill-tune` (renamed evolve) is extended in a follow-up to
  diff adapter prose against the latest contexts/ doc and surface
  drift as a proposal PR (out of scope for this PR).
- **Hot-path budget regressions under coverage / Windows runners**
  — perf tests have flaked before on slow CI. *Mitigation*: tests
  use a 25 % regression tolerance against committed baselines; CI
  retries once on transient infra flake but not on assertion
  failure; baseline file is regenerated only via explicit
  `scripts/perf-baseline.py` command, never in CI.
- **Mirror drift across `.github/`, `.codex/`, `.gemini/`** —
  rename + section additions touch all four IDE surfaces. Drift
  re-introduces the discovery confusion the refactor is meant to
  fix. *Mitigation*: `sync_command_mirrors.py` runs in pre-push
  and CI; manifest hash gate fails loud on stale mirrors;
  `tests/mirrors/test_count_parity.py` asserts each mirror has the
  same skill count as `.claude/skills/`.
- **Manual spec-126 close vs lifecycle automation introduced in this
  PR** — spec_lifecycle.py (M-of-brief §15) ships in this PR but is
  not authoritative until after merge; the operator-elected manual
  close of spec-126 may collide with the new state machine.
  *Mitigation*: lifecycle script ships in observe-only mode for
  spec-126's archived artifacts (read but do not write); first
  authoritative transition is for spec-127's own `mark_shipped` at
  PR merge.
- **Eight-milestone scope on single PR is unprecedented** — even
  with autopilot decomposition, a PR carrying ~50 SKILL.md edits +
  hexagonal refactor + 7 adapters + eval harness + lifecycle
  script + commit/pr/start scripts is large. *Mitigation*: each
  milestone is independently reviewable in the PR via a per-M
  changelog table; reviewers walk M0 → M7; CI gates per milestone
  catch regression before the next milestone's commits land.

## References

- doc: .ai-engineering/specs/drafts/skills-agents-excellence-refactor.md
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/contexts/languages/ (14 language references)
- doc: .ai-engineering/contexts/frameworks/ (15+ framework references)
- doc: AGENTS.md (cross-IDE rules; updated in this work)
- doc: CONSTITUTION.md (Articles I-V, governance contract)
- doc: CLAUDE.md (Claude Code overlay; updated in this work)
- doc: ~/.agents/skills/skill-creator/SKILL.md (Anthropic standard)
- doc: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- pr: ai-engineering/ai-engineering#506
- spec: spec-126 (lock parity, archived to specs/archive/spec-126-lock-parity/)
- spec: spec-051 (architecture v3 active; this refactor's hexagonal goal extends it)
- spec: spec-001 (rewrite v2 baseline)
- research: NotebookLM b8a09700-2ce7-4d6c-84d7-82b89765ea53 (anchor research)
- research: NotebookLM 9a8958c4 (one-agent-with-full-context > 20-agent split)
- research: NotebookLM 9c0fc69d (probabilistic inside, deterministic at edges)
- research: NotebookLM 976df657 (taste invariants as hard CI failures)
- research: NotebookLM 9d9b9ce9 (worktree isolation for implementor agents)
- research: NotebookLM 65ccf1ff (planner-coder split + sandbox boundaries)
- research: NotebookLM e34fd3e2 (golden path: security/observability for free)
- research: NotebookLM eed86d8c (paved route is the obvious choice, not a mandate)
- research: NotebookLM 7146c346 (predictive naming as foundational metadata)
- doc: .ai-engineering/runtime/tool-outputs/2026-05-07T220114Z-963a616b89c74bb997d6f7ae81d4a9b4.txt (extracted NotebookLM quotes)

## Open Questions

None. All seven brainstorm interrogation gates resolved (PR #506
reuse, umbrella + child sub-specs, eval LLM+human, /ai-canvas →
/ai-visual, no backwards-compat aliases, all 7 adapter stacks via
projection, spec-126 manual close).
