---
name: ai-challenge
description: >-
  Grills a written specification from outside it: at most ten questions per round, one
  at a time, each anchored to the sentence it attacks and decided by executing the
  commands behind it. Trigger for "challenge this spec", "attack this decision", "is
  this spec true", "grill this before I approve it". Not for judging a diff — use
  /ai-review, which reads a change against a spec and cannot also be its accuser. Not
  for finding a cause in code — use /ai-debug. It never approves, revises or rewrites:
  it returns findings that carry a command, the author folds them into the
  specification, and a person decides what they mean.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
disable-model-invocation: true
---

# Ask the tree, not the author

## What it produces

At most ten questions per round, returned to the session, each carrying the sentence
it attacks, the command that tested it, what the command printed, and its verdict.
The author folds the round into the specification's `## Grill` section, so the
verdicts land in the document they attack; no file is written beside it.

## Why it is not the section inside the spec

`ai-spec` requires the author to challenge their own recommendation once, and that
section is worth keeping — but the questioner and the answerer are the same reader,
and a reader can only reason about what they already wrote. Measured on this repository: four of twenty
specs carry that section, and not one of the four contains a command or a file
reference. Three claims in one of them were false, and executing them is what found
it.

## Steps

1. Read only the specification and the tree. Not the plan, not the pull request, not
   the conversation that produced it — a challenger who reads the author's reasoning
   inherits it.
2. Choose what to attack: the sentences whose truth changes a decision — a count, a
   path, a behaviour, a claim about another file, a "no code reads this". The
   exhaustive sweep of every sentence is what this replaced: 044's challenge executed
   every one, spent 70 minutes and 28 command blocks, and made two load-bearing
   corrections — a cap bounds what the judgement used to price.
3. Run the command before asking the question. The sentence gets executed, not
   re-read: a count gets counted, a path gets opened, a behaviour gets run. Paste
   what came back, including when it agrees.
4. Return at most ten findings, worst first, one question at a time. `WRONG` when the
   tree says otherwise, `UNPROVEN` when nothing in the tree can decide it and say
   which — those are different problems for the author.
5. The author folds each finding into `## Grill` and revises the attacked sentences
   in place. A round that found nothing checkable to attack returns that as the
   answer `nothing checkable failed`, and the section carries it.

## The loop is bounded

At most two rounds against the same spec digest — the canonical bytes `ai-eng spec
show` prints. A revision changes the digest and reopens the count; the second round
against an unchanged digest is the last. At the ceiling, write the outstanding
findings worst first and hand the page to the person. `loopgate` is the
orchestrator's instrument, not yours: the skill layer's bound is this one, and the
two-identical-greens rule is what an automated cycle runs when it exists.

## What this is not

It is not an approval and not a rejection. It never edits the specification: an
accuser who rewrites the charge is not one. And it is not a second opinion — a
finding either carries a command somebody else can run, or it does not exist.

- "Every sentence checked out, so the spec is true" — a challenge reports what it could not test too; only what it managed to check reads as a clean bill of health.

## Done when

The `## Grill` of the specification it attacked carries the round: its `ran:`
declaration, every question beside the command, the output and the verdict, and the
attacked sentences revised in place rather than answered beside.
