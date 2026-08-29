---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0039"
title: "The read-back gate carries an unattended branch."
date: "2026-08-29"
spec: "048"
status: "accepted"
authority_role: "repository owner"
approval_ref: "54bdfa50"
approved_at: "2026-08-29T12:09:24Z"
supersedes: ""
---

# 0039. The read-back gate carries an unattended branch.

## Context and problem statement

Spec 048's intake gate says nothing is scaffolded until the owner confirms a
plain-words read-back of the idea. `/ai-goal` says the whole cycle runs in one pass
and "no step of an unattended run waits for input". The council executed those two
texts against each other and found the deadlock: in a headless run the confirmation
cannot happen, so either the goal skill's no-wait rule or the intake gate has to bend.
This decision constrains every future gate that demands a human yes: the cycle's
unattended half must be able to pass without one, and passing without one must leave a
mark a later reader can find.

## Considered options

1. **Record the read-back as unconfirmed and carry on.** The clause lands in step 0;
   at scaffold time the author moves "unconfirmed" into the spec's
   `## Assumptions and unresolved risks`, where `ai-verify`'s example can grep for it.
   The attended flow keeps its hard gate; the headless flow keeps its no-wait rule; the
   absence of a human yes becomes a visible line instead of a hidden hang.
2. **Let intake wait for the owner even in a goal run.** Rejected: it breaks the goal's
   defining promise ("this one runs without me") and converts a designed pause into an
   unbounded stall — exactly the hung-fork failure spec 047's wall budget was written
   to catch, but a fork parked on a question is worse than a slow one.
3. **Skip the read-back silently when unattended.** Rejected: a green nobody earned is
   the failure this product cures; the record would read as if the owner confirmed.

## Decision outcome

Option 1: "under an unattended goal the run records that read-back as unconfirmed and
carries on" is part of the pinned step-0 text, and `.agents/skills/ai-spec/references/intake.md` names where
the note lands when the scaffold arrives.

## Consequences

Better: `/ai-goal` stays true unattended and the confirmation duty stays enforced
attended; every goal-run spec carries one honest line either way. Worse: the unconfirmed
record is trust deferred, not trust earned — the person reading the shipped spec must
notice the line, and nothing forces an agent to write it except the same pinned prose
that forces everything else in this cycle; a later mechanization (refuse `spec show`
PASS on a goal-run spec without the line) is allowed by this record and owed to rule 12
if it resolves the same way a third time.
