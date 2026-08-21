# Corpus: ai-council

Reads one specification through several declared lenses that never see each other, and
collects the gaps each one can demonstrate with a command. It has no vote and no verdict,
and a finding without a command is deleted before the file is written.

## Routes here

- "council this spec before I sign it" — the plain trigger: one specification, read by several lenses that do not see each other.
- "read this from several angles" — cost, reversibility, the undecidable path, what is assumed without proof, the example nobody wrote.
- "what is this spec missing that nobody noticed" — absence is what this looks for, which is the half a single reader is worst at.
- "I want more than one reading before I approve" — several sections a person reads, rather than one summary that hides where they disagreed.
- "did anybody think about what happens when this is reversed" — the reversibility lens, run as its own reader.
- "is the cost of this written down anywhere" — the cost lens, which reports the absence and the command that shows it.

## Refuses

- "test whether the claims in it are true" — use `/ai-challenge`, because that executes sentences and this asks what is absent.
- "review this diff" — use `/ai-review`, because that judges a change and this reads a specification.
- "write or fix the spec once the lenses report" — use `/ai-spec`, because a council that rewrites the text is no longer reading it.
- "have the members vote and tell me the verdict" — refused: there is no field to disagree in, and a council that agrees is one agent speaking twice.
- "record the decision the council reached" — use `ai-eng decide`, which needs a named person; this produces material for that person.
- "run the lenses in parallel and tell me it was faster" — refused: where the host can it does, where it cannot it runs them in turn, and the file is identical either way.
