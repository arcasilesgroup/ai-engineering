---
id: "005"
slug: init-says-what-it-did
---

# Plan — the false statements first, in the order that keeps every commit green

## What landed — measured, 2026-08-09

Every figure below was a prediction. These are the counts, read from `git diff --numstat`
per commit over the files `contract.repo_lines` counts, in the order the commits landed.

| | predicted | landed |
|---|---|---|
| 0. 003's ceiling arithmetic, restated (the precondition) | — | +35 |
| 1. `existing()` before the writes, strict `xfail` deleted | −5 | −2 |
| 2. one parser for the typed reply and `--overwrite` | +4 | +57 |
| 3. the `doctor` check nobody wrote | 0 | +11 |
| 4. a backup two overwrites in one second cannot collide on | +1 | +15 |
| 5. the dry run stops reporting writes | +3 | +37 |
| 6. the pin gets the copy the four root files get | +6 | +45 |
| 8. skills linked only into the roots that were found | +7 | +27 |
| 7. a surface stops detecting itself | +9 | +44 |
| 9. three assertions stop passing on an empty set | +8 | +62 |
| 10. every repairable failure names its cure | +6 | +60 |
| 11. the gitleaks wall, named when it is created | +7 | +28 |
| 12. the offer in a directory that is not a repository | +8 | +40 |
| 13. the screen that says it is finished | +15 | +64 |
| 10b. the missing dispatcher stops being handed a cure that would not work | — | +16 |
| 15. the tests the mutation floor said were missing | — | +116 |
| 14. this table and the ceiling comment | — | +15 |
| **total** | **+69** | **+667** |

`REPO_CEILING` closes at **12,686**, which is 12,017 plus that total, with no slack. The
estimate was out by nearly a factor of ten and the reason is one thing, not thirteen: every
prediction counted the product line and none of them counted the test that holds it. 466 of
the 667 are test lines against 154 of product — three to one inside this branch, on a
repository whose gate caps the whole tree at two to one, which is exactly why that gate is
over the tree and not over a branch. The remaining 35 are `package.json` and
`tsconfig.json`; they are the operator's in-flight TypeScript lane and they are in this
branch because the first commit was made against an index that already held them. They are
named in the ceiling comment rather than absorbed into it.

Two tasks in that table were not in the plan, and both were found by a gate rather than by
reading. **10b** is a claim the cure commit itself introduced: it attached
`ai-eng init --global` to the whole of assertion 2, and one of the two things that
assertion reports is a missing dispatcher, which no verb here restores. **15** is the
mutation floor. `just mutate` came out at 88% against a floor of 89% — 3,394 mutants, 387
survivors, seventy of them in `init.py` — and what it had caught was the two screens this
spec adds, both asserted by fragment, so every line the fragment did not name could be
emptied or upper-cased with the suite still green. The plan predicted that the floor would
be the second binding gate and that it had no margin. It was, and it did.

**Row 6 no longer describes the tree.** It landed as a dated backup and a line of output on
every run, and spec 007 reversed that half: `init` writes `.ai/config.toml` when it is
absent and never rewrites it, because `ai-eng update` is the verb that changes governance
and it keeps its three consent gates. What survives from this task is the decision above it,
whose second branch — leave the pin and say which value was kept — is what the tree does
now. The reason for the reversal is in 007's plan, and it is `doctor --fix`: reachable only
by typing the command, an unconditional rewrite is a footgun, and reachable from a
diagnostic it is `update` with the consent removed.

Two orderings changed while this was built, and both are recorded rather than tidied away.
Task 8 landed before task 7, because 7's assertion exempts a row from its own write sites
and that exemption is only sound once nothing writes into a surface that was not already
found — which is what 8 does. And task 7 turned out to be five rows rather than four: the
ADR missed Claude Code, whose `~/.claude/skills` sits inside `~/.claude`, because that is
the one surface everybody testing this has installed.

## The base this was measured from

Committed `HEAD` measures **12,017** against a `REPO_CEILING` of **12,017**: the headroom
is exactly zero. This worktree measures **12,083** — sixty-six over, and none of it is this
work. It is the in-flight TypeScript lane: `tsconfig.json`, `package.json`, the `typecheck`
recipe in `justfile`, `surfaces/opencode.ts` and the workflow step that runs it. So the
ceiling test and `doctor`'s line-budget assertion are red before this branch starts.

Every figure below is a prediction, marked as one. The closing task replaces the whole
table with the count that landed.

Two orderings are constraints rather than preferences, and both concern spec 003.

**The ceiling is 003's, and 003's own number is stale.** Spec 005 deliberately raises
nothing: its arithmetic goes into 003's raise. But 003's plan predicts `REPO_CEILING`
5,790 from a base of 5,610, and the constant now reads 12,017 — that plan was written
before the test plane landed and its section 3 is arithmetic against a repository that no
longer exists. It has to be restated against the real base, and when it is, this spec's
prediction goes into the same table. Nothing here may be started before that.

**Task 1 lands before 003's overwrite task, not after.** Section 7 of 003's plan makes the
offer compare what it would render against what is on disk. On a fresh repository that
comparison finds the four files byte-identical to what was just written, so nothing is
offered and the screen looks correct — with `existing()` still called after the writes,
and the "left as is" line still naming files the installer created. That is the defect
hidden rather than fixed, and it would be hidden by a task whose own check passes. Move
the call first, then let 003 add the content comparison on top of a correct order.

One task, one commit.

## 1. The reported defect, and the marker that already knew

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** with the
  `xfail` decorator deleted, `pytest tests/test_mut_init.py -q` fails today at
  `test_the_files_the_installer_just_wrote_are_not_reported_as_unmanaged` and passes after ·
  **rollback** revert · **done when** `existing(root)` is called before the loop that writes
  the missing offers, the strict `xfail` and its four-line reason are gone, and the
  neighbouring test that today pins the buggy output — it asserts all four files are "left
  as is" in a repository where two of them pre-existed — asserts the two. The marker is
  strict, so the fix without the deletion is a failing build, which is the whole point of
  its being strict. **−6 product-adjacent test lines, +1.**

## 2. The parser that loses input

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** a parametrize
  over four typed replies — `1, 2`, `1,2`, `all`, `1 9` — asserting two files, two files,
  four files and one file with a named remainder; today those four return one file, none,
  none and one silently · **rollback** revert · **done when** the typed reply is parsed by
  the same function as `--overwrite`, so `all` means the same thing in both spellings and a
  comma is a separator in both, and one line names anything that was ignored. Two parsers
  for one intent five lines apart is the DRY half of rule 10, and merging them is smaller
  than fixing one of them. **+4.**

## 3. The check nobody wrote

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check**
  `git grep -c unmanaged -- src/` returns nothing, and the test that pins the sentence
  asserts the replacement · **rollback** revert · **done when** the clause promising that
  `doctor` lists these files as unmanaged is gone. The word appears zero times in
  `doctor.py` and no assertion looks at those files; it is the sentence a person reads in
  order to decline the overwrite. Whatever replaces it says only what is true: the files are
  left alone and nothing watches them. This edits the same assertion string task 1 edited —
  `test_files_that_are_already_there_are_named_and_left_as_they_are` pins the file list and
  the sentence in one literal — and the two are separate commits because a wrong order and a
  false claim are two defects that a reviewer should be able to revert apart. Net **0**.

## 4. The backup that overwrites the backup

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** two overwrites
  of the same file inside one second leave two backups; today the second replaces the first
  and the test that covers backups asserts only that a timestamp is present · **rollback**
  revert · **done when** the backup name carries sub-second resolution. The existing test
  docstring already claims this is what the timestamp rules out, so the test is being made
  to mean what it says rather than being added. **+1.**

## 5. The dry run that reports writes

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check**
  `ai-eng init --no-global --project <tmp> --dry-run` prints no line containing "written",
  the directory is still empty, and — after task 1 — it prints the checklist its help
  promises · **rollback** revert · **done when** the flag guards the printing as well as the
  writing. Today the writes are guarded and the prints are not, and the test asserts the
  files are absent rather than that the output stopped claiming otherwise, which is why this
  has survived. **+3.**

## 6. The pin

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** a repository
  whose `.ai/config.toml` carries an edited value, re-run with `--project`, still carries
  that value, or carries the default with a dated backup beside it and a line of output
  naming the change; today it is silently replaced with no backup and no line · **rollback**
  revert · **done when** the file this project's vocabulary calls the pin is treated at least
  as carefully as the four instruction files beside it. The constitution's rule is that a
  change of governance is never silent, and this is the file that names which version
  governs the repository. **+6.**

## 7. A surface stops detecting itself

- **file** `policy/surfaces.toml`, `tests/test_contracts.py` · **check** a test walks every
  row of the table and asserts its `detect` path is not equal to, and not a parent of, any
  `skills` root or `settings` path in the table; today four rows fail it — OpenCode, pi, Zed
  and VS Code Copilot · **rollback** revert the data edit and the test together ·
  **done when** the rule from ADR 0001 is an exit code rather than a paragraph, and the four rows
  name a path this project never creates or are marked undetectable. A row that cannot find
  such a path is wired by name only, which the table can express and the survey line already
  prints. **+9.**

## 8. Skills stop being linked into every root in the table

- **file** `src/ai_engineering/wiring.py`, `src/ai_engineering/init.py`,
  `tests/test_mut_wiring.py`, `tests/test_mut_init.py` · **check** `init --global --harness
  claude-code -y` against an empty HOME creates `~/.claude/skills` and nothing else; today
  it creates four skills roots and the survey line then calls three of those surfaces "not
  installed" on the same screen · **rollback** revert · **done when** `install_skills`
  receives the surfaces that were found and links only their roots, with the no-argument
  form still meaning every root so the two existing wiring tests stay honest rather than
  being rewritten. Task 7 removes the detection consequence; this removes the write that
  caused it, and both are needed because two of the four overlaps are between rows rather
  than between a row and itself. **+7.**

## 9. Three assertions stop passing on an empty set

- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check** `doctor` run
  against a HOME with no receipt reports could-not-evaluate for the three checks that read
  the receipt and the detected surfaces, and the summary line counts them as not evaluated;
  today all three print ok · **rollback** revert · **done when** an empty set raises
  `Undecidable` with the reason instead of falling out of a loop. The third state already
  exists, it is already never green, and the printer already has a line for it — this is
  using it, not building it. The existing three-state exit-code table gains the rows.
  **+8.**

## 10. Every failure names its cure

- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check** a test asserts
  that every check in the named repairable set returns a message containing a backticked
  `ai-eng` command, and fails today for all of them · **rollback** revert · **done when** the
  messages for the guard entry, the hooks path, the skills link and the pin each end with the
  command that fixes them. This is ADR 0002 as an exit code: the whole user-facing value of a
  repair flag, without a second unconsented entry point to writes that already have a verb.
  The set is named in the test rather than inferred, because "does this check have a cure"
  is a judgement a script cannot make — and naming it in the test means adding a check with
  a cure and no command fails the build. **+6.**

## 11. The wall the repository is not told about

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** wiring a
  project on a PATH with no `gitleaks` prints the warning, the install line and the sentence
  that commits are refused until it exists; with `gitleaks` present it prints nothing
  extra ·  **rollback** revert · **done when** the condition is named at the moment it is
  created rather than at the person's next commit. It observes one `which` and claims
  nothing else, which is what the constitution allows and what the four package-manager
  branches would not be. **+7.**

## 12. The dead end in a directory that is not a repository

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** in a non-repo
  directory, `ai-eng init -y` creates no `.git` and exits 0; answering yes at a terminal
  creates one; the existing test that pins the current single line and exit code is updated
  in the same commit · **rollback** revert · **done when** the offer exists with a **literal
  `False`** as its default. Not `sys.stdin.isatty()`: `ask` returns the default under `-y`,
  so a terminal-shaped default would make `cd ~ && ai-eng init -y` create a repository in
  the person's home directory. The `-y` case is in the check for that reason and not for
  symmetry. **+8.**

## 13. The screen that says it is finished

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** the last screen
  of `ai-eng init --project <tmp> -y` names how many files were written and how many guard
  entries were placed, and carries a numbered list whose first item is that the skeleton
  carries `TODO:` markers on purpose and that `doctor` fails until a person fills them in;
  today the run ends by printing a block of YAML · **rollback** revert · **done when** a
  stranger who reads only the last screen knows what happened and what to do next. The YAML
  block stays, above the report rather than as the final word. Written on the output
  primitives that already exist — no new module, no dependency. **+15.**

## 14. The close

- **file** `src/ai_engineering/contract.py`, `specs/005-init-says-what-it-did/plan.md` ·
  **check** `just check` green, `just mutate` at or above its floor, and
  `contract.repo_lines` equal to the constant · **rollback** revert · **done when** the
  ceiling reads the number that actually landed and this table is replaced by the measured
  one. Two things this task is not allowed to do: leave slack behind, which is how a ceiling
  stops meaning anything; and pad the suite to make the mutation floor, which the test-ratio
  gate exists to catch. The floor is the second binding gate here and it has no margin —
  every branch tasks 2, 5, 6, 9, 11 and 12 add is a mutant, and `init.py` sits in the half
  of the tree the floor's own comment names as thin.

## Neither mandatory task class applies

This spec deploys nothing and gives nothing a URL. There is no pipeline to build and no new
signal to observe, so the CI/CD task and the observability task are absent by fact rather
than by omission, and the eight boxes in the spec stay unticked. The one CI question this
work does raise — that the closing report and the two warnings are exercised on Linux alone,
because the only job that runs `init` on macOS and Windows drives it with `-y` — is recorded
as an accepted risk with a date rather than smuggled in here as a task.

## What this plan is not doing

**Not touching `uninstall`.** The OpenCode parse crash, the skills tree it leaves behind and
the hooks path it fails to restore are three tasks in section 7 of 003's plan. Two branches
editing one file is one conflict.

**Not building the selection widget, the repair flag, the tool installer or the per-surface
uninstall.** All four are refused in writing in the spec, and two of them are now ADRs. A
reviewer who wants them back has a file to supersede.

**Not raising the ceiling.** Task 14 closes it at the measured count; the raise itself is
003's, restated against the real base as the precondition above requires.

**Not cleaning up the `.bak` files, and not fixing the `--overwrite all` route around the
two protected files.** Both are accepted risks with dates and named follow-ups. The second
is 003's to fix and the acceptance says so.

**Not accepting either ADR.** They ship `status: proposed`; accepting or rejecting one is a
one-line change in the pull request, which is the review this project chose over a meeting.
