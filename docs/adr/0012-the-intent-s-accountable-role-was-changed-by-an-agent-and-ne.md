---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0012"
title: "The Intent's accountable role was changed by an agent and needs a receipt"
date: "2026-08-17"
spec: "018"
status: "proposed"
supersedes: ""
---

# 0012. The Intent's accountable role was changed by an agent and needs a receipt

## Context and problem statement

`.ai/intent.md` is the file this framework reads to answer "who may grant anything here".
`decide.granted()` reads `lifecycle.approval.authority_role` out of it and refuses if the
role matches `agent` or `reviewer`; `spec._authority` compares that role against
`ownership.accountable_role` and refuses every governed verb when the two disagree. It is
the pre-approved policy the constitution names — "A human or an already approved versioned
policy supplies authority" — and it is the only one this framework has.

On 2026-08-17 an agent changed `ownership.accountable_role` in that file from
`repository maintainer` to `repository owner`, in commit `7ed87f13`. The change was correct
and it was instructed: `ai-eng spec new` refused on the mismatch, the agent reported that
the field was the owner's to decide and not its own, and the owner replied "pero hay que
arreglarlo" — it has to be fixed. The mismatch was two names for one person, and the
comparison is a string comparison.

The problem is not the change. It is that nothing in the repository says any of the above.
`git log` names the agent's commit; the tree carries no record of who instructed it or what
they said. Two owner approvals from the same session got receipts in `4c02d695`; this one,
which touches the file that grants authority, got none — which an independent reviewer
noticed while reading that commit beside this one.

## Considered options

1. **Leave it to `git log`.** The commit message says what happened and why. It is also the
   agent's own account of its own instruction, in a file the agent wrote, and this framework
   does not accept that shape anywhere else.

2. **Revert the field and ask again in writing.** Honest and expensive: it re-breaks every
   governed verb until the owner answers, to re-obtain an answer already given.

3. **Record it here, as a proposal, and let the owner accept or reject it.** The change
   stays, the account of it becomes a committed record rather than a commit message, and the
   `proposed` status says plainly that nobody has yet confirmed the account is true.

## Decision outcome

Option 3. This record states what was changed, by what, on whose instruction and in whose
words, and it stays `proposed` until the repository owner accepts it. Accepting it is the
owner confirming that the instruction quoted above is theirs; rejecting it says the field
must go back.

It grants nothing while it is proposed, which is the correct state for a record whose whole
subject is an agent having acted on the file that grants things.

## Consequences

Better: the one file that carries this framework's only standing authority now has a record
naming every hand that has touched it, and the record is refusable.

Worse: the field is live in the meantime. Every governed verb has been reading the changed
value since `7ed87f13`, so a rejection is a correction after the fact rather than a
prevention — which is what a receipt written after the change can be, and is the argument
for writing it before next time.

Also worse: this is a rule the repository does not yet enforce. Nothing refuses a commit
that edits `.ai/intent.md` without a record beside it. Making that a check is the obvious
next move and it is not this record's to make.
