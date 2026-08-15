# Corpus: ai-explore

Answers questions about this repository by reading it, anchored to `file:line`, and tours an
unfamiliar area for somebody who has just arrived. Every claim points at a real path or is
marked as a guess, and nothing is changed: this skill reads, it never writes.

## Routes here

- "where does the settings file actually get written?" — a location question about this repository gets a path and a sentence, which is reading here rather than searching outside in /ai-research.
- "how does the dispatcher decide which hook to run?" — the answer is one real path followed end to end, with what happens at each hop, from the files in this tree.
- "why does it exit 2 there?" — the behaviour is intended and the reason lives in the code, so this is a reading question, not the broken-behaviour question /ai-debug takes.
- "what depends on the repo ceiling constant?" — a dependency question answered by following real references, each one anchored to a line.
- "walk me through what happens when a guard denies something" — a walkthrough is a flow, and the shape gets drawn only when the shape is the answer.
- "map the hooks directory for me" — a tour of an area, with every box a file that exists.
- "onboard me, I start on this repo on Monday" — a tour is longer than five sentences by definition, and this is the skill whose depth matches the question.

## Refuses

- "what does the state of the art say about sandboxing hooks?" — use `/ai-research`, because the evidence is outside this repository and every claim has to carry `[N]` or stay marked `[unsourced]`.
- "what do the vendor's docs say about this setting?" — use `/ai-research`, because going to the primary source outside this tree is that skill's first step, not reading our files.
- "is this still true in the current release?" — use `/ai-research`, because dating a claim against an upstream version needs a source, and this repository is not one.
- "the guard is denying a file it should allow" — use `/ai-debug`, because a failure needs a cause named at `file:line` and a check that fails for that reason, not a tour.
- "look over this diff and tell me whether it's safe" — use `/ai-review`, because judging a change at its boundaries is not the same as explaining what is there, and this skill is not a design review.
- "how should we restructure this module?" — use `/ai-spec`, because deciding what to build needs two real options, a recommendation and a named authority.
- "write that trap down so the next person doesn't lose an afternoon" — use `/ai-note`, because a hard-won finding becomes committed markdown with a header, not an answer in the conversation.
