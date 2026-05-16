---
title: Less-Is-More Quality Engine
status: draft
audience: framework-operator
branch: spec-tbd/less-is-more-quality-engine
length_estimate: ~14 sections, four waves, ~4,700 LOC net reduction across tests + workflows + agents (production net-neutral by design)
authoring_style: declarative, evidence-first, no ceremony
principles_required:
  - "§10.1 KISS"
  - "§10.2 YAGNI"
  - "§10.4 DRY"
  - "§10.5 TDD"
  - "§10.7 Clean Code"
delivery_mode: hard-delete per CONSTITUTION.md §3 (no backward-compat shims)
mantra: "Con menos, hacemos más."
---

# Less-Is-More Quality Engine — Spec Brief

## 1. Vision

The repo currently ships **121,380 LOC across 555 test files**, **11 GitHub
workflows with ~57 jobs**, **39 Python hook scripts (12,398 LOC across all
script types)**, **18 quality-cluster files (3,342 LOC of reviewer +
verifier + skill prose)**, and **292 production files at 73,292 LOC under
`src/ai_engineering/`** — of which a handful of validator modules carry
disproportionate complexity that the test surface is forced to mirror.
The framework's promise is "less for more" — yet the quality engine
that enforces that promise, plus the production modules it tests, are
the surfaces most saturated with ceremony, duplication, and
skipped-or-xfail placeholders.

This brief proposes a single coordinated wave that **hard-deletes dead
weight, collapses redundant matrices, and consolidates overlapping
agents** so that the same correctness and security signal is produced by
roughly **half** the files, **half** the LOC, and **a fraction of the CI
wall-clock**. No backward-compat shims — every removal is documented in
the CHANGELOG and lands in one commit per surface so reviewers can
audit blast radius cleanly.

The north star is the canonical mantra (CLAUDE.md §0): a quality engine
should pay rent. A test, a job, a hook, or an agent that does not
demonstrably catch a regression in the last N runs is decoration, not
infrastructure.

## 2. Scope Boundary

**In scope (five surfaces):**

1. `tests/` — pytest suite (unit, integration, e2e, conformance, perf,
   adapters, architecture, mirrors, docs, overrides).
2. `.github/workflows/` — 11 workflow files and their job/matrix
   topology.
3. `.ai-engineering/scripts/hooks/` (canonical) and `.claude/hooks/`
   (read-only symlink) — the 39 Python hooks plus shell/PowerShell/
   TypeScript variants, the `_lib/` shared modules, and the sha256
   manifest at `.ai-engineering/state/hooks-manifest.json`.
4. Quality skills + specialist agents — `/ai-verify`, `/ai-review`,
   `/ai-security`, `/ai-advise` and the 11 reviewer-* + 4 verifier-* +
   review-context + review-validator agents.
5. `src/ai_engineering/` production code — **only the modules whose
   complexity is the root cause of complex tests**. The test surface
   mirrors the production surface (top-LOC production files map 1:1
   to top-LOC test files — see §3.7). A 2,552-LOC test file is a
   symptom of a 1,221-LOC validator module. Refactoring the module
   to extract a shared helper or split categories unblocks deletion
   of the test cluster around it. Production changes land **only when
   they enable a measurable test reduction** — never as standalone
   cleanup.

**Out of scope (deferred to other specs):**

- The `/ai-build`, `/ai-plan`, `/ai-brainstorm` chain (canonical
  workflow per CLAUDE.md §11) — touched only where a quality skill
  contract changes.
- Production code refactors that do not unlock test simplification
  (those belong to a future `/ai-simplify-sweep` or dedicated
  refactor spec).
- Engram, MCP servers, board integration (separate specs).
- Documentation portal regeneration (covered by the parallel
  `prune-contexts-docs-research-evals` brief).

**Anti-goals:**

- No "soft delete" via `pytest.mark.skip` or `if False:` — if a test
  cannot pay rent, it is removed from the tree.
- No new abstraction layers introduced to "manage" the surface — KISS
  and YAGNI bind harder than DRY here.
- No premature property-based test rewrites — PBT is a candidate
  pattern (see §12 [4]) but is decided per cluster, not blanket.

## 3. Diagnostic Snapshot

The current quality engine carries five concrete pathologies, each
backed by file:line evidence.

### 3.1 Dead tests held in the tree as "archaeology"

`tests/unit/test_verify_service.py:610` declares
`@pytest.mark.skip(reason="spec-133 simplified verify_cmd...kept as
skip for archaeology")` over the entire `TestVerifyCmdJsonFlag` class.
The skip reason itself names git history as the correct archaeology
location. The class is collected on every test run and contributes zero
signal.

Two additional hard skips with no tracking reference:
`tests/integration/test_updater.py:150,176` (aspirational behavior
"tracked separately"). One more:
`tests/integration/test_hooks_git.py:121` ("needs redesign… tracked
separately"). The "tracked separately" pattern is the dead-code smell.

### 3.2 xfail stubs that call `pytest.fail()` immediately

`tests/perf/test_hot_path_budgets.py:196,206,216,226` each contain a
test body of exactly one line: `pytest.fail("…not wired yet")`. They
are marked `strict=False`, so they permanently XFAIL without ever
turning green. The deterministic harness they depend on is not in the
tree. Stub placeholders belong in a backlog, not in collected pytest.

### 3.3 CI matrix expansions with no divergent signal

`.github/workflows/ci-check.yml` runs unit tests on
`python-version: ["3.11", "3.12", "3.13"]` across three OS targets — 9
matrix cells. Coverage upload is gated to `ubuntu-latest` and
`python-version == '3.12'` only, meaning **8 of 9 cells produce no
coverage signal**. For a pure-Python framework with no C extensions
and no version-conditional code, the 3.11 and 3.13 legs exercise the
same source against the same stdlib.

`setup-uv` and `uv sync` together appear **27 times** inside
`.github/workflows/ci-check.yml` alone. No reusable workflow or
composite action extracts the pattern (cf. §12 [7] on GitHub's own
guidance).

### 3.4 Hook double-registration with a mislabeled event

`.claude/settings.json:101-110` registers
`.ai-engineering/scripts/hooks/instinct-observe.py` on `PreToolUse`,
and `.claude/settings.json:113-121` registers the same script on
`PostToolUse`. The script's `run_hook_safe` call hard-codes
`hook_kind="post-tool-use"` at
`.ai-engineering/scripts/hooks/instinct-observe.py:41`. Every
PreToolUse firing is mislabeled as a post-tool-use observation, and
two firings per tool call double the hot-path cost on the most
frequent path.

### 3.5 Functional overlap in the quality cluster

The repo currently dispatches **11 reviewer-\*** agents (2,354 LOC) and
**4 verifier-\*** agents (467 LOC) plus 4 quality skills (521 LOC).
- `reviewer-correctness` (330 LOC) and `reviewer-architecture` (232
  LOC) both audit duplicated logic, shared-helper reuse, and design
  appropriateness — the DRY boundary between them is blurred.
- `reviewer-backend` (139 LOC) is categorically mismatched: this repo
  is a Python CLI with no separate backend tier.
- `reviewer-security` (168 LOC) and the standalone `ai-security` skill
  (164 LOC) both assess vulnerability classes on changed code without
  a defined firing contract.

The Anthropic multi-agent research blueprint (§12 [18]) caps roster
size empirically and warns against "spawning 50 sub-agents for simple
queries" — this repo's quality roster is currently sized by sediment,
not by eval signal.

### 3.6 Production-test LOC symmetry — the test bloat has a production root cause

Production surface: **292 Python files under `src/ai_engineering/`, 73,292
LOC**. The largest production files map almost exactly onto the
largest test files:

| Production file (LOC) | Test cluster around it (LOC) |
|-----------------------|------------------------------|
| `src/ai_engineering/policy/orchestrator.py` (1,554) | `tests/unit/test_orchestrator_wave1.py` (1,039) + `_wave2.py` + `_race_safety.py` |
| `src/ai_engineering/cli_commands/core.py` (1,474) | `tests/unit/test_setup_cli.py` (868) and siblings |
| `src/ai_engineering/installer/user_scope_install.py` (1,343) | `tests/unit/test_installer.py` (1,053) |
| `src/ai_engineering/updater/service.py` (1,321) | `tests/unit/test_updater.py` (201) + `tests/integration/test_updater.py` |
| `src/ai_engineering/validator/categories/manifest_coherence.py` (1,221) | `tests/unit/test_validator.py` (2,552, 127 test functions) |
| `src/ai_engineering/validator/categories/mirror_sync.py` (1,108) | `tests/unit/test_sync_mirrors.py` (882) |

`test_validator.py` is the largest test file in the repo (2,552 LOC,
127 test functions) — and the module under test
(`validator/categories/manifest_coherence.py`) is itself the largest
validator category at 1,221 LOC. Splitting `manifest_coherence` into
focused submodules (one per coherence dimension) lets the test file
split along the same seam — likely turning 2,552 LOC into ~600 LOC
across 4 files.

Three validator-category stubs are nearly empty:
`src/ai_engineering/validator/categories/skill_frontmatter.py` (5
LOC), `cross_references.py` (5 LOC), `counter_accuracy.py` (5 LOC).
These are placeholder modules likely tied to skipped or aspirational
tests — they should either be deleted or fleshed out, but never left
as 5-line stubs.

The hot-path injection guard
(`src/ai_engineering/templates/.ai-engineering/scripts/hooks/prompt-injection-guard.py`,
987 LOC) lives in `src/` as the canonical source — the copy under
`.ai-engineering/scripts/hooks/` is a rendered template. Any
hot-path simplification (§9 D-Q2) has its source-of-truth here.

### 3.7 Snapshot tests that re-test the framework, not the framework's logic

`tests/integration/cli/test_help_snapshots.py` parametrizes
`test_help_snapshot_matches` over `PUBLIC_VERBS` and asserts golden
output equality. The system under test is the Click/Typer renderer
which the repo does not own. Any benign wording change forces
`AIENG_UPDATE_HELP_SNAPSHOTS=1` regeneration — the test catches no
logic regression, only intentional wording edits.

Parallel duplication: `tests/conformance/test_md_mirror.py` (21 tests)
and `tests/integration/sync/test_canonical_mirror_parity.py` (9 tests)
both hash and compare the same four mirror files for sha256 equality.
One of the two is redundant.

## 4. Architecture

The proposed engine collapses the four surfaces to a smaller,
single-source-of-truth topology.

### 4.1 Tests

```
tests/
  unit/              # logic-level, fixture-light, no subprocess
  integration/       # cross-module, real disk, no network
  e2e/               # full CLI invocations, ai-eng entrypoint
  conformance/       # invariants (mirror parity, manifest sha256)
  perf/              # hot-path budget tests (1s/5s), enforced in CI
```

Eliminated subdirs after consolidation: `adapters/`, `architecture/`,
`overrides/`, `docs/`, `mirrors/` — their contents fold into the five
canonical buckets based on test character, not source-module identity.

### 4.2 GitHub Workflows

```
.github/workflows/
  pr-gate.yml        # one reusable workflow for all PR signal
  release.yml        # PyPI publish + GitHub Release
  maintenance.yml    # weekly scheduled jobs (label-sync, sbom)
  composite/         # reusable composite actions
    setup-env/       # checkout + setup-python + uv sync (single SoT)
    run-gates/       # lint + type + security + tests
```

Reusable workflow + two composite actions replaces 27 inline
`setup-uv` blocks. Job count drops from ~57 to ~12.

### 4.3 Hooks

A single canonical event-to-hook map with no duplicate registration.
`instinct-observe` either fires once with a runtime `hook_kind` derived
from the actual event, or is unregistered on the path it does not
intend to observe. The 39 Python scripts are audited against the
sha256 manifest; any unreferenced script (e.g.
`.ai-engineering/scripts/hooks/strategic-compact.py`, not present in
`.claude/settings.json`) is deleted.

### 4.4 Quality cluster

Reviewer roster collapses from **11 → 6**:
- `reviewer-correctness` (absorbs architecture's DRY/reuse checks)
- `reviewer-security` (absorbs `ai-security` skill's standalone runs)
- `reviewer-testing`
- `reviewer-performance`
- `reviewer-frontend` (kept; conditionally dispatched)
- `reviewer-compatibility`

Removed: `reviewer-architecture`, `reviewer-maintainability`,
`reviewer-backend`. Their highest-signal heuristics merge into
`reviewer-correctness` or move to `/ai-advise` (advisory, non-blocking).

Verifier cluster: 4 → 3. `verifier-deterministic` keeps its tool-driven
verdict role; `verifier-governance` and `verifier-feature` merge into a
single `verifier-acceptance` that judges acceptance criteria coverage.
`verifier-architecture` becomes part of `ai-advise` instead of a
post-build verdict.

### 4.5 Production code (test-driven refactor only)

The production surface is touched **only where it is the root cause
of a complex test file**. The shape of the refactor follows the
test-file split, not the other way around:

```
src/ai_engineering/validator/categories/
  manifest_coherence/        # split from 1,221-LOC monolith
    __init__.py              # public API; re-exports the split parts
    skill_inventory.py       # one coherence dimension
    agent_inventory.py       # one coherence dimension
    surface_axioms.py        # one coherence dimension
    counter_accuracy.py      # absorbed from the 5-LOC stub
  mirror_sync/               # split from 1,108-LOC monolith
    __init__.py
    md_mirror.py             # one mirror class
    json_mirror.py           # one mirror class
    settings_mirror.py       # one mirror class
```

The 5-LOC validator-category stubs (`skill_frontmatter.py`,
`cross_references.py`, `counter_accuracy.py`) either absorb into the
new split modules or get deleted outright. **The acceptance contract
is one-way: a production refactor is in scope only if it lets us
delete or simplify at least one test file in the same commit.** No
test-deletion → no production change.

Out of the refactor's path: orchestrator, installer, updater, and
CLI core. Their tests are large but largely justified by the
integration surface they cover; tackling them belongs to a future
spec, not this one.

## 5. Evidence Catalog

| Claim | File:line | Surface |
|-------|-----------|---------|
| 555 test files, 121,380 LOC | `tests/` (find + wc) | tests |
| Dead `TestVerifyCmdJsonFlag` class | tests/unit/test_verify_service.py:610 | tests |
| Aspirational test, no ticket | tests/integration/test_updater.py:150,176 | tests |
| Skipped because "tracked separately" | tests/integration/test_hooks_git.py:121 | tests |
| xfail stub, body = `pytest.fail()` | tests/perf/test_hot_path_budgets.py:196,206,216,226 | tests |
| Help-snapshot ceremony | tests/integration/cli/test_help_snapshots.py (full file) | tests |
| Duplicate mirror-parity invariant | tests/conformance/test_md_mirror.py + tests/integration/sync/test_canonical_mirror_parity.py | tests |
| Legacy smoke job kept "intact" | .github/workflows/install-smoke.yml:4,23 | workflows |
| os_release re-probe assertion permanently skipped | .github/workflows/install-smoke.yml:379,407 | workflows |
| 9-cell python+OS matrix, coverage on 1 cell only | .github/workflows/ci-check.yml:200 | workflows |
| setup-uv / uv sync repeated 27 times in one workflow | .github/workflows/ci-check.yml (full file) | workflows |
| Double-registered hook | .claude/settings.json:101-121 | hooks |
| Hard-coded `hook_kind="post-tool-use"` | .ai-engineering/scripts/hooks/instinct-observe.py:41 | hooks |
| 987-LOC injection guard on hottest tool path | .ai-engineering/scripts/hooks/prompt-injection-guard.py (full file) + .claude/settings.json:86 | hooks |
| Reviewer roster, 11 specialists, 2,354 LOC | .claude/agents/reviewer-*.md | quality |
| `reviewer-backend` categorically mismatched | .claude/agents/reviewer-backend.md (full file) | quality |
| `reviewer-security` vs `ai-security` skill, undefined firing contract | .claude/agents/reviewer-security.md + .claude/skills/ai-security/SKILL.md | quality |
| 292 production files, 73,292 LOC | `src/ai_engineering/` (find + wc) | production |
| Largest validator category, 1,221 LOC monolith | src/ai_engineering/validator/categories/manifest_coherence.py | production |
| Second-largest validator category | src/ai_engineering/validator/categories/mirror_sync.py (1,108) | production |
| Empty validator-category stubs | src/ai_engineering/validator/categories/skill_frontmatter.py, cross_references.py, counter_accuracy.py (5 LOC each) | production |
| `test_validator.py` symmetry — 2,552 LOC tests one 1,221-LOC module | tests/unit/test_validator.py + src/ai_engineering/validator/categories/manifest_coherence.py | production ↔ tests |
| Hot-path injection guard source-of-truth | src/ai_engineering/templates/.ai-engineering/scripts/hooks/prompt-injection-guard.py (987 LOC) | production (template) |

## 6. Roadmap

Four waves; each lands as a discrete spec under `/ai-brainstorm`
review. Waves are independent except where explicitly noted — operators
can stop after Wave 1 and still bank the savings. Wave 2.5 (production
refactor) follows Wave 2 because it shares the test-rewrite mechanic.

### Wave 1 — Hard-delete dead weight (1 PR)

- Remove `TestVerifyCmdJsonFlag` class
  (`tests/unit/test_verify_service.py:610-end`).
- Remove the four `pytest.fail()`-bodied xfail stubs
  (`tests/perf/test_hot_path_budgets.py:191-228`).
- Remove the three "tracked separately" hard skips
  (`tests/integration/test_updater.py:150,176`,
  `tests/integration/test_hooks_git.py:121`).
- Remove the legacy `smoke-test` job in
  `.github/workflows/install-smoke.yml` (`spec101-install-smoke`
  covers the same surface).
- Remove the os_release re-probe placeholder block in both branches
  of `install-smoke.yml`.
- Remove `strategic-compact.py` if grep confirms zero references.
- Estimated LOC reduction: ~600. Estimated CI wall-clock saving:
  ~15-25% on PR builds (smoke job + dead matrix cells).

### Wave 2 — Collapse the test matrix and CI duplication (1 PR)

- Reduce `ci-check.yml` python matrix from `[3.11, 3.12, 3.13]` to
  `[3.12]` (the coverage-gated leg). Keep 3-OS matrix.
- Extract `setup-env` and `run-gates` composite actions
  (`.github/actions/setup-env/`, `.github/actions/run-gates/`) to
  replace 27 inline `setup-uv` blocks across the workflow set.
- Fold the four `verifier-*` callers into a single reusable workflow
  step.
- Delete one of the two mirror-parity tests (keep
  `tests/conformance/test_md_mirror.py`; remove
  `tests/integration/sync/test_canonical_mirror_parity.py`).
- Delete `tests/integration/cli/test_help_snapshots.py` (golden-output
  ceremony on a third-party renderer).
- Estimated LOC reduction: ~1,500 (workflows + tests). Wall-clock
  saving: ~30-40% on PR builds.

### Wave 2.5 — Test-driven production refactor (1 PR, gated by test deletion)

- Split `src/ai_engineering/validator/categories/manifest_coherence.py`
  (1,221 LOC) into a package with one module per coherence dimension
  (skill inventory, agent inventory, surface axioms, counter
  accuracy). Public API preserved via `__init__.py` re-exports.
- Split `src/ai_engineering/validator/categories/mirror_sync.py`
  (1,108 LOC) along the per-mirror seam (md / json / settings).
- Delete the three 5-LOC validator-category stubs (`skill_frontmatter`,
  `cross_references`, `counter_accuracy`) or absorb them into the
  split packages.
- Split `tests/unit/test_validator.py` (2,552 LOC, 127 functions)
  along the same seam — one test file per validator dimension.
  Target post-split: ≤ 600 LOC each across 4 files, ~1,400 LOC saved
  via removed duplication and shared-fixture extraction.
- **Hard gate:** this wave merges only if test-LOC reduction is
  measurable in the same PR. If the production split lands without
  a matching test deletion, revert and re-plan.
- Estimated LOC reduction: ~1,400 in tests, net +200 in production
  (split overhead absorbed by deleting stubs and dedup).

### Wave 3 — Collapse the quality roster (2 PRs, gated by eval)

- Define a pass@k eval per reviewer specialty against the recent PR
  corpus (Anthropic blueprint, §12 [18]); use `/ai-reliability-eval`
  to anchor the baseline.
- Merge `reviewer-architecture`'s reuse/DRY heuristics into
  `reviewer-correctness`; delete the standalone agent.
- Merge `reviewer-maintainability` into `reviewer-correctness`.
- Delete `reviewer-backend` (categorically mismatched).
- Merge `verifier-governance` + `verifier-feature` into
  `verifier-acceptance`.
- Move `verifier-architecture`'s heuristics to `/ai-advise` (advisory,
  non-blocking).
- Estimated LOC reduction: ~1,200 (agent prose).

Wave 3 only ships if the pass@k eval shows the smaller roster matches
or beats the current roster on the corpus — no roster shrink without
empirical evidence.

## 7. Definition of Done

The wave is done when every line item below is true and audited.

1. **Tests:** total test-file count ≤ 350 (current 555); total LOC ≤
   80,000 (current 121,380); zero hard `@pytest.mark.skip` without a
   ticket reference + ticket link in the reason; zero `pytest.fail()`-
   bodied tests.
2. **Workflows:** total job count ≤ 25 (current ~57); zero in-repo
   duplicate `uses: astral-sh/setup-uv` invocations outside the
   composite action; PR wall-clock p50 ≤ 6 minutes (current baseline
   to be captured in spec phase).
3. **Hooks:** every script in `.ai-engineering/scripts/hooks/` is
   referenced by either `.claude/settings.json` or by another hook;
   the sha256 manifest matches disk exactly (currently 72 in manifest
   vs 74 on disk — gap of 2 reconciled or deleted); zero hooks
   double-registered on overlapping events.
4. **Quality cluster:** reviewer agent count ≤ 7 (current 11); each
   remaining agent has an explicit firing contract and a pass@k eval
   row in `evals/` or the equivalent `.ai-engineering/runtime/`
   harness.
5. **Production code:** zero validator-category modules >1,000 LOC
   (current: two at 1,221 + 1,108); zero 5-LOC placeholder modules;
   `src/ai_engineering/validator/categories/` net LOC unchanged or
   reduced after the test-driven refactor.
6. **Production ↔ test invariant:** every production change in Wave
   2.5 deletes or splits at least one test file. The PR diff makes
   this 1:1 mapping explicit (production change → test reduction in
   the same commit).
7. **No regressions:** the `/ai-verify --release` pre-release gate
   passes GO; `/ai-reliability-eval` shows no decrease in pass@k for
   the surviving agents; validator categories produce byte-identical
   findings on the existing fixture corpus before and after the
   split.
8. **Audit trail:** CHANGELOG documents every hard-rename or hard-
   delete; one `framework_event kind=quality_engine_collapse` per
   wave.

## 8. Quality Stamps

Principles applied per CLAUDE.md §10:

- **§10.1 KISS** — fewest moving parts. Single reusable workflow,
  single canonical hook registration map, single reviewer per
  domain.
- **§10.2 YAGNI** — xfail stubs and "tracked separately" placeholders
  are by definition speculative; their removal is YAGNI made
  concrete.
- **§10.4 DRY** — 27 repeated `setup-uv` invocations, two
  mirror-parity test files, two overlapping security surfaces all
  collapse to one source.
- **§10.5 TDD** — survivors stay; the pass@k eval becomes the
  acceptance test for Wave 3 roster shrink.
- **§10.7 Clean Code** — every dead-tree comment ("kept for
  archaeology") removed; the test tree expresses present intent only.

Contracts honoured: CONSTITUTION.md §3 (no backward-compat shims);
CLAUDE.md §11 (canonical chain unchanged); CLAUDE.md "Hot-Path
Discipline" (every hook decision improves the budget).

## 9. Open Decisions

The spec phase must resolve:

1. **D-Q1: Which conftest layer owns the git-repo fixture?**
   `tests/conftest.py:147-205` and `tests/integration/conftest.py` both
   build similar fixtures. The spec must pick one home.
2. **D-Q2: Hot-path injection guard.** `prompt-injection-guard.py` is
   987 LOC on the hottest tool path with six `_lib` imports. Options:
   (a) keep as-is and accept the cost, (b) split into a tiny stub +
   async heavy path, (c) move pattern set behind a precompiled
   AST/regex bundle. The spec must benchmark before deciding.
3. **D-Q3: Python matrix policy.** Collapse to 3.12 only, or keep 3.13
   as the "future" leg with 3.11 dropped? Industry pattern (§12 [9])
   gives no mandate.
4. **D-Q4: Reviewer roster eval source.** `evals/` is itself a
   deletion candidate in the parallel surface-cleanup brief. The spec
   must pick a stable harness location (likely
   `.ai-engineering/runtime/quality-evals/`).
5. **D-Q5: `/ai-advise` capacity.** Wave 3 hands `/ai-advise` more
   surface (architecture + verifier-architecture heuristics). Does
   `/ai-advise` need a sub-spec to absorb that load without becoming
   the new bloat sink?
6. **D-Q6: Help-snapshot replacement.** Removing the snapshot test
   leaves no automated check on CLI output. The spec must decide
   whether the loss is acceptable, or whether a much smaller
   "command-list exists" assertion replaces it.
7. **D-Q7: Production ↔ test causation threshold.** Wave 2.5 fires
   only when a production refactor demonstrably enables a test
   deletion. The spec must pick the metric: (a) LOC ratio (≥ 2x
   test-LOC removed per production-LOC added), (b) file-count ratio
   (≥ 1 test file deleted per production file split), or (c) function-
   count ratio (each split absorbs ≥ N test functions). The brief
   recommends (a) with a 2x floor — if a production split saves
   fewer than twice its overhead in tests, it does not ship.
8. **D-Q8: Validator-stub disposition.** The three 5-LOC validator
   stubs (`skill_frontmatter`, `cross_references`, `counter_accuracy`)
   each represent a coherence dimension that may or may not still
   be needed. The spec must decide per-stub: absorb into a split
   sibling, delete outright, or grow into a real module. Each option
   has a different test-impact.

## 10. Migration

Per CONSTITUTION.md §3, all removals are hard. The migration plan:

- **No shims.** Deleted tests, jobs, hooks, and agents are not stubbed.
- **CHANGELOG entry per wave** in `docs/CHANGELOG.md`, listing every
  removed file/job/agent and the one-line rationale.
- **Single PR per wave.** Reviewers see the entire blast radius in one
  diff; bisect remains easy.
- **No "deprecated" warnings phase.** Internal-only surface; the
  framework operator is the only caller.
- **Branch hygiene:** each wave lands on `spec-NNN/less-is-more-wave-K`
  and merges with the standard `/ai-pr` gate.
- **Rollback strategy:** `git revert <wave-merge-sha>` restores the
  prior surface byte-for-byte; tested in the spec phase against a
  throwaway branch before the wave merges.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Deleted test masks a real regression | Medium | High | Wave 1 only deletes skipped/xfail-stub tests that produce no signal today. Wave 2 deletions backed by duplicate-detection script run during spec phase. |
| Roster shrink degrades review quality | Medium | High | Wave 3 gated by pass@k eval against PR corpus; no merge without empirical evidence. |
| CI matrix collapse hides a real py-version bug | Low | Medium | Keep an opt-in `nightly-matrix.yml` on `schedule:` for full python+OS sweep; failure pages but does not block PRs. |
| Hook double-registration fix breaks observability | Low | Medium | The `hook_kind` mislabel today already breaks observability; the fix restores ground truth. Spec phase verifies the audit-event consumer handles both labels. |
| `setup-uv` composite action breaks a workflow edge case | Medium | Low | Composite action is byte-equivalent to current inline blocks; tested on a throwaway workflow first. |
| Snapshot test removal lets a benign-looking wording change ship a real bug | Low | Low | The current snapshot test catches wording, not logic. Logic-level CLI assertions live in `tests/unit/test_*_cli.py` and remain. |
| CONSTITUTION.md §3 enforcement makes rollback the only recovery | Low | Medium | Each wave is a single commit; rollback is `git revert <sha>`. Tested before merge. |
| Validator split breaks public API consumed by external callers | Low | High | Public API preserved via `__init__.py` re-exports — the split is internal-only. Spec phase greps for every importer of `manifest_coherence` / `mirror_sync` and asserts byte-identical exports before merge. |
| Wave 2.5 ships a production refactor without the matching test deletion | Medium | Medium | D-Q7 metric is enforced at PR review — a 2x LOC ratio gate. If the wave drifts into "production-only cleanup," the PR is rejected and re-planned. |
| Production refactor masquerades as "less for more" while net-adding LOC | Medium | Medium | DoD §5 caps validator/categories at net LOC unchanged or reduced. Any net-positive LOC change must be justified by an equal-or-greater test reduction. |

## 12. References

External evidence anchoring the deletion patterns (full citations from
parallel `/ai-research` dispatch):

- [1] Kent Beck, *Test Desiderata* (2019) — twelve properties of good
  tests; explicitly licenses deletion when no property is honoured.
- [2] Kent Beck quoted on HN, "I get paid for code that works, not for
  tests" (orig. 2008).
- [3] Martin Fowler, *On the Diverse and Fantastical Shapes of
  Testing* (martinfowler.com, June 2021) — shape choice downstream of
  test quality.
- [4] Hillel Wayne, *Finding Property Tests* and *Beyond Unit Tests*
  (PyCon 2018) — PBT collapses test count for equal-or-better
  coverage.
- [5] pytest docs — Fixtures reference (conftest.py per-scope
  ownership).
- [6] Forsgren / DORA, *Accelerate* — long-running test suites are the
  primary deployment-frequency drag.
- [7] GitHub Docs — Reusing workflow configurations (reusable
  workflows + composite actions).
- [8] Thoughtworks Technology Radar — Build pipelines + Azure Pipeline
  templates anti-patterns.
- [9] GitHub Docs — Building and testing Python (matrix as DRY
  mechanism, not coverage mandate).
- [10] DevSecOps School Pre-commit Hook Guide (2026) — sub-2-second
  SLO.
- [11] pkgpulse, *Husky vs Lefthook vs lint-staged* (2026) —
  parallel-hooks and hot-path discipline.
- [12] thoughtspile, *How we made our pre-commit check 7x faster*
  (2021) — concrete reduction case study.
- [13] Andrej Karpathy — *karpathy-guidelines* (skills.sh, 2025): "If
  you write 200 lines and it could be 50, rewrite it."
- [14] Gergely Orosz, *Building Claude Code with Boris Cherny*
  (Pragmatic Engineer, 2026) — Claude Code "surprisingly vanilla";
  verification loops are the single most important practice.
- [15] John Ousterhout, *A Philosophy of Software Design*, Ch. 4 —
  deep modules vs shallow modules.
- [16] Hyrum's Law (hyrumslaw.com) — deletion-safety requires evidence
  of zero observable-behaviour dependence, not assumption.
- [17] TheNewStack / InfoQ, *Anthropic launches multi-agent code
  review* (2026) — substantive-review-comment rate 16% → 54%.
- [18] Anthropic Engineering, *How we built our multi-agent research
  system* (June 2025) — lead-agent + sub-agent architecture; "spawning
  50 sub-agents" anti-pattern.
- [19] Anthropic Docs — Create custom subagents.

## 13. Glossary

- **Quality engine** — the union of tests, CI workflows, hooks, and
  quality skills/agents that enforce correctness, security, and
  governance contracts for the framework.
- **Pay rent** (Beck-derived) — a test, job, hook, or agent pays rent
  when it has caught at least one real regression or blocked at least
  one real incident in the recent window.
- **Hard delete** (CONSTITUTION.md §3) — removal of a file/symbol
  with no shim, no deprecation warning, no fallback path; CHANGELOG
  is the only artifact.
- **Specialist roster** (project-local term) — the set of
  reviewer-\* and verifier-\* agents dispatched by `/ai-review` and
  `/ai-verify`. Distinct from Anthropic's official term "subagent"
  (§12 [19]).
- **Matrix collapse** — reducing a CI matrix from N×M cells to the
  smallest set that empirically differentiates failures.
- **Ceremonial test** — a test that exercises code the framework does
  not own (e.g. third-party renderer output), or asserts an invariant
  already enforced elsewhere.
- **Test-driven refactor** (Wave 2.5 contract) — a production code
  change that ships only when it enables a measurable test deletion
  in the same commit. The test reduction is the acceptance gate, not
  a side effect.
- **Validator-category seam** — the per-coherence-dimension boundary
  inside `src/ai_engineering/validator/categories/` that lets a
  1,221-LOC monolith split into 4-6 focused modules with a 1:1 map
  onto the test functions that exercise them.

## 14. Acceptance

The brief is ready for `/ai-brainstorm` handoff when:

- [x] 14 sections present.
- [x] ≥ 5 file:line citations (this brief carries 17+).
- [x] No machine-absolute paths (only `$HOME/...` or repo-relative).
- [x] No emoji.
- [x] YAML frontmatter declares `title`, `status: draft`, `audience`,
  `branch`, `length_estimate`, `authoring_style`,
  `principles_required`, `delivery_mode`, `mantra`.
- [x] CONSTITUTION.md §3 hard-delete posture declared up front.
- [x] Open Decisions enumerates the exact resolutions the spec phase
  must produce.
- [x] Roadmap is independently shippable per wave.
- [x] Risks table includes mitigations, not just hand-waves.
- [x] References cite real sources (URLs in the parallel research
  output; full URLs land in spec.md after `/ai-brainstorm` review).

Next step: `/ai-brainstorm --consume less-is-more-quality-engine-brief.md`
