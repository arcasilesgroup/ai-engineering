---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0013"
title: "Specifications 016, 017 and 018 are approved at exact digests"
date: "2026-08-17"
spec: "018"
status: "proposed"
supersedes: ""
---

# 0013. Specifications 016, 017 and 018 are approved at exact digests

## Context and problem statement

Three specifications carry `status: draft`, and a draft authorises nothing: this repository's
own rule is that nothing may be implemented from a specification until a human approves it at
an exact digest. `0008` did that for the five wave specifications and `0009` for spec 010.
These three have had no such record.

They are not the same kind of document as the five waves, and the difference is worth stating
before approving them together. `016` is the thesis, `017` decides that a blocker is published
as a brief somebody can act on, and `018` is the repair pass for eight controls an independent
reviewer proved were not controls — the last of which is already implemented, because the
repairs were the emergency and the plan was written to govern them rather than to precede
them. Approving `018` is therefore approving a record of work already done, and saying so is
part of approving it honestly.

## Considered options

1. **Leave all three draft.** Accurate about the ceremony and wrong about the facts: `018`'s
   work is in the tree with a green gate on every commit, and a draft that describes shipped
   work is a record nobody can use to decide anything.

2. **Approve each separately, in its own record.** Three records for three digests, which is
   tidier and which nothing needs: they share one authority, one date and one reading, and
   splitting them buys a longer archive rather than a clearer one.

3. **One record, three digests, and the difference between them written down.** The owner
   approves the bytes as they stand; the record says which of the three describes work already
   landed and why that happened.

## Decision outcome

Option 3. The bytes approved are these, and no others:

| file | SHA-256 |
|---|---|
| `specs/016-the-thesis-nobody-owns/spec.md` | `f5c004ee5307af6ffb77f0c4d9e71059fbde7f6f96a723570d66637c561f428d` |
| `specs/017-decision-brief-as-an-artifact/spec.md` | `0c3a2cbc985a1a65d4506103dded9e1a1e3c477004a9577fc33787521bd3f2ac` |
| `specs/018-controls-a-reviewer-proved-were-not-controls/spec.md` | `f454fcca04d0b8a35d243bfcca63b945a38bc36f3db8d5c5b161b217281ebe9b` |
| `specs/018-controls-a-reviewer-proved-were-not-controls/plan.md` | `22d69e65bb677b5d8e426f308baa0642b8828fafa4145ff319a8ab9448cb865c` |

An edit to any of them without a new approval invalidates this record, which is what makes it
a gate rather than a sentence.

Approving these specifications approves what they decide. It does not tick a production-ready
box, it does not accept a risk, and it does not mark anything shipped — `018`'s plan carries
one task still open, and `017` is a decision whose implementation for consumers has not begun.

## Consequences

Better: `ai-eng decide --list` stops showing three drafts beside work that is in the tree, and
the fourth-pass ledger's rows about them rest on something.

Worse: `018` is approved after the fact. The plan governed the repairs as they were made and
the approval arrives behind both, which is the wrong order and is recorded here rather than
smoothed over. The cadence in `0011` asks for a plan before the block; the block that produced
`018` was a repair of live defects found by a reviewer, and stopping to obtain approval first
would have left two controls broken for longer. That trade is the owner's to disagree with,
and this record is where they would.
