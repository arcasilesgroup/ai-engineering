---
spec: spec-129
title: Skills + Agents Excellence Refactor — Pragmatic Scope
status: approved
effort: medium
---

# Skills + Agents Excellence Refactor — Pragmatic Scope

## Summary

The original brief `skills-agents-excellence-refactor.md` (Phase A + Phase B, 8 milestones M0–M7) tracks at 1/8 fully complete. Audit on 2026-05-10 found M7 ✅ shipped; M0/M1/M2/M3/M4/M5/§22 partial; M6 absent (1/47 skills has an eval corpus, none have ≥16 cases). Closing the original DoD requires writing ~736 eval cases (~150 hours focal) before any safe SKILL.md description refactor — the M2 CSO work and §22 pair-length cuts are unsafe without a regression gate. This spec **cuts M6 and its dependent items from the PR-#509 scope** and lands the mechanical, low-risk gaps that have a deterministic safety story. The deferred work is documented for a follow-up PR. The deliverable is **~13 hours of focal work** that closes the verifiable portion of the original DoD while preserving optionality for the description-level refactor once an eval corpus exists.

This spec extends PR #509 (originally `spec-128: Context Layout Refactor — Stack-Based Overrides`). Per user direction, **no new branch and no new PR** are created — all work lands on `spec-128/context-overrides-refactor` and #509 is renamed to reflect the combined scope.

## Goals

1. Land the three missing M3 shared libs (`manifest_reader.py`, `git_activity.py`, `markdown_render.py`) under `.ai-engineering/scripts/skills/_lib/`, with unit tests, used by at least the three existing scripts (`session_bootstrap.py`, `commit_compose.py`, `pr_body_compose.py`) where duplication exists today.
2. Land the three missing M3 hot-path scripts (`standup_render.py`, `cleanup_run.py`, `resolve_classify.py`), each with deterministic logic, ≤500 ms p95 budget, and at least one integration test against fixture data.
3. Close M4 reconciliation: document that **47 skills + 24 agents is the corrected baseline**, justified by the post-spec additions (`ai-analyze-permissions`, `ai-guide` agent retained per §22.4 boundary). Update CHANGELOG + AGENTS.md to reflect the corrected counts. Confirm `ai-poster` is **not** created — `ai-visual` already covers static visual art per spec-126 §4 alt clause.
4. Verify M5 `tools/skill_app/deterministic_router.py` is functional (not a stub): exercise `resolve_adapter()` against fixtures for all 7 supported stacks (TS, Python, Go, Rust, Swift, C#, Kotlin), confirm `UnknownStackError` raises on bad input.
5. Trigger M0 `.ai-engineering/state/spec-lifecycle.json` materialization via the standard brainstorm bootstrap path; confirm `sweep()` heals when JSON is missing on cold start.
6. Update PR #509 title and body to reflect the combined scope (`spec-128 context overrides + spec-129 skills excellence pragmatic`).
7. Rename and rescope the DoD: replace the original DoD §20 checklist with the trimmed checklist in §Decisions / D-129-05; deferred items (M6 evals, M3 SKILL.md ≤120 cuts, §22 pair cuts) move to a documented follow-up.
8. Hot-path budgets test (`tests/perf/test_hot_path_budgets.py`) stays green; new scripts must respect the existing budget ceilings.

## Non-Goals

- **No M6 eval corpus is built in this PR.** Writing 8–16 cases × 46 skills is deferred to a follow-up spec.
- **No SKILL.md description rewrites.** The 24 skills currently >120 lines stay as-is for this PR; the cuts are blocked behind an eval regression gate that does not yet exist.
- **No §22 pair-length cuts** (`ai-autopilot` skill 128/agent 107, `ai-verify` skill 127, etc.). Same reason: unsafe without regression detection.
- **No new skills or agents are created** as part of this PR. `ai-poster` is explicitly rejected.
- **No CSO optimization passes** via `/ai-prompt --skill <name>` over the existing skills.
- **No new branch and no new PR.** Work lands on `spec-128/context-overrides-refactor` and PR #509.
- **No changes to skill-discovery counts in the original brief** (e.g., "target 46 skills"). The baseline is updated to reflect the post-audit reality (47 + 24).
- **No new IDE adapters**, no new conformance rubric rules, no new agent identities.
- **No changes to spec-128 work that already shipped on this branch.** This spec runs additive only.

## Decisions

### D-129-01 — PR #509 scope expansion via title rename (option A)

**Decision**: Rename PR #509 to combine both scopes. New title proposal:
`spec-128 + spec-129: context overrides + skills excellence pragmatic`.
PR body gains a second `## Scope` block summarizing the spec-129 additions.

**Rationale**: User-selected option A out of three (rename / leave / sub-spec). Option A is the most honest about scope, reduces reviewer confusion, and preserves the spec-128 history on the branch. Option B (leave title, add commits) hides the second scope from reviewers scanning PR lists. Option C (frame as sub-spec) invents a parent-child relation that doesn't exist functionally.

**Consequence**: PR review surface area grows; reviewers must scan both blocks. Mitigated by clean separation in the PR body and the spec-129 decisions table.

### D-129-02 — Cut M6 evals and its dependent refactors from PR #509

**Decision**: Defer the M6 eval corpus build (46 skills × 8–16 cases) to a follow-up spec. Also defer everything that depends on eval regression detection: M3 SKILL.md ≤120 line cuts (24 skills), §22 pair-length cuts (5 pairs), M2 Grade A target uplift, CSO optimization passes via `/ai-prompt`.

**Rationale**: Without an eval corpus, any description-level rewrite is hope-driven. The original brief §3 conformance bar requires ≥16 cases per skill. Building that corpus is ~150 hours of focal work — too expensive to bundle with a PR that already carries the spec-128 work. The deferred items have no measurable safety story without the corpus; landing them blind would convert a refactor PR into a regression risk. The mechanical, deterministic items (libs, scripts, count reconciliation) carry no CSO risk and ship cleanly.

**Consequence**: Original DoD §7/§20 checklist items related to evals are removed from this PR. They are documented in §Open Questions for the follow-up. M3 token-cost gain (~1200 lines of excess SKILL.md prose) is not realized in this PR.

### D-129-03 — Accept 47 skills + 24 agents as the corrected baseline

**Decision**: Document that the actual repository state (47 user-facing skills under `.claude/skills/`, plus the `_shared/` helpers dir; 24 agents under `.claude/agents/`) is the correct baseline. The original brief's "46 skills + 23 agents" target was an estimate at draft time. Update CHANGELOG and AGENTS.md to reflect the corrected counts. Do not delete any current skills or agents.

**Rationale**: Investigation surfaced two legitimate additions post-spec: `ai-analyze-permissions` (Claude Code-only permission-rule consolidation skill, `copilot_compatible: false`) and the `ai-guide` agent (distinct from the `/ai-guide` skill — agent is a subagent dispatch target, skill is the user surface, per §22.4 of the original brief which allows agent-only files when there's no user-facing slash command).

**Consequence**: Original DoD "Skill count = 46, agent count = 23" line is removed. No alias breakage. The conformance lint (M1) continues to enforce per-skill quality independently of counts.

### D-129-04 — Confirm `ai-poster` is not created; `ai-visual` covers the case

**Decision**: Do not create `ai-poster`. `ai-visual` (85 lines) already covers static visual design (posters, banners, branding pieces, cover art) per its description ("posters, banners, flyers, branding pieces, cover art, identity compositions"). The original brief §4 explicitly allowed the alt: "`/ai-visual` if poster is too narrow".

**Rationale**: Creating `ai-poster` would duplicate the trigger surface of `ai-visual` and force a narrow-scope split with no benefit. The audit confirmed `ai-poster` was never created during the original refactor — this reflects an implicit decision that we now make explicit.

**Consequence**: M4 §4 rename row "ai-canvas → ai-poster" is closed as "ai-canvas → ai-visual (consolidated, ai-poster not created)". Document this in CHANGELOG so future readers understand the divergence from the original brief.

### D-129-05 — Replace DoD §20 with the trimmed checklist

**Decision**: The PR-merge gate for this work is the following 14-item list. Replaces the original DoD §7/§20 with the items that have a deterministic safety story.

- [ ] `skill_lint --check` exit 0 across all 47 skills (existing rule — already enforced)
- [ ] All SKILL.md retain `## Examples` + `## Integration` sections (already 47/47)
- [ ] No new skills or agents created (verified by git diff against `.claude/`)
- [ ] `tools/skill_app/deterministic_router.py` functional for 7 stacks; new test file proves it
- [ ] Layer-isolation test green (`tests/architecture/test_layer_isolation.py` — already green)
- [ ] Hot-path budgets test green (`tests/perf/test_hot_path_budgets.py` — must remain green)
- [ ] `_lib/manifest_reader.py` ships with unit tests, used by ≥1 existing script
- [ ] `_lib/git_activity.py` ships with unit tests, used by ≥1 existing script
- [ ] `_lib/markdown_render.py` ships with unit tests, used by ≥1 existing script
- [ ] `standup_render.py` ships with integration test against fixtures
- [ ] `cleanup_run.py` ships with integration test against fixtures
- [ ] `resolve_classify.py` ships with integration test against fixtures
- [ ] CHANGELOG entry documents the corrected counts (47 + 24) and the deferred items
- [ ] PR #509 title and body updated to reflect combined scope (D-129-01)

### D-129-06 — Reuse existing `_history.md` and `spec_lifecycle.py`

**Decision**: Use the existing `spec_lifecycle.py` (already shipping) to manage the spec-129 lifecycle. JSON sidecar is `.ai-engineering/state/specs/skills-agents-excellence-pragmatic.json` (already created by the brainstorm bootstrap on 2026-05-11). On PR merge, the `/ai-pr` skill calls `mark_shipped("spec-129-skills-agents-excellence-pragmatic", 509, "spec-128/context-overrides-refactor")`.

**Rationale**: M0 plumbing is already in place. This spec exercises it as the validation path. No new infrastructure needed.

**Consequence**: Confirms M0 wiring works end-to-end for the next-N brainstorm without writing a separate test fixture.

### D-129-07 — Effort sizing and time-boxing

**Decision**: Effort = `medium`. Estimated ~13 hours of focal work, broken as:
- 4h — three shared libs + tests (`_lib/manifest_reader.py`, `_lib/git_activity.py`, `_lib/markdown_render.py`)
- 6h — three scripts + tests (`standup_render.py`, `cleanup_run.py`, `resolve_classify.py`)
- 1h — M5 router verification test (one new test file)
- 1h — CHANGELOG + AGENTS.md updates
- 1h — PR #509 title and body update + spec lifecycle confirmation

**Rationale**: Each unit is mechanically scoped and has fixture-testable behaviour. No LLM-judgment items.

**Consequence**: If a unit overruns by >50%, raise the question in §Open Questions before continuing. Hard ceiling: 20 hours total before requesting a scope re-check.

### D-129-08 — Test-first ordering per item

**Decision**: For each new lib and script, write the failing test before the implementation (TDD per AGENTS.md hard rule). Order per unit: red test → implementation → green test → integration into existing script (libs only) → measurement against perf budget.

**Rationale**: AGENTS.md and CLAUDE.md require TDD as a hard rule. New libs and scripts have well-defined inputs and outputs (regex parsing, git output transformation, markdown templating), making them straightforward to test-drive.

**Consequence**: Each commit on this PR for spec-129 work is preceded by a red-test commit. Hot-path budget changes are measured in CI, not estimated.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Shared lib refactor breaks `session_bootstrap.py` or `commit_compose.py` or `pr_body_compose.py` regression | Medium | High (hot-path scripts are daily-driver) | Existing scripts get integration test coverage in this spec before refactor; new libs land behind a feature-add commit, then the integration commit follows. Per-commit CI gate. |
| `resolve_classify.py` mis-categorizes a real conflict and auto-resolves wrong | High | High (silent merge corruption) | Conservative classification: only auto-resolve lock files (`*.lock`, `package-lock.json`, `uv.lock`, `poetry.lock`, `Cargo.lock`) and explicit `// AUTO-GENERATED` sentinels. Migration paths return `ambiguous`. Test fixtures include adversarial cases (lock file with manual edits, generated file without sentinel). |
| PR #509 review confusion under combined scope | Medium | Medium | PR body gets explicit `## Scope A — spec-128` and `## Scope B — spec-129` sections (D-129-01). Per-commit subject prefixes (`spec-128:` or `spec-129:`) so reviewers can filter. |
| Deferred items rot in backlog | Medium | Medium | Open a placeholder draft `skills-agents-excellence-refactor-phase-c.md` under `.ai-engineering/specs/drafts/` at PR merge time with the deferred bullet list (M6, M3 cuts, §22 cuts) so the work is tracked, not lost. |
| Hot-path perf regression from new shared libs | Low | High | The shared libs are pure-Python stdlib (no I/O imports added). New libs benchmarked in CI per item. If `_lib/git_activity.py` adds >50 ms to `session_bootstrap.py`, the lib gets rolled back. |
| `tools/skill_app/deterministic_router.py` is actually a stub | Low | Medium | Audit showed the file is 76 lines with `resolve_adapter()` implemented (read on 2026-05-11). Risk is verifying tests exist; if absent, write them as part of the M5 verification step. |
| AGENTS.md or CLAUDE.md edit conflicts with parallel changes | Low | Low | Spec-128 already touched these files; spec-129 edits are append-only (CHANGELOG entries, count line update). Rebase if needed. |

## References

- pr: arcasilesgroup/ai-engineering#509
- doc: .ai-engineering/specs/drafts/skills-agents-excellence-refactor.md
- doc: .ai-engineering/specs/archive/spec-128-context-overrides.md
- doc: AGENTS.md
- doc: CLAUDE.md
- doc: .ai-engineering/contexts/spec-schema.md
- research: (none — evidence sourced from on-disk audit dated 2026-05-10)

## Open Questions

1. **Follow-up spec naming**: should the deferred bundle be named `spec-130-skills-excellence-phase-c` or `spec-129-followup`? Lean toward `spec-130` for clean lineage. Resolve at PR merge.
2. **M6 eval MVP size**: when the follow-up spec opens, should we ship 8 cases/skill (~46h focal) or hold at the original 16/skill (~150h)? Recommendation: 8 + iterate. Decide in the follow-up brainstorm.
3. **Pre-commit hook integration**: `skill_lint --check` is shipped, but is it actually wired into `.git/hooks/pre-commit` on contributor machines? Verify in M1 closeout; if missing, wire it (1h, no risk).
4. **`_history.md` row format compliance**: spec-128 wrote a row in the old format; the 7-col format may need a one-time migration. Out of scope for spec-129 but flagged for the follow-up.

