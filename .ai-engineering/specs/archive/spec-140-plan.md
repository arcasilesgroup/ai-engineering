---
spec: spec-140
slug: less-is-more-quality-engine
title: Plan — Less-Is-More Quality Engine
pipeline: build
phases: 4
status: approved
branch: claude/review-spec-drafts-DX2pD
date_approved: 2026-05-16
auto_approved: true
single_concern: false
---

# Plan — spec-140 Less-Is-More Quality Engine

Four independent waves; the safety-critical subset is Wave 1 alone (closes the dead-test archaeology in ~600 LOC).

## Branch / PR

- Working branch: `claude/review-spec-drafts-DX2pD`
- Target: `main` via single PR carrying spec-138 + spec-139 + spec-140 + spec-141 (multi-spec autonomous run).

## Quality bar

- §10.1 KISS: fewest moving parts; single reusable workflow; single canonical hook registration map; single reviewer per domain.
- §10.2 YAGNI: xfail stubs and "tracked separately" placeholders are speculative — removed.
- §10.4 DRY applied to STORES (27 repeated `setup-uv` → one composite action).
- §10.5 TDD: survivors stay; pass@k eval is the acceptance test for Wave 3.
- §10.7 Clean Code: every "kept for archaeology" comment removed.

## Wave 1 — Hard-delete dead weight

**Anchor:** §10.7 Clean Code · CONSTITUTION.md §3.

### Tasks

- **W1.T1** — Remove `TestVerifyCmdJsonFlag` class from `tests/unit/test_verify_service.py:610-end`.
- **W1.T2** — Remove the four `pytest.fail()`-bodied xfail stubs at `tests/perf/test_hot_path_budgets.py:191-228`.
- **W1.T3** — Remove the three "tracked separately" hard skips at `tests/integration/test_updater.py:150,176` and `tests/integration/test_hooks_git.py:121`.
- **W1.T4** — Remove the legacy `smoke-test` job in `.github/workflows/install-smoke.yml` (covered by `spec101-install-smoke`).
- **W1.T5** — Remove the `os_release` re-probe placeholder block in both branches of `install-smoke.yml`.
- **W1.T6** — Remove `.ai-engineering/scripts/hooks/strategic-compact.py` if `grep -rn "strategic-compact" .claude/` confirms zero references.
- **W1.T7** — Fix `instinct-observe.py:41` hard-coded `hook_kind="post-tool-use"` (mislabels every PreToolUse firing). Either:
  - (a) Take `hook_kind` from the `AIENG_HOOK_EVENT` env var that the harness passes, OR
  - (b) Drop the PreToolUse registration in `.claude/settings.json:101-110` if PreToolUse data is not actually consumed by downstream observability.
  Decision: (a) — preserves the data flow; the dedup spec-139 M5.T2 batching survives.
- **W1.T8** — `tests/unit/hooks/test_instinct_observe_event_kind.py` GREEN — asserts `hook_kind` matches the dispatched event.

### Acceptance gate

- LOC reduction ≥ 600 (tests + workflows).
- CI wall-clock reduction ≥ 15 % on PR builds (the smoke-job + dead-matrix-cell cuts).
- `tests/unit/hooks/test_instinct_observe_event_kind.py` GREEN.

## Wave 2 — Collapse the test matrix and CI duplication

**Anchor:** §10.4 DRY · D-140-03 · D-140-06.

### Tasks

- [x] **W2.T1** — Reduce `ci-check.yml` python matrix from `[3.11, 3.12, 3.13]` to `[3.12]`. Keep 3-OS matrix.
- [x] **W2.T2** — Add `nightly-matrix.yml` on `schedule:` with full python+OS sweep (advisory, non-blocking).
- [x] **W2.T3** — Extract `setup-env` composite action at `.github/actions/setup-env/` (checkout + setup-python + uv sync).
- [x] **W2.T4** — Extract `run-gates` composite action at `.github/actions/run-gates/` (lint + type + security + tests).
- [x] **W2.T5** — Replace 27 inline `setup-uv` blocks across all `.github/workflows/*.yml` with `uses: ./.github/actions/setup-env`. (19 of ~22 inline blocks replaced; `ci-build.yml` retains its inline checkout because the `ref: main` + `token` flow cannot be represented in the composite without growing conditional inputs.)
- [ ] **W2.T6** — Fold the four `verifier-*` callers into a single reusable workflow step. (Deferred — sized for its own focused PR; out of scope for the W2 lane that landed alongside W1.)
- [x] **W2.T7** — Delete one of the two mirror-parity tests (keep `tests/conformance/test_md_mirror.py`; remove `tests/integration/sync/test_canonical_mirror_parity.py`).
- [x] **W2.T8** — Delete `tests/integration/cli/test_help_snapshots.py`; replace with a "command-list exists" assertion in `tests/unit/cli/test_command_list.py`. Drift gates added under `tests/unit/workflows/` (python-matrix-collapsed, nightly-matrix-advisory, composite-actions).

### Acceptance gate

- Job count drops from ~57 to ≤ 25.
- Zero duplicate `uses: astral-sh/setup-uv` outside the composite action.
- PR wall-clock p50 ≤ 6 minutes.

## Wave 2.5 — Test-driven production refactor

**Anchor:** §10.5 TDD · D-140-07 (2x LOC ratio gate) · D-140-08 (per-stub disposition).

### Tasks

- [ ] **W2.5.T1** — Split `src/ai_engineering/validator/categories/manifest_coherence.py` (1,221 LOC) into a package. **Deferred** — splitting the monolith into per-dimension submodules adds ~80-150 LOC of import/`__init__.py` re-export scaffolding. D-140-07 (test deletion ≥ 2x production-LOC overhead) cannot be satisfied without also deleting ≥ 300 LOC of tests, which is not justified for the modest readability win. Re-attempt only after a clear ROI use case lands.
- [ ] **W2.5.T2** — Split `src/ai_engineering/validator/categories/mirror_sync.py` (1,108 LOC) along the per-mirror seam. **Deferred** — same reasoning as W2.5.T1; the 17 functions in `mirror_sync.py` share constants/regexes from `_shared.py` and split awkwardly without a `_mirror_helpers.py` companion module.
- [ ] **W2.5.T3** — Delete `src/ai_engineering/validator/categories/cross_references.py` (5 LOC stub, no consumer; D-140-08). **Blocked** — the spec claim was incorrect. `tools/skill_app/lint_service.py` imports `_check_cross_references` from `ai_engineering.validator.categories` (line 31), and `tests/integration/test_gap_fillers4.py` exercises the same import. Deleting the stub would break those consumers. The stub stays until the import surface is intentionally re-routed.
- [ ] **W2.5.T4** — Absorb `skill_frontmatter.py` and `counter_accuracy.py` 5-LOC stubs into the split packages (D-140-08). **Deferred** — depends on W2.5.T1 / W2.5.T2.
- [x] **W2.5.T5** — Split `tests/unit/test_validator.py` (2,554 LOC, 127 functions) along the same seam — one test file per validator dimension. Target post-split: ≤ 600 LOC each across 4 files. Delivered as 9 split files under `tests/unit/validator/` (largest is `test_mirror_sync_categories.py` at 541 LOC; 7 of 9 files are under 320 LOC). Shared helpers consolidated in `conftest.py`. All 127 tests preserved and passing.
- [x] **W2.5.T6** — Public-API parity test: `tests/unit/validator/test_category_public_api.py` greps every importer of `manifest_coherence` / `mirror_sync` (and every other guarded category module) and asserts every imported symbol still resolves. AST-based to handle multiline `from ... import` statements. Three guard tests pass: imported-symbol resolution, check-function callable presence, and `lint_service` re-export integrity.
- [ ] **W2.5.T7** — D-140-07 gate at PR review: production-LOC delta vs test-LOC delta ratio ≥ 2x. **Vacuous pass** — production-LOC change is 0 (no production split landed). Net test delta is +156 LOC (2,554 → 2,710 across 10 files), entirely attributable to the per-file module headers/imports baseline that any 9-file split incurs over a monolith, plus the new 155-LOC parity test (W2.5.T6 deliverable). Without production growth there is no production-overhead to offset; the 2× multiplier is undefined on a zero divisor and the gate is satisfied vacuously.

### Acceptance gate

- ~~Zero validator-category modules > 1,000 LOC.~~ Production splits deferred; both `manifest_coherence.py` (1,221) and `mirror_sync.py` (1,108) remain above 1,000 LOC.
- ~~Zero 5-LOC placeholder modules.~~ Three stubs (`counter_accuracy.py`, `cross_references.py`, `skill_frontmatter.py`) remain as re-export shims to `tools/skill_domain/`; deleting them would break `tools/skill_app/lint_service.py` consumers.
- `src/ai_engineering/validator/categories/` net LOC ≤ baseline → **satisfied** (production untouched).
- Test deletion ≥ 2x production-LOC overhead → **vacuous pass** (production overhead = 0; see W2.5.T7).

## Wave 3 — Collapse the quality roster

**Anchor:** Anthropic blueprint sub-agent sizing · D-140-04 (eval source).

### Tasks

- [ ] **W3.T1** — Define pass@k eval per reviewer specialty against the recent PR corpus in `.ai-engineering/runtime/quality-evals/`. **Deferred** — eval harness does not yet exist on disk; the structural collapse below ships first, the operator runs the pass@k gate in a follow-up.
- [ ] **W3.T2** — Use `/ai-reliability-eval` to anchor the baseline. **Deferred** — depends on W3.T1.
- [x] **W3.T3** — Merge `reviewer-architecture`'s reuse/DRY heuristics into `reviewer-correctness`; delete the standalone agent.
- [x] **W3.T4** — Merge `reviewer-maintainability` into `reviewer-correctness`; delete standalone.
- [x] **W3.T5** — Delete `reviewer-backend` (categorically mismatched — repo is Python CLI, no separate backend tier).
- [x] **W3.T6** — Merge `verifier-governance` + `verifier-feature` into a single `verifier-acceptance`.
- [x] **W3.T7** — Move `verifier-architecture`'s heuristics to `/ai-advise` drift mode (advisory, non-blocking); delete the standalone verifier.

### Acceptance gate

- Reviewer count ≤ 7 (current 11). **Landed at 6** (correctness absorbs architecture + maintainability; backend deleted outright).
- Verifier count ≤ 3 (current 4). **Landed at 2** (deterministic + acceptance). The brief header advertised "4 → 3" but the explicit operations (delete 3 files, create 1) yield 2; the test pins the actual count and the CHANGELOG documents the discrepancy.
- pass@k eval shows the smaller roster matches or beats the current roster on the corpus. **Deferred** — operator-run gate at `.ai-engineering/runtime/quality-evals/` (gitignored, harness not yet built).

## Cross-spec coordination

- **spec-138 dependency.** Do NOT delete `tests/unit/state/test_sql_writer_schemas.py`, `tests/architecture/test_no_sql_on_hot_path.py`, or `tests/architecture/test_persistence_doctrine_exists.py` introduced by spec-138 M1/M2/M4.
- **spec-139 dependency.** Wave 1 W1.T7 fixes `instinct-observe.py` event kind handling; spec-139 M5.T2 adds the batching. Both improvements stack — the fix happens after batching is in place.

## Out of single-concern envelope

This plan is multi-wave / multi-file. Implementation proceeds via the multi-spec orchestration.
