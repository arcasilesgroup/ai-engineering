---
name: ai-research
description: >-
  Finds evidence from outside this repository and reports it with numbered citations, or
  marks a claim [unsourced] and leaves it marked. Ends with three cited directions worth
  taking. Runs in a forked context so the reading does not spend the main window. Trigger
  for "what does the state of the art say", "compare the options for", "find sources on",
  "is this still true", "what do the docs say about". Not for questions whose answer is in
  this repository — use /ai-explore. Not for diagnosing a failure here — use /ai-debug. Not
  for deciding what to build — use /ai-spec.
license: Apache-2.0
compatibility: needs network access for anything beyond the local machine
context: fork
background: false
---

# Find out, and say where it came from

## What it produces

An answer where every claim carries `[N]` and a source list, or carries `[unsourced]`.

## Steps

1. Say what would change depending on the answer. Research with no decision behind it is
   reading, and it should be labelled as reading.
2. Go to the primary source. A vendor's own documentation beats a blog post about it, and
   the source code beats the documentation when they disagree — which they do.
3. Prefer running it to reading about it. A claim you verified by executing it is worth
   more than five that agree with each other, and it is the difference between "the docs
   say it can deny" and "a denial executed on this machine".
4. Date everything. A correct answer about last year's version is a wrong answer.
5. Mark disagreement rather than resolving it silently. If two sources conflict, say so and
   say which one you would act on and why.
6. Anything you could not source is `[unsourced]`, and it stays that way in the final
   answer. Removing the marker because the claim feels right is the failure this format
   exists to prevent.
7. Close with three directions worth taking, each cited. Not a summary — a recommendation
   somebody can act on tomorrow.

## Done when

- Every claim is either cited or marked.
- The sources are named well enough that the person can open them.
- You said which claims you verified yourself, and how.

## What this is not

Not a survey for its own sake. If the answer turns out to be short, the report is short.
And `[unsourced]` says which kind it is: no source exists, or there was no way to look
from here. A report of unsourced markers that never says the network was unreachable is
reporting green while blind.
