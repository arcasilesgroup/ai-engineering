# Plan · Handshake intake mechanisms (spec 048)

Tasks are commits, in order. `[ ]` means no command has sealed these bytes yet;
`ai-eng spec show 048 --task <n> --tick` fills a box by running its check. Each check
names exactly one command `--tick` can execute; the judgement that rides beside it is
prose, marked as such.

1. [x] <!--t:5f3aebc369fd--> **Land the intake mechanisms: skill body, stored pins, reference file** —
   **file**: `.agents/skills/ai-spec/SKILL.md` (step 0 rewritten),
   `tests/test_contracts.py` (both stored pins moved to the new bytes),
   `.agents/skills/ai-spec/references/intake.md` (new; the mechanism detail written
   in this tree's voice, D-048-03).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k "fog or ai_spec or pinned_whole"`
   — exits 0 with `20 passed`; the selection covers the fog ratchet, both stored pins
   and the whole-file digests, so a stale pin or a crossed ceiling both go red in the
   one command `--tick` executes.
   **rollback**: `git revert` of this commit; the old step-0 text, the old digest and
   the absent reference all return together.
   **done when**: the three files are in one commit and the tick seals this line.

2. [x] <!--t:129c5e165dc7--> **De-dangle the intake template** —
   **file**: `specs/new-goal-template.md` (the dead callable `validate_intake` named
   as the checker is replaced by the live step-0 prose; grill Q5's dangling reference).
   **check**: `uv run python -c "raise SystemExit('still dangling' if 'validate_intake' in open('specs/new-goal-template.md').read() else 0)"`
   — exits 0 once the pointer is gone and prints `still dangling` today, which is the
   failure-before-fix shape. The word lives on in specs/037's own record and in the
   reports; those are history and are not rewritten.
   **rollback**: `git revert`; the pointer to the deleted module returns, and so does
   the lie.
   **done when**: the check runs green and the tick seals this line.

3. [x] <!--t:dc06ee032ea3--> **Record the critics' verdicts in the spec** —
   **file**: `specs/048-handshake-intake-mechanisms/spec.md` (fold: grill round 1 of
   ten `### Q`, council round 1 with the recompute-refused counts, both attacked sets
   revised in place; D-048-04 added for the unattended branch the council forced).
   **check**: `uv run python tests/council_counts.py` — exits 0 with 048 printing
   `4 found only by the cross-read, 3 deleted` and `grill: 10 questions`.
   **rollback**: `git revert`; the `TODO` prompts return and the critic step reads
   both rounds as not run, which is the pre-state, not a loss.
   **done when**: `## Grill` and `## Council` carry `ran:` declarations, no template
   prompt survives inside them, and the counts script agrees with the bullets.

4. [ ] **Rebuild the derived page and the changelog at the shipped bytes** —
   **file**: `docs/solution-intent.html` (regenerated, never hand-edited),
   `CHANGELOG.md` (the entry naming what moved and that no new skill was added).
   **check**: `just check` — exits 0; the intent-page digest guard fails on stale
   bytes, so this task cannot pass before 1-3 land, and the gate's green is the whole
   answer.
   **rollback**: `git revert`; the page re-derives from the previous tree on the next
   gate run.
   **done when**: the gate's own `intent-page` step is green in the same run.

## What this plan deliberately does not do

- No new skill (`ai-handshake`), per D-048-01; the spec's options carry that kill.
- No mechanism of `validate_intake` — the rebuild must name its caller in the same
  commit and that is a later spec's problem, recorded as a risk (grill Q5).
- No touch to `AGENTS.md`, `CONSTITUTION.md`, or any other spec's record.
- No vendoring of `~/Downloads/handshake/SKILL.md` (D-048-03): the reference file was
  written from the spec's decisions, in this tree's voice, with the example pair
  rebuilt on a different domain.
- No CI/CD or observability task: this changes skill prose, one reference and test
  pins; it gets no URL (rule 11 is untouched, not skipped).
