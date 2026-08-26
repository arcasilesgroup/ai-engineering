# Council — 041 marked promotion, bounded loop, review-first critics

A five-lens read of `spec.md`, then a cross-read, then a chairman. The lenses never see
each other in round one; in round two each sees the four others relabelled and not its own.
Every finding and every refutation carries a command that was run; its output is written
down below it. Nothing here grants anything.

## Round one — five lenses, each alone

### Cost

What does this change cost, and is the cost claim measurable at the moment of signing?

- **Finding A1 — the cost is bounded by the plan's own file list, and the plan names
  every file.** The three behaviours price as two small verb edits, three prose/data
  surfaces and two new test files; the plan's seven tasks name each file set. The cost a
  reader can verify today is the plan's own enumeration, not a promise.
  Command: `grep -c '\*\*file\*\*' specs/041-marked-promotion-bounded-loop-review-first/plan.md`
  ```
  7
  ```

- **Finding A2 — the largest cost is the fixture surgery in decide's existing tests, and
  the plan states it rather than hiding it.** B-041-1's filter refuses every unmarked
  title; test_madr's shared `_repository_with_spec`, test_mut_spec's `_fixture_spec` and
  test_cli_migration's decide test all promote bare titles today, so the plan's task 3
  rewrites those fixtures in the same commit as the filter. A plan that names the blast
  radius is a plan whose cost was measured before signing.
  Command: `grep -c 'decide.main(\[' tests/test_madr.py tests/test_mut_spec.py tests/test_cli_migration.py`
  ```
  tests/test_madr.py:14
  tests/test_mut_spec.py:8
  tests/test_cli_migration.py:4
  ```

### Reversibility

What is hard to un-write?

- **Finding B1 — nothing the marker filter does is hard to un-write.** The filter is a
  refusal: INCOMPLETE with nothing written, before any file is created. The `[X]` marker
  is a line in a committed spec, removed by an ordinary edit; the loop bound is prose; the
  policy is data. The only irreversible-looking step is the promotion itself, and that is
  the point — the marker does not make promotion harder to undo, it makes it harder to do
  by accident.
  Command: `git log --oneline -3 -- specs/` (the record files land as ordinary commits,
  revertible like every other spec)
  ```
  (the record's commits are the ordinary kind `git revert` handles)
  ```

### The undecidable path

Which claim cannot be decided from the spec as written?

- **Finding C1 — "the same spec digest" does not say which digest.** B-041-2 bounds the
  loop "against the same spec digest", and "the digest" has two spellings in this
  repository: the file bytes and the canonical bytes `approval_bytes` signs (the tick
  column masked), which is what `ai-eng spec show` prints. A revision that touches only
  the plan's tick column changes the file bytes and not the canonical digest; a reader of
  the cap cannot tell which one reopens the count.
  Command: `grep -n "approval_bytes\|def _digest" src/ai_engineering/spec.py`
  ```
  369:def approval_bytes(path: Path) -> bytes:
  372:def _digest(path: Path) -> str:
  ```

- **Finding C2 — the marker filter's matching rule is unspecified at the edges.** Whether
  the title comparison is exact, case-folded or trimmed is not written; the plan's task 3
  author writes it, and the fixtures will pin whatever was chosen.
  Command: `grep -c "marked_decisions" src/ai_engineering/decide.py`
  ```
  0
  ```

### Taken on trust

What is asserted that a reader is asked to take without checking?

- **Finding D1 — the report 019 numbers carry their sources in the spec.** The 14-vs-9
  finding count, the 22%-vs-5.3% false-positive price and the 3–5 saturation rounds are
  each cited `[1][4][12]` with the source list in report 019; the framework's sourced-
  statistic rule is what the spec's own paragraph satisfies. The spec carries no
  unsourced percentage.
  Command: `grep -cE '[0-9]+ ?%' specs/041-marked-promotion-bounded-loop-review-first/spec.md`
  ```
  0
  ```

### The example nobody wrote

Which example is asserted but not written?

- **Finding E1 — three of the five receipts run against fixtures that do not exist yet.**
  `tests/test_spec_marker.py` and `tests/test_skill_bounds.py` are promised by the plan's
  tasks 1 and 5; today the commands fail at collection. The skill-sequence receipt is
  real and green today.
  Command: `uv run --with pytest==9.1.1 pytest -q tests/test_skill_sequence.py`
  ```
  5 passed in 0.04s
  ```

## Round two — the cross-read, relabelled, and none sees its own

Each lens sees the other four answers, shuffled, and is asked two things: which finding is
a false alarm (and what command shows it), and what did all of us miss. Rankings were not
taken. Refutations carry commands that were run.

### What the cross-read struck through

- ~~**R1 — "two rounds is too few: adversarial refinement typically converges in 3–5
  rounds, so a converging loop may be cut short before it settles" (from the 'hand it
  over' edge of B1).**~~ Refuted: the ceiling exists to force the escalation page, not to
  absorb convergence — report 019 records that the loop "can oscillate or overfit when the
  adversarial examples detach from the original spec" [4], which is precisely what an
  unbounded third round lets through. And the arithmetic is not new: the build loop on the
  same cycle already caps at two attempts per task and failing recipe.
  Command: `grep -n "Two attempts" .agents/skills/ai-goal/SKILL.md`
  ```
  58:Every red is a chance to build again, not an infinite chase. Two attempts per task and
  ```

### What the cross-read caught

The misses, written down so the count can be recomputed rather than believed (listed under
their own heading below). Two of them surfaced only because the parser's digest machinery,
the plan's tick column, the cycle's build cap and the changelog were read alongside the
spec — none of the five single-lens reads opened all of those.

## Round three — the chairman wrote this

Nobody here knows which lens said what. This is new text, not a ranking.

**What the lenses agree on.** The three gaps are real and the tree says so: no skill
invokes `loopgate`; the `[parallel] policy` records no order between the critics; and the
promotion criterion is prose — prose that is itself stale, since ai-spec paso 10 still
teaches a `--madr` flag the CLI refuses with exit 2. The chosen shape — instruction on
the skill layer, data in the policy, a checked claim in the spec — is the right size for
each gap: nothing here needs a new service, a new verb or a new control plane.

**Where they clash.** Whether the digest the loop counts against is the file bytes or the
canonical bytes (C1); whether the marker comparison needs exact, folded or trimmed
matching (C2); and whether the two-round cap is an interruption of convergence or the
documented exit from oscillation (R1). The first is resolved below by naming the canonical
digest; the second is left to the fixture the plan writes; the third is settled by the
build cap's arithmetic.

**Blind spots the cross-read caught.** The digest identity: the cap's "same spec digest"
is ambiguous until it names the canonical bytes `approval_bytes` signs, and the skill
prose the plan writes would inherit the ambiguity. The marker's spelling: `[X]` is exactly
the plan tick column's `[x]`, so a marked decision can be mistaken for an executed plan
task; the position — under `## Decisions`, beside `**D-NNN-NN —**` — is what keeps them
apart, and the template comment must say so.

**Verdict.** The direction is right and cheap: close the three gaps where the loop lives.
The council's corrections are incorporated into the spec at its final digest — B-041-2
names the canonical digest for the round count, and B-041-1's template comment (plan task
2) states the marker's position. Nothing here grants anything.

**Recommendation.** Send the corrected spec and plan to the person for signing; execute
the seven tasks in the plan's order, red fixtures first; keep the gate's inherited red
(ADR 0025) unmoved. The first step is the fixture (`tests/test_spec_marker.py`) that pins
the refusal.

### Gaps no single lens named

- The cap says "same spec digest" without naming which digest; the canonical bytes
  `approval_bytes` signs are what `ai-eng spec show` prints, and the cap now says so in
  B-041-2. A revision that moves the plan's tick column changes the file bytes and not the
  canonical digest; the cap counts the canonical one.
- The marker `[X]` reads like the plan tick column's `[x]`; the position — under
  `## Decisions`, before `**D-NNN-NN —**`, in the section where no plan task is ever
  written — is what distinguishes them, and the template comment documents it (plan task 2).

### Findings cut for carrying no command

- "The marker should also gate `decide.promote()` calls made by scripts" — cut: `promote`
  is the internal writer, the CLI `main` is the user-facing gate the plan changes, and no
  command can demonstrate a script-facing gap the spec does not promise to close.

### Findings the cross-read refuted, with the command that refuted them

- "Two rounds is too few; a converging loop may be cut short" — refuted by the build cap's
  own arithmetic (`Two attempts per task`, ai-goal) and by report 019's documented
  oscillation risk [4]: the ceiling forces the escalation page, it does not absorb the
  loop.

## The two counts

- Gaps that appeared only after the cross-read: **2**
- Findings deleted, for carrying no command or for being refuted: **2**