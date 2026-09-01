---
name: new-feature
description: Sets a feature up end to end — makes the feature folder, asks whether to interview first, gets the mock built and approved, then writes the spec. Produces a feature that is ready to build, with no loop attached. Use when the user says "new feature", "set up a feature", "make the spec for X", "I want to add X to the app", or names something they want built that doesn't have a folder yet. Run this before feature-batch, never during a loop.
---

# new-feature

Sets one feature up so it's ready to build. It runs the other skills in the right
order and **stops where the user has to decide something.**

```
folder  →  interview?  →  mock  →  APPROVE  →  spec  →  ready
          (they choose)          (they approve)
```

**This skill does not put the feature in a loop.** It stops at a finished spec. If
the user wants it looped, `goal-writer` writes the `/goal` condition on top of what
this produces, and `feature-batch` runs several of them. **Those depend on this one.
This one depends on neither**, which is the point: a feature you're going to build
yourself, in one sitting, still wants a mock and a spec, and it should cost you
nothing to skip the loop.

**The two stops are the point of this skill, not friction in it.** Everything after
the mock is approved runs without the user. Everything before it is theirs. A run
that sails through both gates has skipped the only two decisions in the process.

---

## 1. Name it and make the folder

Ask what the feature is, in one line, if they haven't said. Then:

```
features/<feature-name>/
  verification/     empty. the loop fills it later
```

Lowercase, hyphenated, named for what the feature does, the way
`features/landing-page/` already is.

## 2. Ask whether to interview first — do not decide this yourself

> "Do you want to run grill me on this first, or is it clear enough to mock?"

**Ask, then wait.** `grill-me` interviews the user until the feature is actually
pinned down, and it's worth it when the feature is still fuzzy or when it touches
data, permissions, or more than one role. It's not worth it when they can already
describe the screen, because in this project the mock answers most of what the
interview would ask.

If they say yes, run `grill-me` and carry what comes out of it into the next step.

## 3. Build the mock

Run `functional-ui`. It reads the real app and the whole-app clone at
`mocks/app.html`, then derives this feature's own mock into
`features/<feature-name>/app.html`, covering every role the feature serves.

**The feature needs its own hash route in that mock** (`#/admin/day-view`), because
that hash is how the spec points at the thing it owns. A screen with no stable
route can't be referenced by anything downstream.

## 4. STOP. The user approves the mock

Show them the screen and wait. Do not write the spec, do not touch app code, do not
queue anything.

This is the last human gate in the whole level. What they're approving is a picture
of the finished feature, and once they say yes it becomes the standard the build
gets held to. If they want changes, change the mock and ask again.

## 5. Write the spec

Write `features/<feature-name>/spec.md`. The rules for it are below, and they are
most of this skill, because the spec is the thing everything downstream reads.

## 6. Say it's ready, and stop

The feature is set up. Tell the user it's ready to build, mention that
`goal-writer` will loop it if they want that, and leave it there.

---

## Writing spec.md

**Write it to be re-entered with no memory.** A loop's every pass starts from
nothing, so the file has to carry the whole job on its own. No "as discussed", no
"the remaining work". This holds even when nobody intends to loop it, because the
person reading it in a week is in the same position.

Read what's already in the folder before you write a line of it. Anything the build
could be compared against is a verifiable, and it belongs in the spec.

- **The feature's mock** — open it. Whatever it establishes that the build has to
  hit goes into the definition of done as its own checkable line, and the mock gets
  named in the verification procedure as the thing to diff against, by hash route.
- **Reference images** — look at them. Write down which parts are the reference and
  which parts aren't, because a reference is almost never a target for everything.
  Layout and composition might come from it while colour and type come from the
  project's own design files. Say which is which, by name, or the build copies the
  wrong half.
- **Anything else sitting there** — a data file, a copy doc, a captured video. If a
  pass could check itself against it, it's a verifiable.

If the feature has a look and there's nothing to compare against, say so rather than
writing a check that can't be run. A reference is the difference between a check and
an opinion, and inventing one is worse than naming the gap.

### The pass procedure goes at the top

1. Run the verification first. Never open with code — open by finding out what is
   currently failing.
2. Fix **one** thing: the highest item that isn't green.
3. Re-run the verification, prove that item is green and nothing else regressed.
4. Record the result and continue or stop per the stop condition.

**A pass that changes nothing still counts as a pass.** Without that line a loop
spins on a no-op.

### Sections

Numbered, so a goal condition can point at them by number.

| Section | Holds |
|---|---|
| How to run this | The pass procedure, and which skills to load for this feature |
| What this is | One paragraph. What it's for, and what it must never become |
| Hard constraints | What must not change. Schema, other surfaces, libraries, scope |
| The build | Whatever the feature needs — routes, blocks, states, copy, motion |
| Gates | Thresholds with numbers. Performance, size, console, accessibility |
| Verification procedure | The exact commands, and where output goes. Re-run every pass |
| Definition of done | A checklist, in fix order. The first unchecked box is the work |
| Stop condition | When it's finished, and when to give up |

### The parts that decide whether it works

**Gates need numbers.** "Fast" is not a gate. "LCP under 2.0s, no frame over 32ms,
First Load JS under 180KB" is.

**The verification procedure needs the actual commands**, and it needs to say where
the output lands. If a pass can't reproduce the check exactly, the results aren't
comparable between passes.

**Never accept a score as evidence.** Quote the individual numbers. A Lighthouse
score hides which metric moved.

**Report the worst, not the mean.** Worst frame, not average frame. An average hides
the stutter people actually notice.

**Definition of done is ordered.** The first unchecked box is the work, so the order
encodes what matters. Correctness before design before performance.

**Stop condition wants two consecutive clean passes**, not one, whenever the checks
are flaky by nature — screenshots, timing, anything measured. One green pass can be
luck.

**Give it a give-up rule.** If the same item fails three passes in a row, something
is wrong with the approach and another pass won't fix it. Stop and report which item.

### Before you hand it over

- Does every gate have a number, and does it come from the user or the project
  rather than from you?
- Does the verification procedure name real paths and binaries that exist on this
  machine? Check them. A wrong version string fails every pass silently.
- Would the spec still make sense to someone who has never seen this conversation?
  That's the position anyone reading it is in later.

---

## What this does not do

- **Build anything.** No app code. The feature is set up, not made.
- **Write a `/goal` condition.** That's `goal-writer`, and it's a separate decision.
- **Queue it or run it.** `feature-batch` does both. Do not touch `features/QUEUE.md`.
- **Decide the interview.** Step 2 is a question, every time.

---

## Setting up several at once

Run the whole sequence per feature, one at a time, and finish one before starting the
next. Batching the mocks together and writing all the specs at the end sounds faster
and isn't: the approval gate is where features get cut or reshaped, and finding that
out after five specs exist means rewriting five specs.

## Both tools

Lives in `.agents/skills/` and is symlinked into `.claude/skills/`, so one copy serves
Claude Code and Codex.
