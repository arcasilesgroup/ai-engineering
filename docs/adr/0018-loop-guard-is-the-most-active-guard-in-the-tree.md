---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0018"
title: "loop_guard is the most active guard in the tree and is not deleted"
date: "2026-08-20"
spec: "022"
status: "accepted"
authority_role: "repository owner"
approval_ref: "no-hitl-2026-08-20"
approved_at: "2026-08-20T14:00:00Z"
supersedes: ""
---

# 0018. loop_guard is the most active guard in the tree and is not deleted

## Context and problem statement

The published subtraction plan carried a recommendation to delete `hooks/loop_guard.py` and,
with it, the `exception` verb — one of the ten — because `exception.py:171` declares
`--guard` with `choices=["loop_guard"]` and exists for nothing else. The reasoning given was
measured: 7,848 denials, all of them in 436 test sessions carrying exactly eighteen each,
and a failure arm that had never fired even inside the suite. Under the owner's direction
that anything unable to show it fires gets deleted, that is a deletion.

It was checked before the deletion rather than after, because it is a guard and 21 files
name it. The check refutes it.

Counting every block in the durable chain on this machine — 44,018 events across 1,605 files
— and splitting the sessions into those whose identifier looks like a fixture (`loop-*`,
`retry-*`, `suite-*`, `test-*`) and those that do not:

| guard | blocks in non-fixture sessions |
|---|---|
| **loop_guard** | **1,942**, across 241 distinct sessions |
| injection_guard | 72 |
| no_verify_guard | 45 |
| self_protect | 27 |

`loop_guard` has more denials in real sessions than every other guard in this repository
put together, by a factor of about thirteen. And the failure arm has fired: 845 of its
denials carry the failure text, in `retry-*` sessions, so the claim that it had never fired
even in the suite is false as well.

## Considered options

1. **Delete it as the plan says.** The plan's arithmetic was arrived at honestly and it is
   wrong: it read a sample of sessions as the whole, and read the absence of the failure arm
   in that sample as absence everywhere.
2. **Delete it anyway, on the argument that a guard firing 1,942 times is a guard people
   route around.** That argument has real force — this repository deleted
   `change_scope_guard` for 3 blocks against 670 bypasses. But the bypass ratio is the
   evidence there, and nothing here measures one for `loop_guard`. Deleting on a suspicion
   while a measurement says the opposite is the direction this product exists to refuse.
3. **Keep it, record why, and leave the bypass question open with the number that would
   answer it.**

## Decision outcome

Option 3. `hooks/loop_guard.py` stays, and so does the `exception` verb: it is the only way
a person grants a bypass of the only guard anybody has ever needed to bypass. The count of
verbs stays at ten.

What made this recommendation wrong is worth writing down, because it is a defect this
repository has a name for. The measurement behind it was real and its denominator was not:
it counted the sessions it could see and generalised. `docs/adr/0014` says a claim one
document makes about another gets a comparator; the same holds for a claim a plan makes
about a log.

## Consequences

The subtraction plan loses its largest single deletion in the surplus block — about 333
lines of guard and verb, plus their tests — and the tree keeps a control with more real
denials than the rest combined.

What stays open, and it is the honest next question rather than a hedge: nobody has measured
how often `loop_guard` is *bypassed*. That number is what condemned `change_scope_guard` at
3 blocks against 670, and it is the only number that could condemn this one. `ai-eng
exception --skip` is the command that would record it, and `bypassed` appears twice in the
whole chain. Two is not a ratio anybody should act on in either direction, and this record
does not pretend it is.
