---
spec: spec-167
title: Plan — Sweep honesty + slot-clobber guard + single-PR consolidation
status: approved
pipeline: full
phases: 5
execution_route:
  version: 1
  spec: spec-167
  executor: build
  automation: hitl
  concern_count: 3
  estimated_files: 20
  reason: Three sequential concerns (sweep honesty cleanup -> slot-clobber guard -> pre-merge consolidation) over high-risk surfaces — hot-path hook integrity (nudge + manifest re-pin), dual template-mirror parity (spec_lifecycle.py + runtime-observation-nudge.py, neither CI-guarded), and a judgment-heavy prose reorder of /ai-pr's merge sequence. At the autopilot file-count boundary (inflated by mirror/template fan-out) but the integrity/parity risk profile warrants controlled per-task TDD over autonomous waves. Operator may opt for /ai-autopilot instead.
  safe_next_command: "/ai-build"
---

# Plan — spec-167 Sweep honesty + slot-clobber guard + single-PR consolidation

Three independent-but-sequential concerns. Foundation-first within each:
delete dead scaffolding before editing the docs that reference it; write the
RED test before the `slot_status` verb; rewrite `/ai-pr` prose last (highest
judgment, lowest mechanical risk). Every SKILL.md / hook / script edit that has
a mirror or template twin is paired with its sync/regen task in the SAME phase —
parity drift is the dominant failure mode here (no CI guard for
`spec_lifecycle.py` or the nudge template).

## Branch / PR

- Working branch: `claude/spec-167-lifecycle-execution-gaps` (build branches from `main`).
- Target: `main` via a SINGLE PR (and per D-167-07 this PR also carries its own consolidation commit).

## Quality bar

- `ai-eng spec verify --fix` clean; `spec_lint --check` BLOCKERS=0 (after plan lands).
- `tests/unit/config` + `tests/unit/docs` + `tests/unit/scripts` + `tests/unit/specs` + `tests/conformance` green.
- `ai-eng check` 7/7; mirror byte-parity (`scripts/sync_mirrors/core.py --check`) clean.
- Hook integrity: `hooks-manifest.json` re-pinned; `tests/unit/hooks/test_canonical_events_count.py` green.
- No suppression tokens, no backwards-compat shims (§13.2/§13.3).

---

## Phase 1 — Sweep honesty cleanup (D-167-01, D-167-02, D-167-03)

Rip the phantom-schedule scaffolding from both sweeps. Delete dead scripts +
dead tests FIRST, then the docs that reference them, then regenerate mirrors.

- [x] T-1 — Delete the four dead scheduled wrapper scripts
  - Agent: build
  - Files: `.ai-engineering/scripts/scheduled/session-watch-sweep.sh`, `.ai-engineering/scripts/scheduled/session-watch-sweep.ps1`, `.ai-engineering/scripts/scheduled/simplify-sweep.sh`, `.ai-engineering/scripts/scheduled/simplify-sweep.ps1`
  - Principles applied: §10.1 KISS (delete a prop that emits only `skipped`), §13.3 hard-delete
  - Patch (deterministic): `git rm .ai-engineering/scripts/scheduled/session-watch-sweep.sh .ai-engineering/scripts/scheduled/session-watch-sweep.ps1 .ai-engineering/scripts/scheduled/simplify-sweep.sh .ai-engineering/scripts/scheduled/simplify-sweep.ps1` — no template mirror exists (`src/ai_engineering/templates/.ai-engineering/scripts/scheduled/` absent). If the now-empty `scheduled/` dir remains, leave it only if another script lives there; else remove it.
  - Gate: `ls .ai-engineering/scripts/scheduled/` shows no `*-sweep.*`; repo grep for `scheduled/session-watch-sweep`/`scheduled/simplify-sweep` returns only doc/test hits resolved in later tasks.

- [x] T-2 — Delete the dead ps1-parity test (asserts a now-deleted script)
  - Agent: build
  - Files: `tests/unit/scripts/test_simplify_sweep_ps1_parity.py`
  - Principles applied: §10.7 Clean Code (dead test follows dead code)
  - Patch (deterministic): `git rm tests/unit/scripts/test_simplify_sweep_ps1_parity.py` — the whole module asserts `_SH_PATH`/`_PS1_PATH` existence (lines 48-49, 135-138), meaningless once T-1 lands.
  - Gate: `pytest tests/unit/scripts -q` collects no `test_simplify_sweep_ps1_parity`.

- [x] T-3 — Remove the dead R5 simplify-sweep parity test from naming-lint
  - Agent: build
  - Files: `tests/conformance/test_naming_lint.py:327-349`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): delete `test_r5_parity_flags_simplify_sweep_passes_after_landing` (lines 327-349). It `pytest.skip`s once `simplify-sweep.ps1` is gone, so it is permanently dead, not failing. Leave the generic `scheduled_root` R5 fixtures that lint the (now scriptless) `scheduled/` dir IF that dir still exists; if T-1 removed the dir, verify `check_naming` fails-open on an absent `scheduled_root` and adjust the fixture to tolerate it.
  - Gate: `pytest tests/conformance/test_naming_lint.py -q` green.

- [x] T-4 — Strip scheduling scaffolding from `ai-session-watch-sweep/SKILL.md`
  - Agent: build
  - Files: `.claude/skills/ai-session-watch-sweep/SKILL.md` (canonical source)
  - Principles applied: §10.6 SDD (docs match reality), Honest-&-Direct (SOUL)
  - Patch (deterministic): delete these blocks (by content, top-down so line numbers stay valid): the `## Scheduling` section (lines 73-85), the `## Scheduled cadence` section (lines 135-151), the `## References` "Scheduled wrapper:" line (157). Edit line 128 `Called by: \`/ai-schedule\` (weekly cron) or operator manually.` → `Called by: operator manually.`. Soften the false-automation framing WITHOUT breaking triggering: frontmatter `description` (line 3) drop "on a schedule" / "scheduled consolidation" / "on a cadence" phrasings but KEEP "session-watch sweep" + "consolidate observations" triggers; `tags` (line 7) remove `scheduled` (keep `[meta, session-watch, autonomous]` or drop `autonomous` too if it implies unattended — keep list non-empty); Purpose (lines 14-19) reword "scheduled wrapper that runs the review on a cadence" → "manual wrapper that runs the review, gates it, and opens a draft chore PR — keeping consolidation off feature branches".
  - Gate: `grep -n "ai-schedule\|Scheduled cadence\|/schedule weekly\|0 4 \* \* " .claude/skills/ai-session-watch-sweep/SKILL.md` returns nothing; `tests/unit/test_ai_simplify_sweep_skill.py`-equivalent for this skill (frontmatter/registry) green.

- [x] T-5 — Strip scheduling scaffolding from `ai-simplify-sweep/SKILL.md`
  - Agent: build
  - Files: `.claude/skills/ai-simplify-sweep/SKILL.md` (canonical source)
  - Principles applied: §10.6 SDD, §10.4 DRY (same fix as T-4, sibling skill)
  - Patch (deterministic): delete the `## Scheduling` section (lines 59-67), the `## Scheduled cadence (spec-121)` section (lines 112-122), the `## References` "Scheduled wrapper:" line (129). Edit line 108 `Called by: \`/ai-schedule\` (weekly cron) or operator manually.` → `Called by: operator manually.`. Soften `description`/`tags`/Purpose identically to T-4 (drop `scheduled`/cadence framing, keep "simplify sweep" trigger).
  - Gate: `grep -n "ai-schedule\|Scheduled cadence\|/schedule weekly\|0 4 \* \* " .claude/skills/ai-simplify-sweep/SKILL.md` returns nothing; `tests/unit/test_ai_simplify_sweep_skill.py` green.

- [x] T-6 — Strip the stray `/ai-schedule` from `ai-simplify/SKILL.md`
  - Agent: build
  - Files: `.claude/skills/ai-simplify/SKILL.md:48`
  - Principles applied: §10.6 SDD
  - Patch (deterministic): in the `## Distinction from /ai-simplify-sweep` table, change the cell `| Invocation | On-demand by operator | Scheduled (weekly cron, \`/ai-schedule\`) |` → `| Invocation | On-demand by operator | On-demand by operator or sibling sweep skill |` (remove the `/ai-schedule` reference; the sibling is no longer "scheduled").
  - Gate: `grep -n "ai-schedule" .claude/skills/ai-simplify/SKILL.md` returns nothing.

- [x] T-7 — Regenerate IDE mirrors for the three edited SKILL.md files
  - Agent: build
  - Files: `.codex/`, `.agents/`, `.github/`, `.opencode/` skill mirrors + `src/ai_engineering/templates/project/.*/skills/...` for `ai-session-watch-sweep`, `ai-simplify-sweep`, `ai-simplify`
  - Principles applied: §16 Surface Axiom (byte-equivalent mirrors), §10.4 DRY
  - Patch (deterministic): run `ai-eng dev sync` (→ `scripts/sync_mirrors/core.py`); do NOT hand-edit mirrors.
  - Gate: `python scripts/sync_mirrors/core.py --check` clean; `tests/mirrors/test_count_parity.py` green (count stays 54 — no skill added/removed); `tests/architecture/test_surface_parity.py` green.

- [x] T-8 — Phase-1 gate sweep (no count drift, budgets still satisfied)
  - Agent: verify
  - Files: `tests/unit/config/test_manifest.py:330-331`, `tests/unit/test_skill_line_budget_post_cleanup.py:46`
  - Principles applied: §10.7 Clean Code
  - Gate: confirm `config.skills.total == 54` still holds (no registry change); `pytest tests/unit/config tests/unit/test_skill_line_budget_post_cleanup.py tests/conformance -q` green. Line-budget only EASES (sections deleted) — assert no regression.

## Phase 2 — Nudge honesty (D-167-04)

- [x] T-9 — Drop the "(or the scheduled …)" phrase from the SessionStart nudge
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/runtime-observation-nudge.py:32-36` AND template mirror `src/ai_engineering/templates/.ai-engineering/scripts/hooks/runtime-observation-nudge.py` (byte-identical edit)
  - Principles applied: §10.6 SDD, Honest-&-Direct (SOUL), §13 hook hot-path
  - Patch (deterministic):
    ```diff
    @@ _HINT
     _HINT = (
         "[observation-nudge] Unconsolidated session-watch observations are pending "
    -    "review — run /ai-session-watch --review (or the scheduled "
    -    "/ai-session-watch-sweep) to consolidate corrections into the corpus."
    +    "review — run /ai-session-watch --review to consolidate corrections "
    +    "into the corpus."
     )
    ```
    Apply the IDENTICAL hunk to the template mirror.
  - Gate: `diff .ai-engineering/scripts/hooks/runtime-observation-nudge.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/runtime-observation-nudge.py` shows no diff; `grep -c "scheduled" .ai-engineering/scripts/hooks/runtime-observation-nudge.py` == 0.

- [x] T-10 — Re-pin the hooks-manifest sha for the edited hook
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json:72` (regenerated, not hand-edited)
  - Principles applied: §13 hook integrity (editing a hook without re-pinning self-disables it)
  - Patch (deterministic): run `python .ai-engineering/scripts/regenerate-hooks-manifest.py`; confirm only the `runtime-observation-nudge.py` sha entry changed.
  - Gate: `tests/unit/hooks/test_canonical_events_count.py` green; hook-integrity verification passes (`AIENG_HOOK_INTEGRITY_MODE=enforce` does not disable the nudge); `hookCount` unchanged (76).

## Phase 3 — Deterministic slot-clobber guard (D-167-05, D-167-06)

TDD: RED test for the new verb before the verb exists, then GREEN, then wire the consumer.

- [x] T-11 — RED: tests for the `slot_status` verb
  - Agent: build
  - Files: `tests/unit/specs/test_spec_lifecycle.py` (extend)
  - Principles applied: §10.5 TDD (RED before GREEN)
  - Patch (deterministic): add cases asserting JSON output of `slot_status`: (a) IDLE slot (`spec.md` == `# No active spec …` placeholder) → `{"occupied": false, "idle": true, "spec_id": null, ...}`; (b) OCCUPIED by an un-shipped spec → `{"occupied": true, "spec_id": "spec-NNN", "state": "approved"|"draft"|"in_progress", "slug": "..."}`; (c) OCCUPIED by a SHIPPED spec → `occupied` reflects state so the consumer can treat shipped-but-not-cleared as safe-to-overwrite; (d) malformed/missing frontmatter → fail-open shape (no exception, `occupied` conservative). Use the existing tmp-repo fixtures in this module.
  - Gate: new tests FAIL (verb not implemented) — RED confirmed.

- [x] T-12 — GREEN: implement `slot_status` in `spec_lifecycle.py` (+ template mirror)
  - Agent: build
  - Files: `.ai-engineering/scripts/spec_lifecycle.py` (function near `status()` ~667-669; subparser after `status` reg ~1587-1589; dispatch `elif` after status ~1639-1641) AND byte-identical `src/ai_engineering/templates/.ai-engineering/scripts/spec_lifecycle.py`
  - Principles applied: §10.5 TDD (GREEN), §10.3 SOLID (read-only query, no state mutation), §13.7 SSOT
  - Patch (deterministic): no — judgment. Add a no-arg `slot_status(project_root)` that: reads `_spec_frontmatter_id()` (~1239); if buffer is placeholder via `_buffer_is_placeholder()` (~429-446) return idle shape; else load the sidecar state for that id and return `{occupied, idle, spec_id, slug, state}`. Register subparser like `sweep` (no positional, ~1585-1586) and add the dispatch `elif args.cmd == "slot_status": print(json.dumps(slot_status(project_root), indent=2))`. COPY the file byte-identical to the template mirror (no CI parity guard — D-167-06).
  - Gate: T-11 tests pass (GREEN); `diff` canonical vs template mirror empty; `tests/unit/scripts/test_spec_lifecycle_python_compat.py` green.

- [x] T-13 — Wire `/ai-brainstorm` Step -1 to call `slot_status` (advisory, fail-open)
  - Agent: build
  - Files: `.claude/skills/ai-brainstorm/SKILL.md` (insert between line 39 and Step 0 at line 40) + mirror regen via `ai-eng dev sync`
  - Principles applied: §10.6 SDD, fail-open principle (SOUL/Operating-Mindset)
  - Patch (deterministic): no — prose. Add "Step -1 — Live-slot guard (before Step 0)": run `python .ai-engineering/scripts/spec_lifecycle.py slot_status`; if `occupied==true` and `state` is not SHIPPED, surface `spec_id`/`slug`/`state` and ask the operator to either run `--consolidate-spec <slug>` first or confirm overwrite; on idle/shipped/script-error, proceed silently (fail-open — never block).
  - Gate: `ai-eng spec verify` clean on the skill; mirror parity green; `tests/unit/skills/test_brainstorm_auto_spec_gate.py` (and any brainstorm SKILL test) green.

## Phase 4 — Pre-merge consolidation in `/ai-pr` (D-167-07)

Move consolidation from post-merge to post-PR-creation/pre-merge so it rides the feature PR.

- [x] T-14 — Rewrite `/ai-pr` consolidation to pre-merge on the feature branch
  - Agent: build
  - Files: `.claude/skills/ai-pr/SKILL.md` (Step 11 at line 69; new step after Step 14 PR-creation ~89 and before Step 16 watch ~95) + mirror regen
  - Principles applied: §10.6 SDD, §13.7 SSOT, Surgical-Changes (timing only, not mechanics)
  - Patch (deterministic): no — judgment/prose. Split Step 11: KEEP the pre-PR half (read spec.md+plan.md, `spec verify --fix`, update to actual scope, compose body). MOVE the consolidation half out of "After PR merge": after Step 14 opens the PR and the PR number `N` is known, run the shared handler `mark_shipped <spec-NNN> N <branch>` ON THE FEATURE BRANCH (archive + clear slot + `_history.md` row + sidecar SHIPPED), then `git add` the consolidated/cleared/archived files, commit `chore(spec-NNN): consolidate (archive + clear live slot)`, and push to the same branch so the open PR updates. Auto-complete (Step 15) and watch (Step 16) proceed unchanged but Step 16 must expect the extra commit before merge. Update the trailing note: `/ai-branch-cleanup` Phase 5 `reconcile_merged` is now a defense-in-depth no-op backstop (consolidation already rides the PR regardless of gh-CLI vs web-UI merge). Remove the "After PR merge" wording and the separate-chore-PR implication.
  - Gate: `ai-eng spec verify` clean; mirror parity green; `tests/unit/test_consolidate_spec_action.py` still asserts all callers wire `_shared/consolidate-spec.md` (unchanged handler) — green.

- [x] T-15 — Guard: a consolidated feature PR (idle slot) stays green
  - Agent: build
  - Files: new/extended test under `tests/unit/specs/` or `tests/unit/validator/` (idle-slot tolerance) — locate the existing `_IDLE_SLOT_PREFIX` consumer tests
  - Principles applied: §10.5 TDD, §10.6 SDD (Risk: feature PR now CIs against placeholder slot)
  - Patch (deterministic): no — judgment. Audit every `spec.md`-reading gate (`tools/spec_lint/cli.py:_IDLE_SLOT_PREFIX`, `verify/service.py`, `manifest_coherence.py`, `vcs/pr_description.py`, docs spec-marker test) for idle tolerance; add an explicit case asserting that with `spec.md`/`plan.md` at the placeholder AND an archived `spec-NNN/` present, `spec_lint --check` BLOCKERS=0 and verify is advisory-only. This encodes the D-167-07 "feature PR runs CI against idle slot" risk as a regression test.
  - Gate: new test green; `pytest tests/unit/specs tests/unit/validator tests/docs -q` green.

## Phase 5 — Full verification

- [x] T-16 — Repo-wide green gate + parity + integrity
  - Agent: verify
  - Files: whole tree
  - Principles applied: §10.4 Goal-Driven Execution (green before done)
  - Gate: `pytest tests/unit/config tests/unit/docs tests/unit/scripts tests/unit/specs tests/unit/skills tests/unit/hooks tests/conformance tests/mirrors tests/architecture -q` green; `python scripts/sync_mirrors/core.py --check` clean; `ai-eng check` 7/7; `spec_lint --check .ai-engineering/specs/spec.md .ai-engineering/specs/plan.md` BLOCKERS=0; no suppression tokens introduced; `grep -rn "ai-schedule\|Scheduled cadence" .claude .codex .agents .github` returns nothing.

---

## Quality Outcome

**Status: GREEN** (one bounded quality pass; two findings fixed in-loop).

- **Tasks**: 16/16 complete across 5 phases.
- **Tests**: 890 passed in the core batch (config, docs, scripts, specs, skills, conformance, mirrors, architecture); hooks suite 305 passed; new coverage = `TestSlotStatus` (8) + 2 idle-slot-CI regression tests.
- **Parity**: `sync_mirrors --check` exit 0; `spec_lifecycle.py` + `runtime-observation-nudge.py` byte-identical to template twins; governance README twin resynced.
- **Integrity**: `ai-eng check` 7/7; `hooks-manifest.json` re-pinned (nudge sha; hookCount 76); `spec_lint --check spec.md` BLOCKERS=0.
- **Hard rules**: no new suppression tokens (§13.2 — relocated import to top instead of `# noqa`); no backwards-compat shims (§13.3 — wrappers hard-deleted); ruff clean on all touched Python.

### Findings fixed in-loop
1. **Governance README twin drift** — `ai-eng dev sync` regenerated the live capability catalog (new sweep descriptions) but not its template twin; resynced to restore byte-parity.
2. **New `# noqa: E402` introduced** by the idle-slot regression test's mid-file import — relocated `from spec_lint import cli` to the top import block (no suppression).

### Pre-existing failures (NOT spec-167 — confirmed failing on clean `main`)
- `tests/conformance/test_skills_rubric.py::test_rule_3_negative_scoping` and `::test_rule_10_no_anti_patterns` — assert `52` graded skills; repo has `53` on `main` independent of this branch. Out of scope.
