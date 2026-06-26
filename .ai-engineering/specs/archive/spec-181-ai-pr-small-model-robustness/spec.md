---
spec: spec-181
title: ai-pr small-model robustness
status: in-progress
effort: small
summary: "Harden ai-pr/SKILL.md for small (sonnet-tier) models: add a terminal self-verify block that fails loud on skipped steps, collapse the duplicated pre-push gate, drop the dead pointer step, and hoist scattered conditionals into one up-front decision preamble. Line-neutral, SKILL.md-only."
---

# ai-pr small-model robustness

## Summary

`/ai-pr` is tagged `model_tier: sonnet` — it is meant to run on a smaller
model than Opus 4.8 — yet its orchestration layer is narrated prose: a 0→16
imperative chain, a 3-lane concurrent dispatch, conditionals scattered across
six steps, and an unbounded watch loop. The load-bearing *mutations* are
already scripted (`branch_slug.py`, `commit_compose.py`, `pr_body_compose.py`,
`spec_lifecycle.py mark_shipped`, `ai-eng gate run`), so the scripts are not
the problem — the **sequencing prose is**. The failure is documented:
`LESSONS.md:28` records PR #190 (spec-056) merging with `spec.md`/`plan.md`
uncleaned because the consolidation steps were "completely skipped". A smaller
model has no terminal check that every step ran, trips over a pre-push gate
that is fully described twice (Step 7 Lane 3 and Step 9), reads an action-free
pointer step (Step 8 → "see Step 2"), and must track `--draft` / existing-PR /
placeholder-spec state across the whole chain. This spec hardens the prose
layer for small-model reliability without changing any behavior, script, or
the watch handler.

## Goals

- A **terminal self-verify block** is the final Process step: it re-reads
  `spec.md`/`plan.md` and asserts they are placeholders post-consolidation,
  asserts docs were staged, the PR exists, and the `_history.md` row was
  appended — failing loud (STOP) on any missing post-condition. Draft runs
  gate the consolidation/placeholder assertions off.
- The pre-push gate is described **exactly once**; the duplicate full
  description is collapsed to a concurrent-dispatch pointer. The externally
  cited `Step 9` label is preserved or every referrer is updated in lockstep.
- No step number maps to "no action" — the action-free pointer step is removed.
- A single **decision preamble** resolves draft? / existing-PR? /
  placeholder-spec? once, before the linear steps.
- `SKILL.md` stays ≤180 lines and the change is net line-neutral or negative
  (the dedup funds the additions); `test_skill_line_budget` stays green.
- Cross-IDE mirrors (`.codex/`, `.agents/`, `.github/`) are regenerated so
  surface parity holds.

## Non-Goals

- No `ai-eng pr run` driver or any new CLI command (explicitly dropped this
  session — the orchestration stays model-driven).
- No change to `handlers/watch.md` procedure or its escalation/cap logic.
- No change to the deterministic Python scripts.
- No change to the canonical chain or to the standalone `/ai-commit` skill.
- No new `/ai-pr` behavior — this is a legibility + skip-resistance restructure
  only, observably equivalent on an Opus-tier model.

## Decisions

### D-181-01 — Terminal self-verify block as the final Process step

Append a block that, after the watch loop / PR creation, re-reads `spec.md` +
`plan.md` and asserts placeholder content (non-draft runs), asserts the docs
files were staged, the PR number exists, and the `_history.md` row for
`spec-NNN` is present; any failed assertion STOPs loud.

*Rationale*: PR #190 skipped consolidation silently (`LESSONS.md:28`).
Converting "did every step run?" into a checkable post-condition is the only
mechanism that catches a skip *after the fact* — the single highest-ROI fix
for small-model skip-resistance.

### D-181-02 — Describe the pre-push gate exactly once; preserve the cited `Step 9` label

Collapse the Step 7 Lane 3 ↔ Step 9 duplication so the gate (`ai-eng gate run
--cache-aware --json --mode=local`) has one canonical full description and one
concurrent-dispatch pointer. Keep the `Step 9` anchor that
`.claude/skills/ai-build/handlers/deliver.md:37,120` cites ("Step 9 via
ai-pr"), or update both referrers in the same change.

*Rationale*: two full descriptions of the same gate make a smaller model run
it twice or stall reconciling the duplicate. `Step 9` is load-bearing across
skills, so it cannot be silently deleted — the dedup must keep the cross-skill
contract intact.

### D-181-03 — Remove the action-free pointer step

The current Step 8 ("Instinct consolidation — see Step 2") carries no action;
fold its note into Step 2 and eliminate the standalone heading so each step
number maps to exactly one action.

*Rationale*: a number that exists only to point elsewhere is pure tracking
overhead for a small model and inflates the apparent step count.

### D-181-04 — Add a decision preamble before Step 0

A short up-front block resolves the three branch conditions once: is this
`--draft`? does a PR already exist for this branch? is `spec.md` a placeholder?
Downstream steps reference the resolved flags instead of re-deciding inline.

*Rationale*: conditionals scattered across six steps force cross-step stateful
tracking that smaller models lose; resolving once up front makes the remaining
chain linear and side-effect-predictable.

### D-181-05 — SKILL.md-only, line-neutral within the ≤180 budget

The dedup (D-181-02/03) frees the lines the additions (D-181-01/04) spend; the
net diff must not exceed the 180-line `SKILL.md` cap or the combined ceiling in
`tests/unit/test_skill_line_budget.py`.

*Rationale*: the line budget is a hard CI gate; a restructure that grows the
file would trade one failure mode (skips) for another (blocked CI), and smaller
models do not read *more* prose more faithfully — terser wins.

### D-181-06 — No behavioral / script / handler change

The edit is confined to `.claude/skills/ai-pr/SKILL.md` (plus its regenerated
mirrors).

*Rationale*: the documented failures are orchestration-prose skips and
mis-sequencing, not script bugs (the scripts work). Fixing the prose layer is
the root-cause fix; touching scripts or the watch handler would be an
unjustified drive-by.

## Risks

- **Cross-skill step-label coupling.** `ai-build/handlers/deliver.md:37,120`
  cite ai-pr `Step 9` as the pre-push gate; a naive renumber breaks them.
  *Mitigation:* D-181-02 preserves the `Step 9` label, or updates both
  referrers in the same PR; grep `Step 9` / `14b` / step refs across `.claude`
  before editing. (`Step 14b` is the D-167-07 consolidation anchor — keep its
  label stable too.)
- **Line-budget overrun.** Self-verify + preamble could push `SKILL.md` past
  180 lines. *Mitigation:* land the dedup first, measure `wc -l`, and confirm
  both the per-file and combined `test_skill_line_budget` ceilings.
- **Self-verify false-loud on legitimate skip states.** A `--draft` run
  intentionally skips consolidation and leaves the slot occupied.
  *Mitigation:* the preamble's draft flag gates which assertions run, so the
  block only fails loud on genuinely-skipped steps.
- **Dogfood wrinkle.** This spec ships via `/ai-pr` itself, exercising the
  very steps being rewritten (`observations.yml` pattern: "a spec that changes
  the delivery pipeline dogfoods on its own /ai-pr"). *Mitigation:* budget for
  one in-loop fix on its own PR.
- **Mirror parity.** Editing a `.claude/skills` file requires regenerating the
  `.codex/` / `.agents/` / `.github/` mirrors (Surface Axiom A1).
  *Mitigation:* run the mirror sync and confirm `test_surface_parity` green.

## References

- doc: .claude/skills/ai-pr/SKILL.md (target)
- doc: .claude/skills/ai-pr/handlers/watch.md (out of scope, referenced)
- doc: .ai-engineering/LESSONS.md (PR #190 skip evidence, line 28)
- doc: .claude/skills/ai-build/handlers/deliver.md (Step 9 cross-reference)
- work-item: spec-167 (D-167-07 Step 14b consolidation anchor)
