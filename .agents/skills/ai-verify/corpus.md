# Corpus: ai-verify

Runs the gate and the security lane and ticks each production-ready box beside the command
that ticked it, or walks a spec's examples and marks each one against a real command. It
observes and never accepts: incomplete is the answer to a box or an example with no command.

## Routes here

- "verify this is ready to ship" — the eight production-ready boxes, each ticked by a command or left incomplete.
- "tick the boxes on spec 014" — the plain trigger: a spec with a production-ready section and nothing proving it.
- "does the code do what the spec said" — the acceptance question, answered against the spec's own examples rather than against the diff.
- "check the acceptance criteria pass" — each Given/When/Then run as a command, marked pass, fail or incomplete.
- "apply the spec's answer key" — the decided standard, read from `answer-key.yaml` beside the approved spec: each binary check is re-executed (`--recheck`) and marked pass, fail or `BLOCKED: U<n>`; a touched unknown is never scored.
- "what does the answer key say about this deliverable" — the same application, from a reader's question rather than a gate.
- "verify this cold" — read-only verifier, no write tools, never the constructor's conversation: applies the answer key with `--recheck` and reports what it saw, not what the builder said. An uncertain check is a fail.
- "verify this and also decide whether to grant the access" — refuse the grant, because an out-of-declaration decision reports `CANNOT DECIDE` and blocks (use /ai-spec to scope what is being decided).

## Refuses

- "review my diff" — use `/ai-review`, because that judges a change and this judges whether a claim about one is true.
- "work out why the check fails" — use `/ai-debug`, because a red check needs a cause at `file:line` and this only reports what it observed.
- "write the examples for me" — use `/ai-spec`, because an example is a decision about what would count as working and this reads them.
- "fix the Then that turned out wrong" — use `/ai-spec`; rewriting an example here is the reader marking their own paper.
- "open the pull request now the boxes are ticked" — use `/ai-ship`, because publishing is a separate authority and this accepts nothing.
- "just mark it green, the gate passed locally" — refused: a box carries the command that ticked it, and on a draft nothing but the writer is checking, because assertion 19 only reads a shipped spec.
- "judge the deliverable by taste" — use `/ai-spec`; a decided standard is written at spec time. If none exists, the honest answer is `BLOCKED`, not an invented opinion.
- "review it warm" — use `/ai-review`; a review that sees the constructor's reasoning defends the work. Cold-read is read-only and never sees it.
