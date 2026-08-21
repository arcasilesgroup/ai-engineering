---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0021"
title: "Specification 023 is approved at exact digests"
date: "2026-08-21"
spec: "023"
status: "accepted"
authority_role: "repository owner"
approval_ref: "ae523990"
approved_at: "2026-08-21T12:36:30Z"
supersedes: ""
---

# 0021. Specification 023 is approved at exact digests

## Context and problem statement

Specification 023 replaces the method behind `/ai-council`. It is above three files, so rule
1 requires an approved plan before any code. Unlike `0017`, this approval is not given under
the standing autonomous grant in `0016`: the repository owner read the brief at
`.ai/reports/004-brief-spec-023.html` and approved in his own words, in session, on
2026-08-21 — "lo apruebo". That is a person at a keyboard, and the record has to say which it
was, because a standing grant and a person reading the thing are not the same authority and a
reader cannot tell them apart afterwards from the word "approved" alone.

An approval cannot be written inside the file it approves: the digest of `spec.md` is a fact
about its bytes, and a paragraph inside it naming that digest changes it by existing. Record
`0009` established that and it holds here.

## Considered options

1. **Approve the specification and leave the plan for later.** The plan is where the cost
   actually lands — five commits, six files in one of them, a deleted control and a rewritten
   test — and approving a specification whose plan nobody has seen approves an unknown. `0017`
   named both files for that reason.
2. **Approve both files at their exact bytes.** What `0009`, `0013`, `0015` and `0017` do, and
   what the task envelope already enforces: `ai-eng spec show 023 --task <n>` refuses when
   either digest has moved.

## Decision outcome

Option 2. Approved at these bytes:

| file | SHA-256 |
|---|---|
| `specs/023-council-that-reads-itself/spec.md` | `862372fb0e241e42f193cf2d5e5d9a3214b4a9056846651c9736c3e78553af59` |
| `specs/023-council-that-reads-itself/plan.md` | `821b48e6cf6c570266edc0ea9b09eb7283bec0b7380d40a9e645841cb6415390` |

This approves those bytes and nothing else. It does not move the specification out of `draft`,
and it authorises no work beyond the five tasks that plan enumerates.

Two things inside those bytes are the owner's decisions rather than the author's, and they are
named here so that a reader does not have to reconstruct them from a conversation:

- **The chairman may conclude.** He was told that `docs/adr/0019` decides the opposite and that
  the evidence gathered for this specification points the same way, and he chose it anyway. The
  boundary that survives is constitutional and not doctrinal: `CONSTITUTION.md:53` forbids a
  model granting authority, not a model recommending. `0019` is reopened by its own record,
  which is task 1 of the plan and not this one.
- **`contract.CEILING` is deleted.** He was shown that the cap is binding on exactly one file,
  that its 80 lines are spent on frontmatter and blank lines rather than instructions, and that
  deleting it returns rule 12 to being a prompt with nothing bounding a skill's length
  afterwards. He chose deletion over changing what the cap counts. That regression is recorded
  in the specification's own unresolved risks and is not repaired by this work.

The boundary the specification names is part of what is approved: `SKILL_FOG_CEILING`,
`contract.fog`, `contract.prose`, `readiness.MAX_AGE_CEILING` and `tests/pilot_register._CEILING`
are outside this work. Task 2 proves the last two are byte-identical rather than asserting it,
which is the difference between a boundary and a hope.

## Consequences

The good one: the second half of the cycle now has something to run against. Until this record
existed the task envelope had two digests and no authority behind them, and `ai-eng report
blocked` would have been the honest answer to "why has nothing been built".

The one that gets worse, and it is the reason this paragraph is not shorter. This is the third
record in two days that reopens something a previous record closed — `0018` and `0019` were the
first two, and `0019`'s own consequences section says "two is not a pattern yet. Three would
be." This is three. What is different here is that a person made the call rather than a standing
grant, and what is not different is the direction: each one loosens something an earlier record
tightened. The check on that is a human reading the pull request, and nothing else. Saying so is
the only control this record can carry.

A second one, smaller and real: this specification's own instrument does not exist yet. Both
counts that `D-023-05` makes the evidence for reopening `0019` are, at the moment of approval, a
sentence in a plan. Task 3 makes them a command. If task 3 is cut, the approval bought a method
change with no way to tell whether it helped, and `EP-195` is exactly where it was.
