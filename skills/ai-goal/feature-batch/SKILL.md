---
name: feature-batch
description: Batches features and runs them. Tell it which features to batch and it writes features/QUEUE.md; pass it to /goal and it works that queue overnight, one feature at a time, building and verifying each one and opening a pull request when it passes. Use when the user says "batch these features", "queue these", "run these in a loop", "build these overnight", or names more than one feature to build.
---

# feature-batch

Two jobs, same skill, because they're the same list.

1. **Batching** — the user says which features to run. You write `features/QUEUE.md`.
2. **Running** — the user puts this skill in a `/goal`. You work the queue.

Which one you're doing is obvious from what they said. "Batch the availability and
the day view" is the first. A `/goal` firing on its own is the second.

**The whole design rests on one thing: every pass starts from nothing.** The agent
does not remember the last feature, the last failure, or what it already tried. So
the state lives in files, and this skill is the instruction for reading them, doing
one unit of work, and writing the state back.

---

## The two files

**`features/QUEUE.md`** — what's left, what's in flight, what's done.

```markdown
# Feature batch

| # | Feature | Spec | Status | Failed passes | PR |
|---|---|---|---|---|---|
| 1 | Stylist availability | features/stylist-availability/spec.md | done | 0 | #12 |
| 2 | Admin day view | features/admin-day-view/spec.md | building | 1 | |
| 3 | Booking reminders | features/booking-reminders/spec.md | todo | 0 | |
```

Status is one of `todo`, `building`, `done`, `stopped`.

**`features/NOTES.md`** — what the runs worked out. **Append, never rewrite.** Told
to "update" this file the agent replaces it and last night disappears. One dated line
per finding, and only findings that would change what a later pass does.

---

## Batching

When the user names the features they want run:

**1. Check what's actually ready.** A feature is ready when `features/<name>/spec.md`
exists. Anything without one hasn't been through `new-feature` yet. **Name those out
loud** rather than quietly leaving them out, or they'll assume it's running tonight.

**2. Get the order right, and ask if you can't tell.** The queue runs top to bottom,
so if one feature builds on another the one underneath goes first. This is the last
moment a person is in the room; after this nobody is watching and the order is fixed.

**3. Write the file.** Everything new goes in as `todo`, zero failed passes, no PR.
**If a queue already exists, leave its rows exactly as they are and append underneath.**
A `done` row reset to `todo` means rebuilding and re-opening a PR for something already
finished and merged.

**4. Create `features/NOTES.md` if it's missing**, empty with a one-line header. The
loop appends to it and won't create it mid-run.

**5. Hand over the goal condition and stop.** Starting the loop is theirs.

```
/goal Use feature-batch on features/QUEUE.md. Post the queue table each pass. Met when no row is todo or building.
```

**Keep it that short.** The condition only needs a pointer, one thing to post, and
what met looks like. Everything else is already in this file, and the queue table
carries the status and the PR number in its own columns, so posting the table is the
evidence. The give-up rule doesn't belong in there either, because a given-up feature
is marked `stopped` and `stopped` already counts as met. A long condition is a sign
you're duplicating this file into a place the evaluator can't use anyway.

**If the queue is long, say something.** Every row is a feature built while nobody is
looking, paid for in real session limit. Eight rows is worth asking whether the last
three are wanted tomorrow or just on a list.

---

## Running: one pass

Do **one** unit of work per pass. Not one feature, one unit. A pass that changes
nothing still counts as a pass.

1. **Read `QUEUE.md` and `NOTES.md`.** Nothing else is known.
2. **Pick the work.** The topmost row that isn't `done` or `stopped`. If every row is
   one of those, the batch is finished. Say so and stop.
3. **If it's `todo`,** create its branch off main, named for the feature, and set the
   row to `building`.
4. **Build.** Spawn a **subagent** using the default task agent type, and give it the
   feature's spec path and nothing else. **Never build in this session.** It reads the
   spec, finds the highest thing not yet green, and fixes that one thing. Tell it not
   to declare the feature finished, because that isn't its call.
5. **Verify.** Spawn the **`adversary`** agent. See below, this is the part that gets
   skipped and it's the part that matters.
6. **Record.** Post the verdict into this conversation in full. Append anything worth
   carrying to `NOTES.md`. Update the row.
7. **If the verifier passed everything**, run the close-out in "Finishing a feature".
   Otherwise increment `Failed passes` and stop the pass.

**Only one feature is `building` at any time.** Running several at once means several
session limits burning, work colliding in the same files, and no shared memory of what
any of them worked out. It's slower in wall-clock, not faster.

---

## Both are subagents. Only one of them is custom

**Building and verifying both run in subagents, never in this session.** This session
is the loop, and its job is to read the queue, hand work out, and write state back. The
moment it starts building, its context fills with one feature's work and every later
pass gets worse.

**The builder is the default task agent type**, with no custom definition, because
everything that steers it is already in the spec: what to build, what done means, what
to run. An agent file for it would be the spec copied into a second place, and two
copies drift.

**The verifier is the custom `adversary` agent** in `.claude/agents/`, and it has to be
custom for one reason: what makes it work is what it's **denied**, and a spec can't deny
anything. It has no edit tools and it never sees the builder's conversation, and neither
of those can be written into a file the builder also reads.

They're never the same subagent as each other, and neither of them is you. The session that wrote the
code watched itself make every decision, so it already believes the work is right.
Asking it to check is asking it to agree with itself, and it will. That's the single
most common way an overnight run produces a queue full of `done` and an app full of
nothing.

**`adversary` gets:** the spec path, where the built thing is, and how to run it.

**`adversary` never gets:** the builder's conversation, its reasoning, or any claim it
made about what it did. **It also has no edit tools**, on purpose — an agent that can
fix things fixes them quietly and then passes the work.

It starts cold, reads the spec, runs the checks itself, and reports what it saw. If it
can only tell you the work is done because the builder said so, it isn't a verifier.

**Run the checks cheapest first, and stop at the first failure** instead of running the
rest:

1. does it build
2. does the feature do what the spec says it does
3. does it match the feature's own mock, at the hash route the spec names
4. is it actually good

Running the expensive ones against something that doesn't compile is how a night
disappears for nothing.

**Never accept a score or a summary as evidence.** Quote the individual results.
"Design checks passed" is not a result. "Hero matches at 1440, mobile nav overlaps the
logo at 390" is.

**An uncertain check is a fail.** An uncertain pass ends the loop early and ships
something broken. An uncertain fail costs one more pass. Those are not the same price.

---

## Finishing a feature

Done means the verifier passed every item on **two consecutive passes**, not one.
Screenshots and timings vary run to run and one green pass can be luck.

Then, in order:

1. Commit the verification output, screenshots and numbers, onto the branch. This is
   what makes it visible in the pull request: a comment can't hold an uploaded image,
   so the files have to be in the repo and linked by their raw URL.
2. Open the pull request with the `gh` CLI. Title is the feature. Body is the checklist
   state, the gate numbers, and the screenshots inline.
3. Set the row to `done` and record the PR number.
4. **Do not merge.** Merging is the user's, and an agent that merges its own work is
   back to grading itself.
5. Return to main. Take the next row on the next pass.

---

## When to stop

**Per feature:** the same item fails three passes in a row, set the row to `stopped`,
write why into `NOTES.md`, and move to the next feature. Something is wrong with the
approach and a fourth pass won't fix it. **One bad feature must not end the batch** —
that's the whole reason the queue is a list and not a prompt.

**The batch:** finished when every row is `done` or `stopped`. Say which are which.

**Never invent a turn cap or a time limit.** The queue's own statuses are the exit. A
third exit condition only ends runs that were still working.

---

## What this does not do

- **Set a feature up.** That's `new-feature`. If they name something with no spec, say
  so and point at that skill instead of writing a row for a spec that doesn't exist.
- **Merge anything.**

## Both tools

One copy per machine serves every surface (canon in `~/.ai-engineering/skills/`, mirrors
per IDE). **Subagent spawn syntax differs between surfaces** and some are unverified — if
the spawn instruction fails on yours, that's the thing to check first.
