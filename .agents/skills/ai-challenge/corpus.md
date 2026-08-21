# Corpus: ai-challenge

Takes a written specification and tries to break it by running its own sentences. Every
finding carries the command that produced it, and a finding without one is deleted before
the report is written. It reads the specification and the tree, and deliberately not the
conversation that produced either.

## Routes here

- "challenge this spec before I approve it" — the plain trigger: a written specification and a reader who wants it attacked rather than summarised.
- "is anything in here actually false" — each claim executed against the tree, and the ones that survive named as survivors.
- "what did the author assume without checking" — the assumptions the specification states, each turned into a command that would show it wrong.
- "attack this from outside, the author already questioned themselves" — the whole point: the self-challenge inside a spec is the same agent twice, and this is a different reader.
- "the numbers in this spec, do they still hold" — every count and measurement re-run rather than re-read.
- "tell me what breaks if this is wrong" — the consequence of each refuted claim, stated against the spec's own examples.

## Refuses

- "read this spec and tell me what it is missing" — use `/ai-council`, because absence is what several lenses find and this only refutes what is written.
- "write the spec" — use `/ai-spec`, because an accuser who wrote the text is grading their own paper.
- "review my diff" — use `/ai-review`, because that judges a change and this judges a document.
- "work out why this test is red" — use `/ai-debug`, because a red check needs a cause at `file:line` and this needs a claim to refute.
- "approve it once it survives" — refused: `ai-eng decide` needs a named person, and a challenger that can approve is not a challenger.
- "challenge it, but skip the commands, just tell me what feels weak" — refused: a finding without a command is an opinion, and this deletes those before writing.
