# Corpus: ai-cycle

Walks one request through the governed cycle by loading each stage's own skill body and
following it. It stops at a brief a person reads, and it has no field in which an approval
could be written.

## Routes here

- "run the whole cycle on this" — the plain trigger: one request, every stage in order, stopping where a person is needed.
- "take this from an idea to a spec I can approve" — the first half exactly: research, spec, challenge, council, brief.
- "/ai-cycle build 021" — the second half, once an approval record with the specification's digest exists.
- "carry on now that I have approved it" — the same, and it refuses if the bytes moved after the approval.
- "do the research and the spec and get it challenged, then wait for me" — the halt is the feature, not a limitation.
- "keep going through the reds, do not stop at the first one" — the repair loop: two attempts per task and failing recipe, then a page.

## Refuses

- "just write the spec" — use `/ai-spec`, because one stage is cheaper called directly than wrapped in the other five.
- "just review my diff" — use `/ai-review`, for the same reason.
- "approve it yourself and carry on" — refused: the brief is where this stops, and an approval is a record a named person writes.
- "skip the council, it always agrees" — use `/ai-council` and read why it cannot agree; dropping a stage silently is what this exists to prevent.
- "the gate is red, just turn that check off so we can ship" — refused: no suppression, no skip mark, no loosened bound; an honest raised ceiling is an escalation with its arithmetic.
- "run all six build stages in parallel to save time" — refused: one writer owns the commits, and the critics run apart for independence rather than for speed.
