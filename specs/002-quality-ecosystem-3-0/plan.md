---
id: "002"
slug: quality-ecosystem-3-0
---

# Plan — the order the gates go red in

Ordered so the first failing check appears at task 1. Every task below already fails today;
none of them is a check that has to wait for something else to be built before it can go
red. The deletion comes first because it is the payment, and because the gate in task 5
would otherwise be permanently red on a spec seeded from a work item.

**This plan is rebased onto `7df21510..31fa6cf4`, six commits that raised the ceiling to
5,764 for four controls that were reporting green while doing nothing.** The arithmetic here
is **minus eighteen**, and that delta is the claim. At that head it closes at 5,746; a
coverage push is expected to move the count again before this lands, so task 7 recomputes
the absolute rather than reading it out of this file.

Every finding this plan rests on was re-checked at that head rather than assumed to have
survived, and every one does: `seed()` and its `subprocess` import are still there, `accept`
still writes three fallback markers, assertion 19 still reads only unticked boxes, assertion
6 still returns ok on an absent chain, the sentence in `/ai-ship` is still there, and the
three unbackticked ticked boxes in spec 001 are unchanged. `doctor` still carries twenty-one
assertions and assertion 5 is present and unchanged in shape, so task 7 uses it.

One correction to an earlier draft of this header, which asserted that
`specs/003-guards-that-never-fired` had landed and that this plan was rebased onto it.
It has not. Verified: `git log --name-only` across those six commits touches exactly one
file under `specs/`, and it is `001`; `git ls-files specs/` lists only `001`; `002`, `003`
and `004` are all untracked. `003` is an uncommitted draft by a third session on this
worktree, none of whose eleven decisions is a commitment anyone has made, and this plan
depends on none of them. It was written here as fact on the strength of a plausible
attribution, which is the failure this whole spec is about, committed by its own author
while writing it down.

## 1. Delete the work-item paste

- **file** `src/ai_engineering/spec.py` · **check**
  `! grep -q "def seed" src/ai_engineering/spec.py && ! grep -q "^import subprocess" src/ai_engineering/spec.py` ·
  **rollback** `git revert` the commit; the flag and the frontmatter are untouched either
  way · **done when** `seed()`, its call, the truncated-body paste and the now-unused
  `subprocess` import are gone, `ai-eng spec new x --ref owner/repo#45` still writes
  `ref: "owner/repo#45"` into the frontmatter, and nothing writes an issue body into
  `## Context and problem`. Measured on a copy: **minus thirty-one lines**, 172 to 141, the
  result parses, and no reference to `seed`, `subprocess` or `body` survives. The estimate
  this spec first carried was twenty-nine; it was never counted.
- **file** `.agents/skills/ai-spec/SKILL.md` · **check**
  `! grep -q "seed" .agents/skills/ai-spec/SKILL.md` · **rollback** restore the two lines ·
  **done when** line 7 no longer says the skill seeds itself from a work item and step 2 no
  longer says `--ref` seeds the problem, because documentation that advertises deleted
  behaviour is worse than none. Same commit as the deletion, never a follow-up.

## 2. An acceptance cannot be written unsigned

- **file** `src/ai_engineering/accept.py` · **check** a new case in
  `tests/test_contracts.py`: `accept.main(["--finding", "x", "--expires", "2027-01-01"])`
  exits non-zero and writes nothing. It returns 0 today and writes an unnamed person into
  the record · **rollback** `git revert`; no state migrates, because the record is markdown
  in the user's own repository · **done when** `--by` and `--justification` are required and
  **all three** fallback strings are deleted, including `--follow-up`'s. The third one is
  not optional: it writes a marker when the flag is omitted, so leaving it would make every
  acceptance without a follow-up red its own spec permanently under task 6. An absent
  follow-up becomes an empty field. Measured: this change is **zero net lines** — three
  lines shorten, two flags change in place, and the file stays at 122 lines and parses.
- **file** the changelog · **check** `grep -q "accept" CHANGELOG.md` · **rollback** delete
  the entry · **done when** it is written as a breaking change, in the words somebody
  upgrading would search for. Two required flags on a released verb is a break and is said
  so; there is no shim and no deprecation period.

## 3. Assertion 6 stops greening on nothing

- **file** `src/ai_engineering/doctor.py` · **check** a new case in
  `tests/test_contracts.py` that points `chain_path` at a file which has never existed and
  asserts `Undecidable` is raised. It returns `None` today, which prints `ok` ·
  **rollback** restore the `return None` branch · **done when** an absent chain raises
  `Undecidable("nothing has been written to this chain yet")` instead of passing, the
  question mark appears in the doctor output, and the run still exits 0 because not
  evaluated is not a failure.

## 4. The three boxes in spec 001 are repaired

- **file** `specs/001-v1-from-scratch/spec.md` · **check** `ai-eng doctor` assertion 19,
  which must go **FAIL** on the unmodified file the moment task 5 lands, and `ok` after
  this one · **rollback** restore the three lines · **done when** the CI/CD, Logs and
  External check boxes each name a command or a file in backticks, and any box that
  genuinely cannot be proved says `not applicable` and why, the way the Traces box already
  does. This task is free: `specs/` is outside `repo_lines`. It is also the evidence that
  task 5 works, so it lands in the same commit and its diff is the proof.

## 5. A ticked box must name a command

- **file** `src/ai_engineering/doctor.py` · **check** `ai-eng doctor` on the tree at
  `HEAD` before task 4 is applied: assertion 19 must print `FAIL` and name
  `001-v1-from-scratch`. Then, with task 4 applied, `ok` · **rollback** revert the added
  condition; the assertion returns to reading unticked boxes only · **done when** the scan
  is confined to the text after `## Production-ready`, a ticked line there with no
  backticked span and without the words `not applicable` fails, and the assertion's title
  says what the code observes — a box ticked with no command — rather than claiming the
  work is finished, which it cannot see.
- **file** `.agents/skills/ai-ship/SKILL.md` · **check**
  `! grep -q "A box ticked without a command" .agents/skills/ai-ship/SKILL.md` ·
  **rollback** restore the sentence · **done when** the prose that asked for the command is
  gone and the gate asks instead. Rule 12's second half: the prompt goes in the same commit
  the script arrives in, or the repository now has two of them.

## 6. A shipped spec may not contain a TODO marker

- **file** `src/ai_engineering/doctor.py` · **check** two cases in
  `tests/test_contracts.py`, and the second is the one that matters: a fixture spec at
  `status: shipped` carrying an unfilled marker at the start of a line must FAIL, and a
  fixture spec quoting the same string inline, inside backticks, must PASS · **rollback**
  revert the added condition · **done when** the condition sits inside assertion 19's
  existing loop and is anchored — `^\s*(?:[-*]|\d+\.)?\s*TODO:` — rather than copying
  assertion 4's unanchored `"TODO:" in text`.
- **why the second test exists, measured before the gate was written.** The unanchored form
  has exactly one red across all four specs in this tree, and it is `specs/002` — the
  document proposing it, which quotes the literal strings three times as evidence. The
  anchored form has four reds on the template `ai-eng spec new` writes, which is the whole
  target, and zero across all four specs. The precedent is already here:
  `test_the_ioc_catalogue_leaves_ordinary_technical_prose_alone` exists because a pattern
  that fires on ordinary prose is a pattern that gets switched off.

## 7. The ceiling moves to what was measured

- **do not read the target number out of the spec.** Recompute it: `contract.repo_lines()`
  at the head this lands on, minus eighteen. The absolute has moved twice already while this
  was being written, and a coverage push is expected to move it again.
- **file** `src/ai_engineering/contract.py` · **check** `pytest -k line_ceiling` and
  `ai-eng doctor` assertion 5, which exists and is unchanged at `31fa6cf4` · **rollback**
  restore the previous number in a commit that says why · **done when** `REPO_CEILING` is
  the number this branch actually measures after tasks 1 to 6, its comment records this
  move the way it records the ones before it, and the commit message carries the
  arithmetic. **This task needs the operator's answer first**, and the question is not
  whether to raise: this change nets minus eighteen. It is whether the constant follows the
  count down or stays where it is and banks the difference. The recommendation is to follow
  it down, and spec 003 reaches the same conclusion from the other direction — it raises
  for work that needs the room, then closes at what landed, because slack under a ceiling
  is how a ceiling stops meaning anything.

## Not doing

- **No CI/CD task and no observability task.** The eight boxes make both mandatory when a
  spec adds something that gets a web address. This one adds no service, no endpoint and no
  deployment: it changes two assertions, one verb and deletes a function inside a package
  that already builds, lints, tests and scans on every push. Saying so here is the point —
  a plan that carries the two tasks anyway would be claiming a deployment that does not
  exist.
- **No spec section for how we will know the work was right.** This is the largest gap in
  the framework and it is named in the spec rather than closed here. Every gate proposed
  for it either reds only on absence, which the deck's own slide condemns, or has its
  subject deleted by `.agents/skills/ai-spec/SKILL.md`, which tells the model to remove a
  section with nothing real to say. Rule 12 is explicit about what happens next: it stays a
  prompt and the reason is written down, or it becomes its own spec with a shape gate whose
  weakness is stated before it is approved. It does not get smuggled in here.
- **Nothing in `solution-intents` or `si-hub`.** That question is `specs/004-solution-intent-home`
  and its own plan. Its decision changes no line of this framework, so bundling it here would
  put two changes in one spec and give this plan a task nobody in this repository can run.
- **Nothing about `AGENTS.md`.** The stale ceiling line was found while writing this and is
  already fixed, in `7df21510`: the file now names `contract.REPO_CEILING`,
  `tests/test_contracts.DOCTRINE_CEILING` and `contract.CEILING`, and quotes no value.
  Verified at that head, not taken on report.
