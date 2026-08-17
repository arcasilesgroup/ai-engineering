---
id: "018"
title: "Controls a reviewer proved were not controls"
slug: controls-a-reviewer-proved-were-not-controls
status: draft
date: 2026-08-17
---

# Plan — controls a reviewer proved were not controls

One repair pass over the eight findings an independent reviewer raised against the twenty
commits `e3c779dd~1..ffa9cde7`, in the shape `docs/adr/0011` requires: the writer stopped,
the diff was frozen, the reviewer read each commit against its parent and against the
requirement texts, every finding landed in one ledger, and the repairs are this one pass.

Each task lands the fix and the check that would have caught it without a reviewer. A task
with no such check is not done.

## Tasks

- [x] T-1 The whole-tree mutation gate reads a field that exists. `check.yml` and
  `tests/anti_theatre.py` read `updated_at`; `tests/test_anti_theatre.py` records the field
  set a live workflow-run object returns and refuses a fixture that invents one, so the two
  readers can no longer agree with the fixture that taught them.

- [x] T-2 The nightly alarm can fire. `mutation-nightly.yml` creates the `mutation` label
  before naming it, and the issue body stops claiming a failure blocks a merge, which the
  gate it describes does not do.

- [x] T-3 The security lane answers instead of throwing. `scan.model` catches `ValueError`,
  which is what a non-UTF-8 file raises; `scan.stacks` stats through a helper that answers
  `False` on `OSError`. Two fixtures, one per input, both driving `scan.baseline`.

- [x] T-4 The five-condition guard has five reasons. `spec._why_not_authority` takes the
  approval, names the `approval_ref` drift, and `tests/test_mut_spec.py` counts the guard's
  conditions against the explainer's branches so a sixth cannot be added silently.

- [x] T-5 The machine-path exemption excuses names, not files. `PATH_EXEMPT` holds the names
  found on the day it was written, and a second test refuses an excused name that has left
  the file it was excused for.

- [x] T-6 Every boundary's check touches its control. The `dispatcher-input` row names
  `tests/test_hooks.py`, and a new test refuses any row whose check never mentions its
  control — the relation the file header promised and nothing held.

- [x] T-7 A preview needs no keyboard and a removal still does. `uninstall --dry-run` passes
  the tty gate, the gate is asked again before any removal, and one fixture drives both
  halves from a pipe rather than monkeypatching `isatty` to True first.

- [x] T-8 The published ledger says what actually closed each row. `EP-113` is credited to
  the commit `git blame` names; `EP-044` gets the data-flow and business-rule clauses it asks
  for, written into `ai-review/SKILL.md` and pinned, because two of its four published pins
  guard other sentences.

- [x] T-9 The two hand-kept claims get readers. The assertion count in `ai-eng --help` is
  pinned to `len(doctor.CHECKS)`, and `FIXTURE_NAMES` keeps only the names the tree carries.

- [x] T-10 `just check` green and shown: 1,454 tests, lint 181, skilleval 254, adversarial
  21 of 21.

- [ ] T-11 The whole-tree mutation lane, run to a number. **Not done, and not for want of
  trying.** Three local runs reached the baseline and past it — 82%, 37% and 82% of 21,772
  mutants — and every one was killed by the environment rather than failing. What is measured
  is the scoped lane over the five modules this branch changes: 3,212 killed, 1,117 survived,
  **74%**, against a floor of 89. That floor is the whole *package* average, and the justfile
  records that the average is that low because `update` and `uninstall` drag it down while
  everything else sits between 93% and 98%. This branch changes `uninstall`. So a bar that
  reads "this change is well tested" means "this change did not touch the two weak modules",
  and no branch touching either can pass it. Lowering it to go green is the defect this
  repository is named after, so it is a decision and not a repair: it is written up for the
  owner with three options and a recommendation, and nothing here acts on it.

## Green gate

`just check`, and `python tests/adversarial/run.py` at 21 of 21. The mutation lane is run
whole rather than scoped, because three of this pass's own tests were what took it down.
