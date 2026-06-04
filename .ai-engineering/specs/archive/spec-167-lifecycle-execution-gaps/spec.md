---
spec: spec-167
slug: lifecycle-execution-gaps
title: Sweep honesty + slot-clobber guard + single-PR consolidation
status: in-progress
effort: medium
summary: Make both sweep skills honest manual-only (rip phantom /ai-schedule scaffolding + 4 dead wrappers), add a deterministic advisory slot-clobber guard to /ai-brainstorm, and move /ai-pr consolidation pre-merge so it rides the feature PR (one PR, not two).
---

# Sweep honesty + slot-clobber guard + single-PR consolidation

## Summary

Two lifecycle-plumbing gaps, surfaced during a live session and confirmed
by read-only investigation:

**Problem 1 — the sweep skills lie about being scheduled.** Both
`/ai-session-watch-sweep` and `/ai-simplify-sweep` advertise a cron/`/ai-schedule`
activation path that does not exist. `/ai-schedule` is not a real skill. The four
wrapper scripts under `.ai-engineering/scripts/scheduled/` (`session-watch-sweep`
and `simplify-sweep`, each `.sh` + `.ps1`) emit `outcome=skipped
reason=requires_agent_review` and `exit 0` unconditionally — they do no work even
if cron'd, because the review is LLM-driven and has no headless `ai-eng`
subcommand. The SessionStart observation-nudge therefore fires every session,
forever, telling the operator to run "the scheduled sweep" that nothing
schedules. Net effect: observations accumulate and never consolidate, and the
documentation describes an automation that is not real.

**Problem 2 — `/ai-brainstorm` can silently clobber a live spec slot.** The
single-slot model keeps exactly one `spec.md`/`plan.md` buffer. The happy path is
already robust: `/ai-pr` Step 11 auto-consolidates on merge (archive + clear slot
to placeholder), so a new brainstorm normally starts clean. But in the edge case
where a prior spec is not yet consolidated (PR still open, or merged via the
GitHub web UI before `/ai-branch-cleanup` ran) and the operator starts a fresh
`/ai-brainstorm`, Step 6 overwrites `spec.md` with no warning. Recovery exists
(`git checkout HEAD -- spec.md plan.md`) but only if the operator notices.

This spec makes the sweeps tell the truth (honest manual-only) and hardens the
one brainstorm foot-gun with a deterministic, advisory slot check.

## Goals

- Remove every reference to a non-existent `/ai-schedule` activation and every
  "scheduled cadence" claim from both `ai-session-watch-sweep` and
  `ai-simplify-sweep` SKILL.md, plus the stray `/ai-schedule` reference in
  `ai-simplify`.
- Delete the four dead scheduled wrapper scripts and update every test/gate that
  asserts their existence, so the deletion lands green.
- Correct the SessionStart observation-nudge wording so it no longer claims a
  "scheduled" sweep exists — it should point only to the real manual trigger.
- Add a deterministic `slot_status`-style query to `spec_lifecycle.py` that reports
  whether the live slot is occupied by an un-shipped spec, and which one.
- Wire `/ai-brainstorm` to call that query at the start (a "Step -1") and, when the
  slot is occupied by an un-shipped spec, surface the slug + state and ask the
  operator to confirm overwrite (or consolidate first) — advisory, fail-open.
- Keep template-mirror parity for any edited `spec_lifecycle.py` (canonical +
  `src/ai_engineering/templates/...`), since no CI guard enforces it.
- Collapse the per-spec double-PR (feature PR + a `chore(spec-NNN): consolidate`
  follow-up) into a single PR by invoking consolidation on the feature branch
  before merge, so the archive + slot-clear + `_history.md` row + sidecar SHIPPED
  flip all ride the feature PR.

## Non-Goals

- Building a real autonomous scheduler / remote-agent engine for either sweep
  (explicitly rejected — see Decision D-167-01). The sweeps stay
  manual-invocation only.
- Escalating-nudge behavior (counting sessions, getting louder over time). The
  nudge stays a single truthful advisory line.
- A hard block on `/ai-brainstorm` when the slot is occupied. The guard is
  advisory and fail-open, never a gate.
- Changing the `mark_shipped` script internals or the
  `_shared/consolidate-spec.md` handler. Only the *timing/call-site* of
  consolidation inside `/ai-pr` moves (post-merge → pre-merge); what
  consolidation does is unchanged (D-167-07).
- Re-homing the manual/backstop consolidation surfaces.
  `/ai-branch-cleanup` Phase 5 `reconcile_merged` stays as the idempotent
  backstop, and `/ai-brainstorm --consolidate-spec` / `--consolidate-spec`
  stay as manual overrides.

## Decisions

### D-167-01 — Sweep execution model is honest manual-only

The sweeps remain manual-invocation skills. All scaffolding that implies
automatic/scheduled execution is removed rather than made real.

**Rationale**: The review step is LLM-driven with no headless `ai-eng` equivalent,
so a deterministic cron cannot perform it — proven by the wrapper scripts that can
only emit `skipped`. A real autonomous engine (remote-agent harness) is heavier
than the value and was explicitly rejected by the operator. The worst outcome is
the current one: scaffolding that *claims* automation that does not exist, so the
honest fix is to delete the claim, not to ignore it.

### D-167-02 — Fix the whole phantom-schedule pattern, both sweeps

The cleanup covers BOTH `ai-session-watch-sweep` and `ai-simplify-sweep` (their
SKILL.md scheduling sections, all four wrapper scripts, and the `ai-simplify`
`/ai-schedule` reference) in one pass.

**Rationale**: The lie is identical and systemic across both sweeps. Fixing only
the one the operator hit would leave a byte-for-byte copy of the same deception in
the sibling skill, violating surgical-consistency and guaranteeing a repeat
report. One pattern, one fix.

### D-167-03 — Delete dead wrapper scripts and follow the test/gate fallout

The four scripts under `.ai-engineering/scripts/scheduled/` are hard-deleted (no
backwards-compat shim per §13.3), and every referencing test/gate is updated in
the same change: `test_simplify_sweep_ps1_parity.py`,
`test_ai_simplify_sweep_skill.py`, `test_manifest.py`,
`test_skill_line_budget_post_cleanup.py`, `test_naming_lint.py`.

**Rationale**: The scripts do no work and exist only to be "scheduled" by a
mechanism that does not exist. Leaving them is keeping a prop. Deletion must be
green on landing, so the spec names the known consumers up front; `/ai-plan` owns
the exhaustive sweep for any others.

### D-167-04 — Correct the SessionStart observation-nudge wording

`runtime-observation-nudge.py` (and its template/byte-equivalent mirror, plus the
hooks-manifest sha re-pin) drops the "(or the scheduled /ai-session-watch-sweep)"
phrasing and points only to the real manual trigger.

**Rationale**: The nudge is the one honest, working automated component — it
should not itself repeat the "scheduled" lie. Editing a hook requires regenerating
`hooks-manifest.json` or the hook self-disables via integrity (known LESSONS
gotcha), so the spec flags it as a constraint, not an afterthought.

### D-167-05 — Deterministic, advisory slot-clobber guard in `/ai-brainstorm`

Add a `slot_status`-style read-only verb to `spec_lifecycle.py` returning whether
the live slot holds an un-shipped spec (and its slug/state). `/ai-brainstorm`
calls it before writing `spec.md`; if occupied, it surfaces the occupant and asks
the operator to confirm overwrite or run `--consolidate-spec` first. Fail-open: a
script error never blocks the brainstorm.

**Rationale**: A deterministic verb is CI-testable and robust where prose-only
instructions are skippable by the LLM. Advisory + fail-open preserves the
skill's fail-open principle everywhere else and avoids turning a rare,
recoverable edge case into a hard gate. It closes the one real foot-gun in the
single-slot model without touching the already-robust happy path.

### D-167-06 — Maintain `spec_lifecycle.py` template-mirror parity

Any edit to `.ai-engineering/scripts/spec_lifecycle.py` (the new verb) is copied
byte-identical to `src/ai_engineering/templates/.ai-engineering/scripts/spec_lifecycle.py`.

**Rationale**: No CI guard enforces parity for this script (only hooks +
session_bootstrap are guarded — known LESSONS gotcha). Without the mirror copy,
the new verb ships to existing repos but is missing from fresh installs, exactly
the spec-161 failure mode.

### D-167-07 — `/ai-pr` consolidates pre-merge, on the feature branch (one PR)

`/ai-pr` moves the consolidation call from post-merge (Step 11) to *after PR
creation but before merge*, running it on the feature branch: generate the PR
body from `spec.md`/`plan.md`, open the PR to obtain its number, then run
`mark_shipped <spec> <pr> <branch>` on the branch (archive + clear slot + append
`_history.md` + flip sidecar to SHIPPED), push the consolidation commit to the
same branch, and let auto-complete merge. The result is a single PR carrying both
the feature and its consolidation. The separate `chore(spec-NNN): consolidate`
PR is eliminated.

**Rationale**: Every artifact `mark_shipped` writes is git-tracked (`spec.md`,
`plan.md`, `archive/spec-NNN/`, `_history.md`, and the sidecar
`state/specs/spec-NNN.json` — confirmed tracked), so post-merge consolidation
*necessarily* needs its own PR against protected `main` (proven by #587/#584).
Folding it onto the feature branch is the only way to reach one PR. The design is
safe because tracked changes reach `main` only at merge: an abandoned PR never
ships the premature SHIPPED state (it dies on the branch and git-reverts on
checkout), so the "SHIPPED before merge" window is branch-local and self-healing.
Bonus: because consolidation now rides the PR itself, it lands regardless of
whether the PR is merged via `gh` CLI or the GitHub web UI — closing the
UI-merge backfill gap that `reconcile_merged` exists to paper over (reconcile
stays as a defense-in-depth no-op backstop).

## Risks

- **Test/gate fallout undercounted.** Deleting the wrapper scripts and trimming
  SKILL.md line counts may trip count gates beyond the five named
  (skill-line-budget, manifest totals, naming-lint, ps1-parity). *Mitigation:*
  `/ai-plan` runs `tests/unit/config` + `tests/unit/docs` + `tests/unit/scripts`
  + `ai-eng check` before push; spec names the known five as the floor.
- **Hook-integrity self-disable.** Editing `runtime-observation-nudge.py` without
  re-pinning `hooks-manifest.json` makes the hook exit non-blocking (scan off)
  until re-pinned. *Mitigation:* D-167-04 calls out the manifest regen + template
  mirror as required, in lockstep.
- **Template-mirror drift for `spec_lifecycle.py`.** New verb could ship to
  upgrades but miss fresh installs (no CI parity guard). *Mitigation:* D-167-06
  mandates the byte-identical copy; `/ai-plan` adds it as an explicit task.
- **Idle-slot intolerance.** The `slot_status` verb and any new gate must tolerate
  the `# No active spec` placeholder, or risk reding main on idle. *Mitigation:*
  reuse the existing `_IDLE_SLOT_PREFIX` recognition; test the idle case.
- **Advisory guard ignored.** Being fail-open + advisory, the operator can still
  confirm-through and clobber. *Accepted:* the goal is to surface the foot-gun, not
  prevent a deliberate overwrite; recovery (`git checkout HEAD`) remains.
- **Nudge still nags with no drainer.** Honest manual-only means the nudge keeps
  firing until a human runs the sweep. *Accepted:* that is the truthful state; the
  alternative (fake automation) is what this spec removes.
- **Feature PR now runs CI against an idle slot (D-167-07).** Today the feature PR
  carries `spec.md` *with content*; after pre-merge consolidation it carries the
  `# No active spec` placeholder, so the PR's own CI runs against an idle slot. Any
  gate that requires an active spec during feature CI would break. *Mitigation:*
  `/ai-plan` audits every spec.md-reading gate for idle tolerance (the
  `_IDLE_SLOT_PREFIX` consumers already tolerate it per prior fixes); add a CI case
  that a consolidated feature PR stays green.
- **PR-number ordering dance (D-167-07).** `mark_shipped` needs the PR number, which
  exists only after PR creation, so the flow is create-PR → consolidate → second
  push to the same branch. A failure between the two pushes leaves a created PR
  without its consolidation commit. *Mitigation:* make the consolidation push
  idempotent/retryable; `reconcile_merged` remains the backstop if it never lands.
- **Premature SHIPPED visible mid-flow (D-167-07).** Between branch consolidation and
  merge, local working tree + branch report SHIPPED. *Accepted:* branch-local only,
  self-heals on abandon via git; the slot-clobber guard (D-167-05) also reads this
  state correctly.
