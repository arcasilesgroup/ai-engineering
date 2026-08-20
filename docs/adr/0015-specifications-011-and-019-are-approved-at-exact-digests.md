---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0015"
title: "Specifications 011 and 019 are approved at exact digests"
date: "2026-08-19"
spec: "020"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-19T21:07:36Z"
supersedes: ""
---

# 0015. Specifications 011 and 019 are approved at exact digests

## Context and problem statement

The section specification 020 added to `docs/solution-intent.html` published five
specifications as waiting for an approval, each with the literal that would clear it. The
repository owner answered: "apruebo 010, 011, 018 y 019 con esos digests".

Two of those four did not need approving. `010` was approved at `364d83c56c7d…` by record
0009 on 2026-08-16, and `018` at `f454fcca04d0…` by record 0013; both digests still match
the files. The page asked for them anyway, because the collector reads `status: draft` from
the frontmatter and treats it as "nobody has approved this" — and record 0009 says in its own
last paragraph that this is exactly what `draft` does not mean: "Approval is a fact about a
person and a moment; it is not a state of the work". The surface built to make a wait visible
manufactured two waits that had already ended.

That defect is recorded here and repaired in the collector. This record carries only what was
genuinely new.

An approval also cannot be written inside the file it approves. Record 0009 established the
reason and it holds here: the digest of `spec.md` is a fact about its bytes, and a paragraph
inside it naming that digest changes it by existing.

## Considered options

1. **Treat all four as new and record them together.** Simpler to write, and it would put a
   second approval of `010` and `018` in the tree at digests already approved elsewhere. Two
   records saying the same thing is how a reader stops being able to tell which one is load
   bearing, and it would bury the collector defect rather than name it.
2. **Record only what was new, and name the defect that produced the other two.** Longer,
   and it is the only version where the tree afterwards says what actually happened.

## Decision outcome

Option 2. The repository owner approved these bytes on 2026-08-19, in a session that
published each digest on the page before the answer was given, so what was approved is what
the owner could read.

| file | SHA-256 |
|---|---|
| `specs/011-surface-adapter-contract/spec.md` | `7ab95b297fc0d9376664a6890649f479133be6caa462ddeca54d052bed4c3836` |
| `specs/019-the-four-days-two-specs-cost/spec.md` | `cbba04d99d3663e3e169c8fe12b4358e0422335cc72e988ef90bf44661751ef0` |
| `specs/019-the-four-days-two-specs-cost/plan.md` | `fe9a3923fae5f6b2cbbdfcb7b8c0fca041c6ac1d6d24ddcff3195bd2a380dac3` |

The plan digest for `019` is here because it was approved earlier in the same session, in its
own answer that named it: "apruebo spec cbba04d9 y plan fe9a3923".

`specs/011-surface-adapter-contract/plan.md` is **not** approved. The owner's answer named
specification digests, which is what the page published, and nothing was said about that plan.
It hashes to `f8976a2bbc81cf156a7d59e9f8caa609afa48093fa07ce0b230f4c84b8be589c` today and
that number is recorded as an observation, not as an approval.

Approving these bytes approves the specifications as they stand. It does not move either out
of `draft`, for the reason record 0009 gives. It ticks no production-ready box, grants no
capability, and authorises no implementation of `011`, which has no approved plan.

## Consequences

`011` and `019` stop appearing in the waiting section once the collector reads these records,
which is the repair this defect earns. Until that repair ships, the page keeps asking, and
the page keeps being wrong in the direction that costs an owner their attention rather than
the direction that costs the tree its safety.

One thing gets worse and it should be said. The number of places a reader must consult to
answer "is this approved" is now four records rather than three, and nothing enumerates them.
A reader who checks only `docs/adr/0015` concludes `010` is unapproved. The collector repair
has to read all of them or it will trade one false statement for another.

A second finding fell out of the same measurement and is not addressed here.
`specs/016-the-thesis-nobody-owns/spec.md` was approved by record 0013 at `f5c004ee5307…`
and no longer hashes to it. Its bytes changed after approval and nothing in the tree says so.
An unapproved edit to an approved specification is a worse silence than an unapproved
specification, and it is invisible today because `016` has no plan and the collector drops it
before it is ever considered.
