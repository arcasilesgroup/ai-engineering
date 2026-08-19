# Corpus: ai-verify

Runs the gate and the security lane and ticks each production-ready box beside the command
that ticked it, or walks a spec's examples and marks each one against a real command. It
observes and never accepts: incomplete is the answer to a box or an example with no command.

## Routes here

- "verify this is ready to ship" — the eight production-ready boxes, each ticked by a command or left incomplete.
- "tick the boxes on spec 014" — the plain trigger: a spec with a production-ready section and nothing proving it.
- "does the code do what the spec said" — the acceptance question, answered against the spec's own examples rather than against the diff.
- "check the acceptance criteria pass" — each Given/When/Then run as a command, marked pass, fail or incomplete.
- "which of these boxes can we actually claim" — the honest half: a box with no command beside it is incomplete and says so.
- "the gate is green, are we done" — no; green is one box, and this says which of the other seven are unproven.

## Refuses

- "review my diff" — use `/ai-review`, because that judges a change and this judges whether a claim about one is true.
- "work out why the check fails" — use `/ai-debug`, because a red check needs a cause at `file:line` and this only reports what it observed.
- "write the examples for me" — use `/ai-spec`, because an example is a decision about what would count as working and this reads them.
- "fix the Then that turned out wrong" — use `/ai-spec`; rewriting an example here is the reader marking their own paper.
- "open the pull request now the boxes are ticked" — use `/ai-ship`, because publishing is a separate authority and this accepts nothing.
- "just mark it green, the gate passed locally" — refused: a box carries the command that ticked it, and assertion 19 reads what sits beside each tick.
