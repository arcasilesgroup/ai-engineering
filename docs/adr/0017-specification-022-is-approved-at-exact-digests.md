---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0017"
title: "Specification 022 is approved at exact digests"
date: "2026-08-20"
spec: "022"
status: "accepted"
authority_role: "repository owner"
approval_ref: "no-hitl-2026-08-20"
approved_at: "2026-08-20T14:00:00Z"
supersedes: ""
---

# 0017. Specification 022 is approved at exact digests

## Context and problem statement

Specification 022 deletes the chain anchor. It is above three files, so rule 1 requires an
approved plan before any code, and `docs/adr/0016` is the standing authority under which
that approval is given — it names the scope, the date and the role, and it names this class
of work explicitly.

An approval cannot be written inside the file it approves: the digest of `spec.md` is a fact
about its bytes, and a paragraph inside it naming that digest changes it by existing. Record
0009 established that and it holds here.

## Considered options

1. **Fold this approval into 0016.** One record fewer, and it would make a standing grant
   and a specific approval the same object — so a reader could not tell which digests the
   owner saw and which the grant merely permitted. 0015's own consequences section already
   records what happens when one record has to answer two questions.
2. **A record per specification, naming its digests.** What 0009, 0013 and 0015 do.

## Decision outcome

Option 2. Approved at these bytes, under the standing authority of 0016:

| file | SHA-256 |
|---|---|
| `specs/022-the-anchor-nobody-could-answer-for/spec.md` | `5bf8c039a6d13a1442c5687b04d911c14f0d2a15848f4808faa48d9f512d2efc` |
| `specs/022-the-anchor-nobody-could-answer-for/plan.md` | `bae2a86cd56dc7a031bcff5acf4f65991716c1678fcc7af1e9c90142da0bf3fa` |

This approves those bytes and nothing else. It does not move the specification out of
`draft`, and it authorises no work beyond the eight tasks that plan enumerates.

The boundary that specification names is part of what is approved: `accept._anchored_bytes`,
`accept._anchored_path`, `acceptance._anchored`, `readiness._anchored`, the `anchor=`
argument of `spec_transaction`, `uninstall.anchors` and `decide._require_anchored_io` are a
path-safety reader and are outside this work. Task 8 turns that sentence into a test, which
is the difference between a boundary and a hope.

## Consequences

`ai-eng audit verify` keeps every property a reader depends on except the three history
verdicts, which have produced no finding in this repository's life while printing a false
alarm on every commit.

One thing gets worse and it is written into the specification rather than left for somebody
to discover: after this lands, `audit verify` still exits 1 on this machine. The 22 broken
links stay, the owner declined to run `ai-eng audit account` before the deletion, and nothing
in this work repairs them. What stops is the line on every commit. The exit code does not.
