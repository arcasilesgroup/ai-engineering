---
name: ai-verify
description: >-
  Runs the gate and the security lane and ticks each production-ready box beside the command
  that ticked it, or walks a spec's examples and marks each one against a real command.
  Trigger for "verify this", "is it ready", "tick the boxes", "does it do what the spec said",
  "check the acceptance criteria". Not for judging a diff — use /ai-review, which reads a
  change and this reads a claim. Not for finding a cause — use /ai-debug. It observes and
  never accepts: incomplete is the answer to every box and every example with no command
  pasted beside it.
license: Apache-2.0
compatibility: needs git; needs the ai-eng CLI on PATH
context: fork
background: false
disable-model-invocation: true
---

# Say what ran, and what it proved

## What it produces

Two things, never mixed. A production-ready table where every ticked box carries the command
that ticked it, and an acceptance table where every example carries its verdict.

## Verify — the boxes

1. Run `just check` and `just security`. Paste the output. A summary of a gate is not a gate.
2. For each of the eight production-ready boxes, write the command that proves it and the
   output it gave. A box with no command beside it is `INCOMPLETE`, and that is the answer,
   not a gap to fill in later.
3. A box that does not apply says `not applicable` and why in the same line. Assertion 19
   reads what sits beside each tick, so a tick with neither is a build that goes red.
4. Never tick a box on the strength of a run somebody described. `ai-eng spec checkpoint`
   reads receipts and says which of them is about this code; read its answer, not its age.

## Validate — the examples

1. Read the spec's `## Examples somebody can check`. `ai-eng spec show NNN` prints how many
   Given, When and Then lines it holds and how many name a command with its output.
2. Run each example's command. Mark it `PASS` when the output matches what the Then says,
   `FAIL` when it does not, and `INCOMPLETE` when the Then names no command — which is most
   of them, and saying so is the point.
3. The undecidable example is the one that matters. An example nobody can decide is not a
   pass and not a failure; report it as the third thing.
4. Do not repair the example. A Then that turned out to be wrong is a finding for `/ai-spec`,
   and rewriting it here is the reader marking their own paper.

## Done when

- Every box carries a command and its output, or `not applicable`, or `INCOMPLETE`.
- Every example carries a verdict, and the undecidable ones are counted separately.
- Nothing was accepted. This reports; a person or a gate decides.

## What this is not

Not a gate. `just check` is the gate and it runs in CI; this reads what it said. Not a
review — `/ai-review` judges a diff, and this judges whether a claim about one is true.
