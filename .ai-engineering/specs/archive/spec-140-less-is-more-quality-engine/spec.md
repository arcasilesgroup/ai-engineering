---
spec: spec-140
slug: less-is-more-quality-engine
title: Less-Is-More Quality Engine — Hard-Delete Dead Weight, Collapse Matrices, Consolidate Roster
status: approved
effort: large
branch: claude/review-spec-drafts-DX2pD
source_brief: .ai-engineering/specs/drafts/less-is-more-quality-engine-brief.md
target_dispatch: /ai-build
chains_after: spec-139
mantra: "Con menos, hacemos más."
date_approved: 2026-05-16
auto_approved: true
auto_approval_reason: operator invoked --no-hitl autonomous run; brief carries explicit recommendations on all 8 D-Q decisions; CONSTITUTION.md §3 hard-delete posture removes shim ambiguity
summary: Hard-delete the dead-test archaeology (`TestVerifyCmdJsonFlag` skip class, four `pytest.fail()`-bodied xfail stubs, three "tracked separately" hard skips), collapse the 9-cell python+OS matrix to 1 cell + 3 OS, replace 27 inline `setup-uv` blocks with a composite action, remove the redundant mirror-parity test, kill the help-snapshot ceremony, fix the `instinct-observe` PreToolUse/PostToolUse double-registration mislabel, audit the 39 Python hooks against `hooks-manifest.json` and delete unreferenced scripts (`strategic-compact.py`), and split the two oversized validator-category monoliths (`manifest_coherence.py` 1,221 LOC, `mirror_sync.py` 1,108 LOC) so the matching test files shrink in the same commit. Quality cluster collapses from 11 → 6 reviewers + 4 → 3 verifiers, gated by pass@k eval against the recent PR corpus. ~600 LOC saved in Wave 1; ~1,500 in Wave 2; ~1,400 in Wave 2.5; ~1,200 in Wave 3.
---

# spec-140 — Less-Is-More Quality Engine

> Mantra: **Con menos, hacemos más.**

## Summary

The repo currently ships 121,380 LOC across 555 test files, 11 GitHub workflows with ~57 jobs, 39 Python hook scripts (12,398 LOC), 18 quality-cluster files (3,342 LOC), and 292 production files at 73,292 LOC. A handful of validator modules carry disproportionate complexity that the test surface is forced to mirror (the 2,552-LOC `test_validator.py` exists because the 1,221-LOC `manifest_coherence.py` module is monolithic). The quality engine that enforces the framework's "less for more" promise is paradoxically the surface most saturated with ceremony, duplication, and skipped-or-xfail placeholders. This spec lands a coordinated multi-wave hard-delete + collapse + consolidate program: Wave 1 removes archaeology and dead xfail stubs; Wave 2 collapses the CI matrix and extracts composite actions; Wave 2.5 splits the validator monoliths along the test-file seam (one-way contract: production refactor ships ONLY when it unlocks a measurable test deletion); Wave 3 collapses the reviewer roster 11→6 and verifier roster 4→3, gated by pass@k eval against the recent PR corpus. CONSTITUTION.md §3 binds: every removal is hard, no shims, CHANGELOG-only audit. The north star is Beck's rent rule: a test, job, hook, or agent that has not caught a regression in the recent window is decoration, not infrastructure.

## Goals

1. **Tests trimmed.** Total test-file count ≤ 350 (current 555); total test LOC ≤ 80,000 (current 121,380); zero hard `@pytest.mark.skip` without a ticket reference; zero `pytest.fail()`-bodied tests.
2. **Workflows collapsed.** Total job count ≤ 25 (current ~57); zero duplicate `uses: astral-sh/setup-uv` invocations outside the composite action; PR wall-clock p50 ≤ 6 minutes.
3. **Hooks clean.** Every script in `.ai-engineering/scripts/hooks/` is referenced by `.claude/settings.json` or by another hook; sha256 manifest matches disk exactly; zero hooks double-registered on overlapping events.
4. **Quality cluster shrunk.** Reviewer agent count ≤ 7 (current 11); each remaining agent has an explicit firing contract and pass@k eval row.
5. **Production decongested.** Zero validator-category modules > 1,000 LOC; zero 5-LOC placeholder modules; `src/ai_engineering/validator/categories/` net LOC unchanged or reduced after the refactor.
6. **Production-test 1:1 invariant.** Every production change in Wave 2.5 deletes or splits at least one test file. PR diff makes the mapping explicit.
7. **No regressions.** `/ai-verify --release` returns GO; `/ai-reliability-eval` shows no decrease in pass@k for the surviving agents; validator categories produce byte-identical findings on the existing fixture corpus.
8. **Audit trail.** CHANGELOG documents every hard-rename or hard-delete; one `framework_event kind=quality_engine_collapse` per wave.

## Non-Goals

- The `/ai-build`, `/ai-plan`, `/ai-brainstorm` canonical chain — touched only where a quality skill contract changes.
- Production refactors that do not unlock test simplification — those belong to a future `/ai-simplify-sweep`.
- Engram, MCP servers, board integration.
- Documentation portal regeneration.
- "Soft delete" via `pytest.mark.skip` or `if False:` — every removal is hard.
- New abstraction layers to "manage" the surface (KISS + YAGNI bind harder than DRY).
- Blanket property-based test rewrites — PBT decided per cluster.

## Decisions

- **D-140-01 — Conftest layer ownership of git-repo fixture.** `tests/conftest.py` owns the canonical fixture; `tests/integration/conftest.py` consumes it via `request.getfixturevalue`. Rationale: pytest fixtures resolve from broadest scope first; one fixture, one home. Resolves brief D-Q1.
- **D-140-02 — Hot-path injection guard disposition.** Option (a): keep as-is. Rationale: spec-139 M5 adds module-level mtime caching that reduces per-call cost to < 50 ms; splitting into stub + async heavy path is premature optimization (spec-139's cache already meets budget). Resolves brief D-Q2.
- **D-140-03 — Python matrix policy.** Collapse to 3.12 only on 3-OS matrix. Rationale: coverage upload is already gated to 3.12; the 3.11 and 3.13 legs exercise identical source against identical stdlib; nightly schedule preserves full matrix as advisory. Resolves brief D-Q3.
- **D-140-04 — Reviewer roster eval source.** `.ai-engineering/runtime/quality-evals/`. Rationale: `evals/` is itself a deletion candidate in the parallel surface-cleanup brief; the `runtime/` namespace is preserved across cleanup waves; the harness is project-local and not committed. Resolves brief D-Q4.
- **D-140-05 — `/ai-advise` capacity for absorbed heuristics.** Sub-spec deferred to a follow-up. Rationale: `/ai-advise` is already advisory (non-blocking); absorbing architecture + verifier-architecture heuristics into a non-blocking advisor cannot regress correctness; load-balancing the advisor is a future concern. Resolves brief D-Q5.
- **D-140-06 — Help-snapshot replacement.** Acceptable loss — replace with a "command-list exists" assertion. Rationale: the snapshot test catches wording (not logic) on a renderer the repo does not own; logic-level CLI assertions live in `tests/unit/test_*_cli.py`. Resolves brief D-Q6.
- **D-140-07 — Production-test causation threshold for Wave 2.5.** Metric (a) LOC ratio with 2x floor. Rationale: the floor is a hard production-refactor justification gate; if a production split saves fewer than twice its overhead in tests, it does not ship. Resolves brief D-Q7.
- **D-140-08 — Validator-stub disposition.** Per-stub decision codified in Wave 2.5:
  - `skill_frontmatter.py` (5 LOC) → absorb into `manifest_coherence/` split package (becomes one of the dimension modules).
  - `cross_references.py` (5 LOC) → delete (no consumer; surface duplicated by `tools/spec_lint/checks/references.py`).
  - `counter_accuracy.py` (5 LOC) → absorb into `manifest_coherence/counter_accuracy.py` (becomes a coherence dimension).
  Resolves brief D-Q8.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Deleted test masks a real regression | Medium | High | Wave 1 only removes skipped/xfail-stub tests producing zero signal; Wave 2 deletions backed by duplicate-detection script |
| Roster shrink degrades review quality | Medium | High | Wave 3 gated by pass@k eval against PR corpus; no merge without empirical evidence |
| CI matrix collapse hides a real py-version bug | Low | Medium | Opt-in `nightly-matrix.yml` on `schedule:` for full python+OS sweep; failure pages but does not block PRs |
| Hook double-registration fix breaks observability | Low | Medium | The `hook_kind` mislabel today already breaks observability; the fix restores ground truth |
| `setup-uv` composite action breaks a workflow edge case | Medium | Low | Composite action byte-equivalent to current inline blocks; tested on throwaway workflow first |
| Snapshot test removal lets a benign wording change ship a real bug | Low | Low | Current snapshot test catches wording, not logic |
| CONSTITUTION.md §3 enforcement makes rollback the only recovery | Low | Medium | Each wave is a single commit; rollback = `git revert <sha>` |
| Validator split breaks public API consumed by external callers | Low | High | Public API preserved via `__init__.py` re-exports; spec phase greps importers and asserts byte-identical exports |
| Wave 2.5 ships production refactor without matching test deletion | Medium | Medium | D-140-07 2x LOC ratio gate enforced at PR review |
| Production refactor masquerades as "less for more" while net-adding LOC | Medium | Medium | DoD §5 caps validator/categories at net LOC unchanged or reduced |

## References

- doc: .ai-engineering/specs/drafts/less-is-more-quality-engine-brief.md
- doc: CONSTITUTION.md §3 (no backwards-compat shims)
- doc: CLAUDE.md §11 (canonical chain unchanged)
- doc: .ai-engineering/reference/principles.md §10.1 KISS, §10.2 YAGNI, §10.4 DRY, §10.5 TDD, §10.7 Clean Code
- doc: Kent Beck, *Test Desiderata* (2019)
- doc: Anthropic Engineering, *How we built our multi-agent research system* (June 2025) — sub-agent roster sizing
- pr: arcasilesgroup/ai-engineering#514 (spec-136 + spec-137 — concurrent reductions on the same lineage)

## Open Questions

None — all eight D-Q decisions in the brief are resolved as D-140-01 through D-140-08.
