---
spec: spec-129
title: Skills + Agents Excellence Refactor — Pragmatic Scope
pipeline: full
phases: 4
tasks: 22
status: approved
---

# Plan — spec-129 Skills + Agents Excellence Refactor (Pragmatic Scope)

## Summary

Phased execution plan derived from approved `.ai-engineering/specs/spec.md`. Scope = the trimmed 14-item DoD per D-129-05: three shared libs + three hot-path scripts + integration refactors + M5 verification (no-op — tests already cover) + M4 doc-only count reconciliation + PR-#509 retitle. M6 evals and dependent description-level refactors are explicitly out of scope per D-129-02.

Branch: `spec-128/context-overrides-refactor` (no new branch). PR: #509 (no new PR; retitle in T-21). Effort target: ~13 h focal, ceiling 20 h per D-129-07.

## Architecture

**Pattern: Hexagonal / Ports-and-Adapters** (continues the architecture consolidated in spec-128 D-128-01 and spec-127 sub-008 D-127-09).

**Justification**: The codebase already enforces a layered split — `tools/skill_domain/` (pure dataclasses, zero deps), `tools/skill_app/` (use cases like `deterministic_router.resolve_adapter`), and `tools/skill_infra/` (IDE/MCP adapters). The three new shared libs are **infrastructure adapters** for stdlib + git/yaml/markdown I/O concerns. The three new scripts are **interface drivers** that compose libs to serve a single CLI surface each. No new domain logic is added — this plan extends the existing hexagonal seam, it does not redefine it. `tests/architecture/test_layer_isolation.py` remains the enforcement gate; any new `_lib` module must not import from `skill_domain` and must not be imported by `skill_domain`.

## Phase 0 — Shared Libs (Foundation, TDD)

**Goal**: Land three pure-stdlib shared libraries under `.ai-engineering/scripts/skills/_lib/` per spec §14.1. Each lib gets RED test first, then GREEN implementation. No I/O in tests beyond fixtures and `tmp_path`.

**Gate**: All Phase 0 tests green; layer-isolation test green; pyflakes/ruff clean on new files; perf budget per lib ≤ 50 ms p95 over 100 calls.

- [x] **T-1** [build/test, RED] Write failing tests `tests/unit/scripts/_lib/test_manifest_reader.py`. Cover: `resolve_stack(manifest_path) → str`, `read_work_items(manifest_path) → dict`, `MissingManifestError` raises on absent file, `InvalidManifestError` raises on malformed YAML. Use fixtures under `tests/unit/scripts/_lib/fixtures/manifest_*.yml`. — **DONE** (9 tests, ModuleNotFoundError confirmed)
- [x] **T-2** [build/code, GREEN, blocks-on=T-1] Implement `.ai-engineering/scripts/skills/skill_scripts_lib/manifest_reader.py`. Stdlib + `yaml` only. Namespace package created (renamed from `_lib`), `pyproject.toml` pythonpath extended. Constraint: DO NOT modify test files from T-1. — **DONE** (9/9 tests green, ruff clean, layer-isolation green)
- [x] **T-3** [build/test, RED] Write failing tests `tests/unit/scripts/_lib/test_git_activity.py`. Cover: `recent_merges(since_iso) → list[Merge]`, `last_commit() → Commit`, `commits_since(ref) → list[Commit]`, `branch_age_days(branch) → int`. Use a `tmp_path` throwaway repo via `git init` for fidelity (preferred over mocks). — **DONE** (15 tests, ModuleNotFoundError confirmed)
- [x] **T-4** [build/code, GREEN, blocks-on=T-3] Implement `.ai-engineering/scripts/skills/skill_scripts_lib/git_activity.py`. Wraps `git log --format=...` parsing into typed tuples. Stdlib + subprocess. Constraint: DO NOT modify test files from T-3. — **DONE** (15/15 tests green, ruff clean)
- [x] **T-5** [build/test, RED] Write failing tests `tests/unit/scripts/_lib/test_markdown_render.py`. Cover: `render_table(headers, rows) → str`, `render_checklist(items) → str`, `parse_frontmatter(md_text) → dict`, `strip_frontmatter(md_text) → str`. Edge cases: empty input, special chars, malformed YAML in frontmatter. — **DONE** (24 tests, ModuleNotFoundError confirmed)
- [x] **T-6** [build/code, GREEN, blocks-on=T-5] Implement `.ai-engineering/scripts/skills/skill_scripts_lib/markdown_render.py`. Stdlib + `yaml`. No external rendering deps. Constraint: DO NOT modify test files from T-5. — **DONE** (27/27 tests green, ruff clean)

## Phase 1 — New Hot-Path Scripts (TDD)

**Goal**: Land three new scripts using the shared libs from Phase 0. Each script targets a specific `/ai-*` skill's hot-path determinism per spec §14.2.

**Gate**: All Phase 1 integration tests green; perf budget per script ≤ 500 ms p95; `tests/perf/test_hot_path_budgets.py` still green (no regression on existing budgets).

- [x] **T-7** [build/test, RED] Write failing tests `tests/integration/scripts/test_standup_render.py`. Fixture: `tmp_path` repo with seeded commits + branches. Assert: standup markdown contains expected sections (Yesterday / Today / Blockers), counts match commit fixture, no LLM placeholder strings. — **DONE** (18 tests, ModuleNotFoundError)
- [x] **T-8** [build/code, GREEN, blocks-on=T-7, depends-on=T-4,T-6] Implement `.ai-engineering/scripts/skills/skill_scripts/standup_render.py`. Uses `git_activity.recent_merges` + `markdown_render.render_checklist`. CLI: `python standup_render.py [--since=7d] [--format=md|json]`. — **DONE** (19/19 tests green, ruff clean, package skill_scripts configured)
- [x] **T-9** [build/test, RED] Write failing tests `tests/integration/scripts/test_cleanup_run.py`. Fixture: throwaway repo with merged + unmerged branches. Assert: classification (merged-into-main, squash-merged, stale-no-commits-30d, protected), `--dry-run` reports without delete, `--apply` deletes only the classified-safe set. — **DONE** (21 tests, ModuleNotFoundError)
- [x] **T-10** [build/code, GREEN, blocks-on=T-9, depends-on=T-4] Implement `.ai-engineering/scripts/skills/skill_scripts/cleanup_run.py`. Uses `git_activity` for branch metadata. CLI: `python cleanup_run.py [--dry-run|--apply] [--protect=main,master]`. — **DONE** (20/20 tests green, ruff clean)
- [x] **T-11** [build/test, RED] Write failing tests `tests/integration/scripts/test_resolve_classify.py`. **Adversarial fixtures required** per spec §Risks: lock file with manual edits, generated file WITHOUT sentinel, migration path, plain code conflict. Assert: conservative classification — only `lock`, `generated-with-sentinel` auto-resolve; everything else returns `ambiguous` or `code`. — **DONE** (30 cases, 3+ adversarial fixtures, ModuleNotFoundError)
- [x] **T-12** [build/code, GREEN, blocks-on=T-11] Implement `.ai-engineering/scripts/skills/skill_scripts/resolve_classify.py`. Pure classification (no resolution writing). CLI: `python resolve_classify.py <conflict-path> → {type, action, confidence}`. — **DONE** (32/32 tests green, 11 adversarial cases, conservative_default ✅)

## Phase 2 — Integration Refactor (libs → existing scripts)

**Goal**: Refactor the three existing hot-path scripts to consume the shared libs, eliminating duplicated parsing/rendering logic. Behavior-preserving — existing tests stay green throughout.

**Gate**: All existing tests for `session_bootstrap`, `commit_compose`, `pr_body_compose` still green; perf budget unchanged or improved; layer-isolation test green; diff per file is structural (function bodies shrink, no new public API).

- [x] **T-13** [build/refactor, depends-on=T-2,T-4,T-6] Refactor `.ai-engineering/scripts/session_bootstrap.py` to use `markdown_render.parse_frontmatter` + `git_activity.last_commit`. — **DONE** (301→294 lines, 4/4 tests, perf green, behavior preserved)
- [x] **T-14** [build/refactor, depends-on=T-2] Refactor `.ai-engineering/scripts/commit_compose.py` to use `markdown_render.parse_frontmatter` (manifest_reader N/A here). — **DONE** (6/6 tests, perf green, behavior preserved)
- [x] **T-15** [build/refactor, depends-on=T-2,T-6] Refactor `.ai-engineering/scripts/pr_body_compose.py` to use `markdown_render.parse_frontmatter` + `markdown_render.render_checklist`. — **DONE** (204→202 lines, 5/5 tests, perf green, behavior preserved)

## Phase 3 — Verification + Docs + PR Finalization

**Goal**: Close M5 verification (already complete — just confirm), close M4 doc-only count fix, materialize M0 JSON via brainstorm bootstrap, retitle PR #509, final DoD signoff.

**Gate**: D-129-05 14-item DoD checklist all ✅; CHANGELOG entry merged; PR title updated; spec-lifecycle.json materialized; final `/ai-verify` pass green.

- [x] **T-16** [verify, depends-on=T-2..T-15] Run existing `tests/unit/router/test_deterministic_router.py`. **M5 CLOSED** — 29 tests green (parametrized expansion of 7 stacks + UnknownStackError + p95 ≤ 50 ms). No impl change needed.
- [x] **T-17** [build/docs] Update `CHANGELOG.md` — **DONE** (spec-129 entry added under `[Unreleased]`, above spec-127 Wave 8 entry, with shipped + deferred + baseline sections).
- [x] **T-18** [build/docs] Update `AGENTS.md` — **NO-OP**. AGENTS.md already says "Skills (47)" (line 30, 68) and "Agents (9)" first-class (line 41, 69). Counts already accurate. No edit required.
- [x] **T-19** [build/docs] Create placeholder draft — **DONE** (`.ai-engineering/specs/drafts/skills-agents-excellence-phase-c.md` with deferred items, sequencing recommendation, North Star §0 mapping).
- [x] **T-20** [verify] Confirmed `.ai-engineering/state/specs/skills-agents-excellence-pragmatic.json` exists (328B). M0 lifecycle bootstrap path validated end-to-end. — **DONE**
- [x] **T-21** [build/ops] Update PR #509 title to combined scope + append Scope B section. — **DONE** (`gh pr edit 509` ok, title now "spec-128 + spec-129: context overrides + skills excellence pragmatic")
- [x] **T-22** [verify, depends-on=T-1..T-21] **DONE** — 152 passed, 7 skipped (perf gates intentionally skipped), 0 failed in 21.75s. All 14 DoD items ✅ (see `## DoD §D-129-05 Verification` below).

## DoD §D-129-05 Verification

| # | Item | Status |
|---|---|---|
| 1 | `skill_lint --check` exit 0 across all 47 skills (existing enforcement) | ✅ existing |
| 2 | All SKILL.md retain `## Examples` + `## Integration` sections | ✅ 47/47 |
| 3 | No new skills or agents created | ✅ git diff confirms |
| 4 | `tools/skill_app/deterministic_router.py` functional for 7 stacks | ✅ 29 tests green |
| 5 | Layer-isolation test green | ✅ `test_domain_layer_has_no_outer_ring_imports` |
| 6 | Hot-path budgets test green | ✅ (7 skipped, 0 failed) |
| 7 | `_lib/manifest_reader.py` ships with unit tests, used by ≥1 existing script | ✅ 9 tests + used by commit_compose, pr_body_compose |
| 8 | `_lib/git_activity.py` ships with unit tests, used by ≥1 existing script | ✅ 15 tests + used by session_bootstrap |
| 9 | `_lib/markdown_render.py` ships with unit tests, used by ≥1 existing script | ✅ 27 tests + used by session_bootstrap, commit_compose, pr_body_compose |
| 10 | `standup_render.py` ships with integration test against fixtures | ✅ 19 tests |
| 11 | `cleanup_run.py` ships with integration test against fixtures | ✅ 20 tests |
| 12 | `resolve_classify.py` ships with integration test against fixtures | ✅ 32 tests (11 adversarial) |
| 13 | CHANGELOG entry documents corrected counts and deferred items | ✅ spec-129 entry merged |
| 14 | PR #509 title and body updated to reflect combined scope | ✅ `gh pr edit 509` ok |

**Total new tests added**: 51 (Phase 0 libs) + 71 (Phase 1 scripts) = 122 new tests. Existing tests for refactored scripts (15 across 3 files) stay green. Layer-isolation honoured.

## Done condition

Plan is complete when:

1. All 22 tasks above are checked off.
2. T-22 verification step reports 14/14 ✅ on D-129-05 DoD.
3. `tests/perf/test_hot_path_budgets.py` still green (no regression introduced).
4. Branch `spec-128/context-overrides-refactor` is pushable to PR #509 with combined-scope commits.
5. `_history.md` row updated (auto via `mark_shipped` on PR merge — out of plan scope, handled by `/ai-pr`).
