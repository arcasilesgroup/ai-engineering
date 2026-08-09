---
id: "008"
slug: the-receipt-that-only-grows
title: Plan — the test that was missing first, so every later task has something to fail
---

# Plan — the round trip before the repair

## What landed — measured, 2026-08-09

Read from `git diff --numstat` per commit over the files `contract.repo_lines` counts, in
the order the commits landed.

| | predicted | landed |
|---|---|---|
| 0. the ceiling raise, and what it was buying | — | +13 |
| 1. the round trip nothing asserts | +45 | +90 |
| 2. a record nobody can read is undecidable | +129 | +146 |
| 3. the receipt gains a way out | +37 | +55 |
| 4. one line per row, and the record retracted | +102 | +89 |
| 5. a repository you are not standing in | +39 | +43 |
| 6. one file it cannot change stops that file | +38 | +84 |
| 7. the links it removes are the ones it installed | +50 | +47 |
| 8. `init` asks the machine | +72 | +86 |
| 9. the row uninstall restores from | +36 | +25 |
| 10. the coverage block opens the settings file | +120 | +70 |
| 11. assertion 13 looks inside the room | +52 | +30 |
| 12. assertion 21 stops offering a cure that cannot work | +38 | +30 |
| 13. `update` records what it wires | +69 | +62 |
| 14. the prose this spec made false | 0 | +3 |
| 15a. the tests the mutation floor asked for | — | +175 |
| 15b. this table and the ceiling comment | — | +35 |
| **total** | **+840** | **+1,092** |

`REPO_CEILING` closes at **16,803**, with no slack.

## What T-7 measured

`just check` — exit 0. 801 passed, 3 xfailed; `just cover` at 97% against a floor of 80;
gitleaks, semgrep and trivy clean; `RAN lint=86`, `RAN tests=783`.

`python tests/adversarial/run.py` — 14 of 14, negative control included.

`just mutate` — **red the first time, at 88% against a floor of 89.** 543 survivors of 4,652,
and 96 of them were in `uninstall`: 74% against a tree at 89, so the code this spec wrote was
a third of the survivors on a twelfth of the lines. The plan named this task as the binding
gate with nothing to give, and it was.

What killed them is the same lesson specs 005 and 006 both closed on, arriving a third time:
the screen asserted whole rather than by fragment, a count asserted as a number rather than
as a line that happens to contain one, a fate table with a row for every kind there is, and
the consent question driven with five answers instead of one. Three real defects were behind
those survivors — a copied skill removed on a row that says symlink, a count that could have
reported anything, and `unlink(missing_ok=False)` on a file a person had already deleted.

What could not be killed left instead. `timeout=10` and `capture_output=True` written at
three call sites are six mutants no honest test can reach, because a repository that answers
in eleven seconds is not a behaviour anybody can assert; they became one function and stopped
existing, which is the exit spec 006 took for `soft_wrap=True`. Ten more are equivalent by
construction: git config keys are case-insensitive, so `core.hookspath` and `AI.MANAGED` do
exactly what the originals do, and no test can tell them apart because there is nothing to
tell apart.

Second run: **4,129 killed, 508 survived, 89%** — at the floor, which is where 006 and 007
both left it. Guards half 14 of 14.

One thing worth writing down that is not a number. The guards half of `just mutate` edits the
real tree and restores each file in a `finally`; a run that is interrupted leaves a deliberate
defect behind. This one was, twice — `FAILURES = 5` became `6` in `loop_guard.py` and a `<=`
became `<` in `design_gate.py` — and both were caught by `git status` rather than by anything
that fails. The recipe's own comment says the four watched surface files are hashed either
side of the run for exactly this reason; the guards it mutates are not.

**Five per cent over, against 005's eight hundred and seventy and 007's seven hundred and
thirty.** The reason is not discipline. Those two counted the product line and never the
test that holds it; this estimate was written after that bill had been paid twice, so it
carried the test line from the start. 612 of the 881 are test against 269 of product.

**Nine of the fifteen tasks changed a test that was pinning the defect rather than adding
one.** That is the finding worth keeping out of this table, because it is the same shape
every time: `/a`, `/b`, `/c` and `/somewhere/settings.json` as fixtures for counting rows in
a file; a vendor's directory created and asserted on as though it were a wired surface, in
four separate tests across three files; and one passing assertion that an install destroys a
settings file, whose own docstring read *"This pins the loss; it does not bless it."* A
suite can be green, thorough and describing a machine that does not exist.

Two things happened that are not in the table.

Task 2 grew a second half nobody had looked for. The lenses were pointed at the receipt, and
the same `read_json` line sits under the three settings writers — so `ai-eng init` replaced a
`~/.claude/settings.json` carrying a JSONC comment with our hooks block alone. That is the
operator's own live file, and it is worse than the bug this spec was opened for.

Task 5's fix had to be applied twice in one commit's worth of code. `fate`, written two
hours earlier in task 4, had copied the same `startswith` comparison the bug lives in. A
copied idiom keeps a defect alive across the rewrite that was supposed to remove it.

## The base this was measured from

Committed `HEAD` measures **15,712** against a `REPO_CEILING` of **15,712**: specs 005, 006 and
007 closed at the count that landed, so the headroom is exactly zero and the first task that
adds a line needs a raise. Every figure below is a prediction, marked as one, and the closing
task replaces this table with the count that landed.

Spec 005's estimate was out by nearly a factor of ten and spec 006's by two, for the same
reason both times: the prediction counted the product line and not the test that holds it. The
figures here carry the test line with them and are roughly three to one against the product.

**Total predicted: +840, of which +215 product and +625 test.** The one prior estimate in this
project that carried its test line — spec 007's — came in at 879 against 106 planned, and the
overrun was the mutation floor asking for tests nobody had planned. That will happen here too:
the floor sits at 89 against 89 with no margin as of spec 007, and tasks 4 through 10 are
almost entirely new branches.

Two orderings are constraints rather than preferences.

**Task 1 lands first and it lands red.** No test in this repository runs `uninstall` and then
asks what `init` sees. That is why a screen reporting four guards over zero could ship. It is
the only commit in this plan allowed to be red, and it is red on purpose for exactly one
commit.

> **Changed while building, and recorded rather than tidied away.** It landed as four strict
> `xfail`s instead of four red tests. Same pinning, and a green gate: a strict marker turns the
> build red the moment the defect is fixed without the marker being deleted, so each one names
> the task that removes it. This is the idiom this repository already uses — spec 005's whole
> first task was deleting one — and a red commit would have made `just check` fail on the
> branch for a reason a reviewer has to be told to ignore. Each test asserts against
> `stripped()`, which reads the guards and links off the disk, so the four failures are about
> what the report says and never about `uninstall` having failed to do its half.

**Task 2 lands before anything else touches the receipt.** While a corrupt receipt reads as an
empty one, every later task is building on a file that can silently become `{}` — and task 3's
retraction path would then write that emptiness back as fact.

One task, one commit.

## 1. The round trip nothing asserts

- **file** `tests/test_install.py` · **check** a test installs the machine half against a
  temporary HOME, runs `uninstall -y`, and then asserts: no surface settings file contains
  `wiring.SIGNATURE`; `init.global_ready()` is `False`; a plain `init.main(["--no-project"])`
  rewires rather than printing the ready block; and `doctor`'s assertion 13 does not report ok.
  It fails today on all four · **rollback** delete the test · **done when** the defect is pinned
  by a red test rather than by a paragraph. `tests/test_mut_init.py:243` already asserts
  `global_ready()` is `False` for an empty `wrote`, so the new assertion is about a receipt that
  is full and a disk that is not. **+45 test, 0 product.**

## 2. A record nobody can read is undecidable, never empty

- **file** `src/ai_engineering/wiring.py`, `src/ai_engineering/doctor.py`, `hooks/_emit.py`,
  `tests/test_mut_wiring.py`, `tests/test_install.py` · **check** a truncated `machine.json`
  makes `receipt()` raise rather than return `{}`; `record()` refuses to write over it and says
  which file; a `~/.claude/settings.json` carrying a JSONC comment is left alone with the reason
  printed rather than replaced; `doctor` reports could-not-evaluate rather than ok; and a file
  that is simply absent still reads as empty, because absent and unreadable are different
  answers · **rollback** revert · **done when** `read_json` stops treating a parse failure as an
  empty document. Measured: a receipt of three rows, one interrupted write, and `record` stores
  one — the `project` rows that tell `uninstall` which files are ours, gone for good. And the
  same line under the three settings writers, which open with `read_json`, mutate and write
  back, so a settings file this tool cannot parse is **replaced** with our hooks block alone
  while the screen says `(merged)` and the docstring three lines above says foreign entries are
  preserved. That half is the operator's own live file, and it is worse than the receipt half.
  This repository already made this ruling one file over, in `text.yaml_blocks`, and its
  sentence is the check: *undecidable is an answer, invisible is not*. `hooks/_emit.machine_id`
  loses its bare `except Exception` write in the same commit, because it is a second route to
  the same loss. **+34 product, +95 test.**

## 3. The receipt gains a way out

- **file** `src/ai_engineering/wiring.py`, `tests/test_mut_wiring.py` · **check** a test records
  five rows, forgets two by `(path, kind)`, and asserts the file holds the other three and that
  forgetting a row that was never there is not an error · **rollback** revert · **done when**
  `record` has a sibling that removes. It matches on `(path, kind)` because that is the key
  `record` already deduplicates by, and a retraction keyed on anything else is a second identity
  for one row. `machine_id`, `version`, `python` and `hooks` are left alone: they describe the
  install, not what it wrote. **+12 product, +25 test.**

## 4. `uninstall` says what it did to every row it showed you

- **file** `src/ai_engineering/uninstall.py`, `tests/test_install.py` · **check** a receipt
  holding one row of every kind produces exactly one line per row; the `skills` row says it was
  kept and why; the consent question counts only rows this run will touch; the receipt
  afterwards holds the kept rows and none of the removed ones; and the repositories in the
  receipt that are not this one are named with the command to run inside each · **rollback**
  revert · **done when** the loop has a branch per kind and the verb retracts what it removed.
  Nothing starts deleting files across four repositories from one `y`; naming them and stopping
  is the honest half. **+32 product, +70 test.**

## 5. `uninstall` cannot reach a repository you are not in

- **file** `src/ai_engineering/uninstall.py`, `tests/test_install.py` · **check** a receipt
  holding `project` rows for `<root>` and for `<root>-backup` unwires only the first; today
  `"…/tests-backup/justfile".startswith("…/tests")` is `True` and the file is unlinked ·
  **rollback** revert · **done when** the comparison is by path parts rather than by string
  prefix. This is its own commit and not folded into task 4 because it is the only defect here
  that destroys a file outside the blast radius the user consented to. **+4 product, +35 test.**

## 6. One unwritable file stops that file, not the loop

- **file** `src/ai_engineering/uninstall.py`, `tests/test_install.py` · **check** a settings
  file that cannot be written leaves the surfaces after it unwired-and-reported rather than
  wired-and-silent; the verb exits non-zero naming the file · **rollback** revert · **done
  when** `strip_entries` guards the write it already guards the read and the parse for. It is
  the shape spec 003 closed for the OpenCode parse crash, in the one line that fix did not
  reach. **+8 product, +30 test.**

## 7. The link branch removes the links the receipt names

- **file** `src/ai_engineering/uninstall.py`, `tests/test_install.py` · **check** a skills root
  holding one of our symlinks and one `ai-*` skill somebody else installed keeps the second;
  today both go · **rollback** revert · **done when** the branch reads the rows rather than
  globbing the directory, and reports what it actually removed instead of printing a tick.
  `tests/test_install.py:378` is a strict `xfail` for the Windows half of this same line —
  copies recorded as `how: "copy"` are never removed — so that marker comes off in this commit
  or the build goes red for the right reason. **+10 product, +40 test.**

## 8. `init` asks the machine

- **file** `src/ai_engineering/init.py`, `tests/test_mut_init.py` · **check** with a receipt
  listing four guards and four links and a disk holding none, `global_ready()` is `False` and
  the survey runs; with both present it is `True` and the ready block prints counts read from
  the disk; and a test compares every number on that screen against the filesystem ·
  **rollback** revert · **done when** the sentence spec 007 shipped — *every number here is
  counted from what is on the disk* — is true of every number rather than one in three.
  `global_ready()` asks the question assertion 2 asks, through the same helper. The closing
  panel's guard count and its "the guards are already loaded there" step read the same source.
  **+22 product, +50 test.**

## 9. `init --project` stops poisoning the row uninstall restores from

- **file** `src/ai_engineering/init.py`, `tests/test_install.py` · **check** a repository set up
  twice, then uninstalled, has no `core.hooksPath` rather than ours; today the second run
  records our own hooks directory as the value that was there before us · **rollback** revert ·
  **done when** the `repo` row is written once and never overwritten by a later run, which is
  the same rule task 3 of spec 007 applied to the pin. **+6 product, +30 test.**

## 10. The coverage block reads the settings file

- **file** `src/ai_engineering/doctor.py`, `policy/surfaces.toml`, `tests/test_mut_wiring.py` ·
  **check** a surface whose directory exists and whose settings file holds no entry of ours
  reports UNPROVEN with the reason, not BLOCKS; the `opencode` heartbeat is cleared by
  `uninstall` so a deleted plugin cannot read as blocking for a day; and `coverage()`'s
  docstring claim — *derived: from the receipt, the pin, the settings files on disk* — is either
  true or gone · **rollback** revert · **done when** the block that answers *where can a call
  actually be stopped* stops answering it from a static flag. `digest` reprints this block with
  no assertion beside it, so it is the same fix in both readers. **+30 product, +90 test.**

## 11. Assertion 13 checks the links and not the room they are in

- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check** a skills root that
  exists and holds none of our links reports FAIL naming the root; one that holds them reports
  ok; one that is gone still reports FAIL; and a row recorded `how: "copy"` on a stale copy is
  named · **rollback** revert · **done when** the check looks inside. Its own `Undecidable`
  branch already says *an empty loop is not a passing check*, and it was keyed on the receipt
  having no link rows — which task 3 makes reachable and which, until then, could never fire.
  **+12 product, +40 test.**

## 12. Assertion 21 stops naming a cure that cannot work

- **file** `src/ai_engineering/doctor.py`, `tests/test_doctor.py` · **check** on a machine with
  no Codex entry, assertion 21 says the guard is not registered and names `ai-eng init
  --global`, not `/hooks`; with an entry present and unapproved it says `/hooks` as it does
  today · **rollback** revert · **done when** the two shapes of that failure carry their own
  cure, which is ADR 0003's rule applied to a check spec 007 wrote before this shape existed.
  **+8 product, +30 test.**

## 13. `update` records what it wires, and wires only what was chosen

- **file** `src/ai_engineering/update.py`, `tests/test_install.py` · **check** a machine where
  Cursor was declined at install still has no Cursor entry after `ai-eng update`; every entry
  `update` does write appears in the receipt; and `uninstall` afterwards removes all of them ·
  **rollback** revert · **done when** `update` stops being a second, unrecorded installer. It
  rewires everything `detect()` finds, so declining a surface at install and updating later
  wires it `failClosed: true` with no row — and `uninstall` then swears it was never there.
  **+14 product, +55 test.**

## 14. The prose that this spec makes false

- **file** `specs/007-the-install-a-stranger-can-follow/plan.md`, `src/ai_engineering/init.py`,
  `docs/tools.md` · **check** `git grep` for the four sentences named in the spec returns the
  corrected text · **rollback** revert · **done when** spec 007's plan says what its
  already-wired summary actually exposed, and no docstring left in the tree claims a number is
  read from the disk when it is read from the receipt. Corrections, not rewrites: the sentences
  stay and the record says what happened, which is how specs 005 and 007 were closed. Net **0**.

## 15. The close

- **file** `src/ai_engineering/contract.py`, `specs/008-the-receipt-that-only-grows/plan.md` ·
  **check** `just check` green, `python tests/adversarial/run.py` green, `just mutate` at or
  above 89%, and `contract.repo_lines` equal to the constant · **rollback** revert · **done
  when** the ceiling reads the number that landed and this table is replaced by the measured
  one. Two things this task may not do: leave slack, and pad the suite to reach the mutation
  floor. The floor is the binding gate again and it has nothing to give.

## The mandatory task classes

This deploys nothing and gives nothing a URL, so the CI/CD task and the observability task are
absent by fact. The one thing this spec adds that CI can see is task 1's round trip, which runs
inside `just check` like every other test and needs no job of its own.

## What this plan is not doing

**Not building per-surface uninstall.** Spec 005 refused it because the receipt had no delete
path. That premise stops being true in task 3, and the feature is still not wanted: nobody has
asked for it, and adding it here would bury the fact that the refusal's reason moved.

**Not deleting `machine.json`.** Killed in writing in the spec: it is the only record of which
project files this tool wrote, across every repository it has touched.

**Not touching the chain under `~/.ai-engineering/state`.** `uninstall` already says that folder
is proof of what happened and not ours to throw away, and that sentence stays as it is.

**Not repairing the operator's machine as part of a task.** It is unwired right now and
`ai-eng init --global` restores it today; that is an operation, not a commit.
