# Corpus: ai-research

Finds evidence from outside this repository and reports it with numbered citations, or marks
a claim `[unsourced]` and leaves it marked. Dates everything, prefers the primary source over
a blog post about it, and closes with three cited directions somebody can act on tomorrow.

## Routes here

- "what does the state of the art say about sandboxing untrusted code" — the answer lives outside this repository, so it comes back with sources rather than with a file path.
- "compare the options for a background job queue and tell me which one you'd pick" — the things being compared are external, and the close is three cited directions, not a summary.
- "find me sources on whether this library is still maintained" — the request is for evidence and where it came from, which is the entire output of this skill.
- "is this still true? the post I'm reading is from last year" — dating the claim against the primary source is a step here, because a correct answer about last year's version is wrong.
- "what do the docs say about how this client retries" — the vendor's own documentation is the primary source, and where the docs and the source disagree this says which it acted on.
- "I heard that flag is deprecated, can you check" — if nothing can be sourced the claim comes back marked `[unsourced]` instead of confident.

## Refuses

- "where does the settings writer live" — use `/ai-explore`, because the answer is a path in this repository, not evidence from outside it.
- "walk me through how the dispatcher picks a hook" — use `/ai-explore`, whose triggers are "how does this work" and "trace this import chain" and whose claims are anchored to `file:line`.
- "CI is failing and I can't tell why" — use `/ai-debug`, because that is broken behaviour here with a cause at `file:line`, not a question about the world.
- "which of these two approaches should we build" — use `/ai-spec`, because deciding what to build needs options, a recommendation and the authority to proceed; research supplies the evidence a spec cites and stops there.
- "save what we just worked out about the vendor's rate limit so we don't lose it" — use `/ai-note`, because that finding is already ours and needs a commit stamp, while research goes and gets a finding we do not have yet.
- "look over my branch for anything I missed" — use `/ai-review`, because judging a diff is a different job from sourcing a claim.
