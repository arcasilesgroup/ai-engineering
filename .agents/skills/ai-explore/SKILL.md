---
name: ai-explore
description: >-
  Answers questions about this repository by reading it, anchored to file:line, and tours
  an unfamiliar area for somebody who has just arrived. Trigger for "where does X live",
  "how does this work", "why does it do that", "what depends on Y", "walk me through", "map
  this module", "trace this import chain", "onboard me". Not for evidence from outside this
  repository — use /ai-research. Not for diagnosing a failure — use /ai-debug. Not for
  judging a diff — use /ai-review.
license: Apache-2.0
compatibility: needs git
context: fork
background: false
---

# Read this repository and answer

## What it produces

An answer anchored to real paths. Every claim points at `file:line`, or it is marked as a
guess.

## Steps

1. Match the depth to the question, not to a flag. "Where is X" gets a path and a sentence.
   "How does this work" gets the flow. "Onboard me" gets a tour, and a tour is longer than
   five sentences by definition.
2. Match the words to who is asking. Somebody who does not code gets what the thing does and
   what it costs them when it breaks, with the file paths kept as evidence rather than as
   the answer; somebody who does gets the path first. Ask which if the question does not
   say, and never answer a business question with a call graph.
3. Find the real entry point before reading anything else. Working outward from the wrong
   file produces a confident answer about the wrong subsystem.
4. Follow one real path end to end and say what happens at each hop. Never summarise a flow
   from file names alone — that is the single most common way this goes wrong, and it reads
   exactly like a correct answer.
5. When the shape is the answer, draw it. Under 70 columns, and every box is a real file
   that exists:

   ```
   settings.json ──> chain.py ──> self_protect ──> exit 2
                        └───────> loop_guard
   ```
6. Explain what is here, not the pattern in general. If a textbook name applies, one clause
   is enough; the reader came for this codebase.
7. Name the pitfall by pointing at a line in this repository. A generic warning helps
   nobody; "this returns None on line 84 and the caller does not check" does.
8. If the answer is "it does not exist here", say that in the first sentence.

## Done when

- Every claim has a path, or is explicitly marked as unverified.
- The person could reach your conclusion by opening the files you named, in that order.
- Nothing was changed. This skill reads; it never writes.

## What this is not

Not a design review, not a refactor, and not an opinion about quality. If you spot
something genuinely dangerous, say it in one line at the end and move on.

- "I read the file names, so I can summarise the flow" — a flow summarised from file names alone is the single most common way this goes wrong; follow one real path end to end.
