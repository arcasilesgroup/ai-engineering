---
name: goal-writer
description: Writes the /goal condition that loops one feature. Sets the feature up first by running new-feature if it doesn't have a spec yet, then produces the goal command to paste into Claude Code or Codex. Use when the user says "write the goal for this", "loop this feature", "make this a goal", or describes something they want built in a loop. For a feature they intend to build themselves, use new-feature on its own instead.
---

# goal-writer

Writes **one thing**: the `/goal` condition that decides when a loop on a single
feature stops.

Everything that condition points at — the folder, the mock, the spec — comes from
`new-feature`. Run that first if it hasn't been run. Then write the condition.

```
new-feature  →  goal condition
(if needed)     (this skill)
```

**Why they're separate skills.** A feature you're going to build yourself in one
sitting still wants a mock and a spec, and it should cost nothing to skip the loop.
So `new-feature` stands alone and knows nothing about goals. This skill is the layer
on top, and it's the one you skip.

---

## 1. Make sure the feature is set up

A feature is ready when `features/<feature-name>/spec.md` exists.

**If it doesn't, run `new-feature` and let it finish**, including its approval gate.
Don't write the spec yourself — those rules live in that skill, and a second copy
drifts from the first.

**If it does, read it.** You need its section numbers and its stop condition, and
nothing else.

## 2. Write the condition

The evaluator gets **your condition and the conversation transcript**. Nothing else.

- It does **not** read files. It has never seen the spec.
- It does **not** run commands.
- It judges only what the agent has already said out loud in the session.

So `/goal follow features/x/spec.md` gives it nothing to judge except the agent's own
claim that it finished, which hands the verdict back to the agent. That's the failure
a loop exists to prevent.

### Three parts

1. **The pointer** — which spec to follow. One clause.
2. **The reporting clause** — what the agent posts into the conversation each pass.
   This is the only thing that makes the evaluator able to work at all.
3. **The met condition** — what has to appear in the transcript for it to be finished.

### Shape

```
/goal Follow <spec path>. Each pass, post <the evidence>. Met when <what appears in the transcript>.
```

### Example

```
/goal Follow features/services/spec.md. Each pass, post the §10 checklist state and the §8 gate numbers. Met when a pass shows every §10 box checked and every gate passing, and the pass right after it shows the same.
```

The fix order, the screenshot commands, the thresholds and the skills to load are all
absent, because the agent reads those out of the spec.

### Keep it short, and know what to leave out

- **Anything already in the spec.** The evaluator can't use it and it burns the
  character budget.
- **The give-up rule.** It's in the spec's stop condition, the agent reads it, and a
  loop that gives up says so in the transcript anyway.
- **An invented turn or time cap.** Only if the user asks, and only with a number they
  chose. A spec with its own stop condition needs no third exit.
- Condition limit is **4,000 characters**, and a good one is nowhere near it. Pointing
  at the spec is what keeps it short. **A long condition means you're duplicating the
  spec into the one place that can't read it.**

## 3. Hand it over and stop

Give them the condition. **Starting the loop is theirs.**

---

## Before handing over

- Could the agent satisfy the condition by saying "done" and showing nothing? Then the
  reporting clause is too weak.
- Do the section numbers you cited actually exist in that spec? Check them.
- Is anything in the condition already in the spec? Cut it.

## More than one feature

This skill loops **one** feature. Several features in one run is `feature-batch`,
which writes the queue and has its own condition. Don't write a goal that names two
specs.

## Both tools

The goal condition works on any surface with a native goal/loop mode (Claude Code, Codex,
and equivalents). One condition covers all of them: the surface's loop reads this skill's
contract, not an install path.
