# Corpus: ai-spec

Writes the governed record of a decision before code exists: the evidence, the problem, at
least two real options, one recommendation and the self-challenge against it, the
assumptions, the unresolved risks, observable examples and the authority for proceeding. It
produces `specs/NNN-slug/spec.md` in the user's repository, and it is not code, not a plan,
and not permission the agent gave itself.

## Routes here

- "let's add rate limiting to the public API" — something that does not exist yet needs its options weighed and a recommendation recorded before anybody opens an editor, which is this skill and not /ai-plan.
- "how should we handle sessions that expire mid-upload?" — the question is which behaviour is right rather than which file to touch, so it needs at least two real options and one recommendation, not a task list.
- "what's the best approach for storing the audit trail?" — asking for an approach is asking for a recommendation that has been challenged once with its strongest realistic failure case.
- "I'm thinking about splitting the worker into two services" — a half-formed intention is exactly where the fixed constraints, the intended outcome and the harm of leaving it unchanged get written down.
- "we need to decide whether the CLI or the hook owns the check" — a decision that constrains later work belongs in a record with named assumptions and unresolved risks, not in a conversation nobody can audit.
- "write the spec for the new export format" — asked for by name, and the authority basis has to be named or the result is `INCOMPLETE`.

## Refuses

- "break this down into tasks I can start on" — use `/ai-plan`, because turning an approved spec into numbered tasks that each name one file, one check and one rollback is that skill's whole job.
- "the scope changed, re-plan it" — use `/ai-plan`, because a spec is not reopened to reshuffle work; only a spec that turned out to be wrong comes back here.
- "review this, is it merge-ready?" — use `/ai-review`, because judging a diff that already exists runs the opposite direction from writing the record before code exists.
- "compare the options for background job libraries and find sources on them" — use `/ai-research`, because the evidence is outside this repository and every claim has to carry a numbered citation or stay marked `[unsourced]`.
- "CI is failing on main, why?" — use `/ai-debug`, because broken behaviour needs a cause named at `file:line` before anybody decides what to build.
- "save this, the settings writers merge rather than replace" — use `/ai-note`, because a non-obvious behaviour that cost real time is a committed note stamped with its commit, not a project decision.
- "ship it and open the PR" — use `/ai-ship`, because landing the work is commits, a changelog entry and a pull request, none of which a decision record contains.
