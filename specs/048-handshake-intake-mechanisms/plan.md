# Plan · Handshake intake mechanisms (spec 048)

Tasks are commits, in order. `[ ]` means no command has sealed these bytes yet;
`ai-eng spec show 048 --task <n> --tick` fills a box by running its check.

1. [ ] **Land the intake mechanisms: skill body, stored pins, reference file** —
   **file**: `.agents/skills/ai-spec/SKILL.md` (step 0 rewritten, one swap),
   `tests/test_contracts.py` (both stored pins moved to the new bytes),
   `.agents/skills/ai-spec/references/intake.md` (new; the mechanism detail written
   in this tree's voice, D-048-03).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k "fog
   or ai_spec or pinned_whole"` exits 0 with `20 passed`, and
   `uv run python -c "import sys;sys.path.insert(0,'src');from ai_engineering import
   contract;print(contract.fog(contract.prose(open('.agents/skills/ai-spec/SKILL.md').read())))"`
   prints a number ≤ 11.03. A stale pin or a crossed ceiling both go red here.
   **rollback**: `git revert` of this commit; the old step-0 text, the old digest and
   the absent reference all return together.
   **done when**: the three files are in one commit and the check's output is pasted
   into the task's tick receipt.

2. [ ] **De-dangle the intake template** —
   **file**: `specs/new-goal-template.md` (the dead callable `validate_intake` named
   as the checker is replaced by the live step-0 prose; grill Q5's found dangling
   reference).
   **check**: `git show HEAD:specs/new-goal-template.md | grep -c validate_intake`
   prints `1` today (red until this commit lands) and
   `grep -c validate_intake specs/new-goal-template.md` prints `0` after.
   **rollback**: `git revert`; the pointer to the deleted module returns, and so does
   the lie.
   **done when**: no tracked file in the tree names `validate_intake` as live
   (`grep -rn validate_intake --include="*.md" . | grep -v specs/03 | grep -v
   .ai/reports` is empty — 037's own record and report 025 keep their history).

3. [ ] **Record the critics' verdicts in the spec** —
   **file**: `specs/048-handshake-intake-mechanisms/spec.md` (fold: grill round 1 of
   ten `### Q`, council round 1 with the recompute-refused counts, both attacked sets
   revised in place; D-048-04 added for the unattended branch the council forced).
   **check**: `uv run python tests/council_counts.py` exits 0 with 048 printing
   `4 found only by the cross-read, 3 deleted` and `grill: 10 questions`.
   **rollback**: `git revert`; the `TODO` prompts return and the critic step reads
   both rounds as not run, which is the pre-state, not a loss.
   **done when**: `## Grill` and `## Council` carry `ran:` declarations and no
   template prompt survives inside them.

4. [ ] **Rebuild the derived page and the changelog at the shipped bytes** —
   **file**: `docs/solution-intent.html` (regenerated, never hand-edited),
   `CHANGELOG.md` (the entry naming what moved and that no new skill was added).
   **check**: `just check` exits 0 — the intent-page digest guard fails on stale
   bytes, so this task cannot pass before 1-3 land.
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
