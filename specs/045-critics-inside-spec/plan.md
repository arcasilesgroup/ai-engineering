# Plan: critics inside spec — 045 ordered execution

## Authority and atomicity gate

No implementation starts until the accountable role approves **this exact `spec.md` and
this exact `plan.md`**, recorded at their digests in their own `docs/adr/` record — the
series this spec restores, resuming after the gap since ADR 0026. One repository
writer, on one branch. Each task is one atomic commit; rollback for every task is
`git revert <commit>`. Tasks 1-7 are the coupled family of D-045-01/02/03/05: any one
of them reverted re-edits the others' pinned strings, so the family reverts as a
block, task by task in reverse order.

**This plan is not edited while it is executed.** The spec digest at approval time is
recorded in the approval ADR, not here.

## The order, and why

The council's one first step: *"write the five refusal fixtures before the template
ships the headings, so the first spec the new tool makes cannot pass a gate its own
printed rules do not enforce."* So the reader and its refusals land first (task 1),
the scoped no-authority with it (task 2), and only then does the template print the
headings (task 3) and the skills point at them (tasks 4-5). Policy and docs follow the
code that makes them true (tasks 6-7); the gate closes the family (task 8); the two
promotion-marked decisions become MADRs and the approval record cites them (task 9).

## What this plan is not doing, and why

- **No rewrite of written history.** The 15 `approval.md` dossiers, the 14
  `challenge.md` and 14 `council.md` and 12 `council.html` sidecars, and the nine
  specs whose option count is not three stay byte-exact (D-045-03, D-045-04;
  `CONSTITUTION.md` Never-list).
- **No grill-count counter in the template.** The critic step reads `## Grill`
  refusal states (empty, declared-with-prompt, malformed `ran:`) — a
  more-than-ten-questions refusal is not added; the cap stays a skill instruction
  with an escalation, per D-045-01.
- **No timing instrumentation.** `ran:` minutes are self-reported (D-045-05); the
  fork-timing instrument is its own change on the day the number must be true.
- **No section-number re-resolution.** `section()` gains no caller and no rename
  (the recorded risk; mitigation is written in the spec, not coded here).
- **No new verb, no new capability, no justfile step.** The `council` recipe keeps
  its name; `just check` stays sixteen steps.
- **No CI/CD or observability tasks.** This spec adds no deployable surface; the
  production-ready boxes stay unticked.

## Tasks

1. [ ] **The critic reader: dual glob, emptiness, declared-prompt, ran-grammar —
   with planted fixtures** —
   **file** `tests/council_counts.py` (+ its refusals in `tests/test_contracts.py`,
   `test_council_counts_recomputes_and_refuses_a_total_it_cannot_reproduce` extended).
   The reader counts `specs/*/council.md` (h2 `## The two counts`) and every
   `specs/*/spec.md` carrying a `## Council` section (h3 `### The two counts`) into one
   receipt; a declared `ran: round <n>, <ISO date> — <n> min` line is required for
   enforcement of the other three rules: present-but-empty bullet headings without a
   `none` line refuse, `TODO` prompt or HTML comment under a *declared* heading refuses,
   a malformed/missing `ran:` line in a section that has content refuses; a section
   with no `ran:` line at all reads "has not run" (today's absence-green). Fixtures:
   one planted file per refusal plus the clean control.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k
   council_counts && uv run python tests/council_counts.py`
   **rollback**: `git revert <commit>`.
   **done when**: the real mixed tree prints the historical `(8, 13)` for 044 plus the
   045 section's `(3, 12)` in one `RAN council=` line, exit 0, and each planted
   refusal exits non-zero naming its fixture.
2. [ ] **No-authority, scoped to section bodies** —
   **file** `tests/test_contracts.py` (`test_a_council_reviews_and_never_approves`).
   Keeps the file-wide rule over `specs/*/council.md`; gains a `## Council`-body-scoped
   pass over `specs/*/spec.md`. Whole-file prose must not fire: 036's register row and
   045's challenge answer stay green; a planted `## Council` body writing the
   specification as approved must refuse.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k
   council_reviews`
   **rollback**: `git revert <commit>`.
   **done when**: both directions (green on the tree, red on the plant) assert inside
   the one test and the real suite passes.
3. [ ] **The template prints the critics, and three options** —
   **file** `src/ai_engineering/spec.py` (`TEMPLATE`: insert `## Grill` and
   `## Council` with their prompts and the exact machine shape after `## Challenged
   once`; replace the two-option prompt with three numbered prompts) +
   `.agents/skills/ai-spec/SKILL.md` (steps 3/7 amended: exactly three options; fold
   grill and council into the named sections) + the three verbatim pins in
   `tests/test_contracts.py` (`AI_SPEC_SECTIONS`, governing-skill text) moved with it.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_mut_spec.py
   tests/test_contracts.py -k "template or governing or steps or sections"`
   **rollback**: `git revert <commit>`.
   **done when**: `ai-eng spec new` output for a probe slug carries both critic
   headings, `sed`-count of numbered options in the template is `3`, and the joint
   skill↔template test is green.
4. [ ] **ai-challenge becomes the grill** —
   **file** `.agents/skills/ai-challenge/SKILL.md` (+ `corpus.md` where routing text
   moves). ≤10 `### Q` entries per round, one at a time, command-and-verdict per
   question, empty-section and `nothing checkable failed` rules, `ran: round` lines,
   author folds into `## Grill`, no `challenge.md`, escalation and the two-rounds /
   digest / loopgate sentences the bounds test pins stay verbatim, `context: fork`
   and `background: false` unchanged.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_bounds.py
   tests/test_skill_sequence.py tests/test_contract_smells.py && uv run python
   tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: bounds tests green on the new text and `just skilleval` routes
   without a new dead end.
5. [ ] **ai-council runs once** —
   **file** `.agents/skills/ai-council/SKILL.md` (+ `corpus.md`). One pass: five named
   lenses + anonymous cross-read, author writes the verdict into `## Council`, the
   three headings and two counts survive as section shape, lens names never a tally,
   no `council.md`/`council.html`, the pinned sentences ("It is never asked which
   answer is best", "It may not write an approval", two rounds, digest, hand the page,
   loopgate) kept.
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_bounds.py
   tests/test_contracts.py -k "council_reviews or critic" && uv run python
   tests/skill_eval.py`
   **rollback**: `git revert <commit>`.
   **done when**: the 106-line file ships under the 80-line shape it was flagged
   over, and the no-granting boundary test is green against its text.
6. [ ] **Policy: the dead template holes** —
   **file** `policy/skill-map-exclusions.toml` (drop the `challenge.md`, `council.md`,
   `council.html` template-hole and nested-route rows) + the accepted pairs whose only
   reason was those skill mentions (`policy/skill-map-accepted.toml` row
   `ai-council/SKILL.md -> …/council.md`). Historical sidecar pairs stay: those files
   exist and their prose is history.
   **check**: `just map`
   **rollback**: `git revert <commit>`.
   **done when**: `just map` prints zero real-and-unaccepted and one fewer declared
   hole per removed row.
7. [ ] **Docs: the row and the record** —
   **file** `docs/tools.md` (`just council` description: sections and sidecars both;
   step list unchanged) + `CHANGELOG.md` (behaviour change for consumer repos: new
   specs carry `## Grill`/`## Council`, sidecars are not created, approval resumes in
   `docs/adr/`).
   **check**: `uv run --with pytest==9.1.1 pytest -q tests/test_contracts.py -k
   "tools or reference or changelog"`
   **rollback**: `git revert <commit>`.
   **done when**: the comparator test that pins the tools table to the justfile is
   green and the changelog names every shipped behaviour change.
8. [ ] **The gate, once, whole** —
   **file** none.
   **check**: `just check`
   **rollback**: fix forward; any red names its task and that task fixes in its own
   commit family.
   **done when**: the tail reads `0 failed` with the same passed/skipped shape the
   pre-change baseline printed plus the new fixtures' count, every step green
   including `council`, `map`, `skilleval`.
9. [ ] **Promotion and the approval record** —
   **file** `docs/adr/0028-…` (+ the two promoted records via `ai-eng decide`).
   Promote D-045-03 and D-045-04 (marked `[X]` in the spec); write the approval ADR
   at the exact spec and plan digests — the first digest approval since ADR 0026, in
   the home this spec restores.
   **check**: `uv run python -c "from pathlib import Path; from ai_engineering import
   madr; assert madr.validate(Path('.')).outcome == 'PASS'"`
   **rollback**: `git revert <commit>`.
   **done when**: `madr.validate` PASSes over `docs/adr/` with the three new records
   included, and each names the authority role and reference the conversation gave.
