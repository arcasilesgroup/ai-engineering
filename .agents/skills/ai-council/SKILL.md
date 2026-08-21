---
name: ai-council
description: >-
  Reads one specification through several declared lenses that never see each other, and
  collects the gaps each one can demonstrate with a command. Trigger for "council this spec",
  "read this from several angles", "what is this specification missing". Not for attacking the
  claims it makes — use /ai-challenge, which executes sentences; this asks what is absent. Not
  for judging a diff — use /ai-review. It has no vote, no verdict and no field in which the
  word approved could be written: a council that approves is the same agent speaking twice.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
disable-model-invocation: true
---

# Several angles, no agreement to reach

## What it produces

`specs/NNN-slug/council.md`: one section per lens, each a list of gaps. A gap names what the
specification does not say, and the command a reader can run to see the absence for
themselves. A section that found nothing says so and stays — a lens that never comes back
empty is a lens inventing work.

## The rule that makes it not one agent three times

A council of models that debate reach consensus, and consensus is what this repository
already measured and rejected: an earlier run of three ended with "the three members arrived
at the same point", having been handed three pre-written options to rank. So:

1. **The members are lenses, not opinions.** Cost, reversibility, the undecidable path, what
   is assumed without proof, the example nobody wrote. Each is a question, not a personality.
2. **A lens reads the specification and nothing else.** Not the other lenses, not the plan,
   not the conversation. A lens that sees another's answer is anchored by it.
3. **No vote and no ranking.** There is no field to disagree in. Two lenses naming the same
   gap is corroboration and both entries stay.
4. **A gap without a command is deleted before the file is written.** That is the whole of
   the difference between a gap and an opinion.

## Steps

1. Take the specification's digest. If it moved since it was written, stop and say so.
2. Run each lens over the specification alone, and write its section.
3. Delete every finding that carries no command. Say how many were deleted.
4. Write the file. Do not summarise it: a summary is where a verdict grows.

## What this is not

It grants nothing and blocks nothing. `ai-eng decide` is where a person records a decision,
and this produces material for that person to read. It also does not run in parallel by
contract: where the host can start several lenses at once it does, and where it cannot it
runs them one after another, and the file is identical either way.

## Done when

Every lens has a section, every finding carries a command, the deleted count is written down,
and nothing in the file says whether the specification is good.
