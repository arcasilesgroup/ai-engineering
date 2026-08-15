---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0008"
title: "The five wave specifications are approved at exact digests"
date: "2026-08-15"
spec: "011"
status: "proposed"
supersedes: ""
---

# 0008. The five wave specifications are approved at exact digests

## Context and problem statement

Specifications 011 through 015 cover P1 to P5 of `.ai/reports/evolution-proposal/index.html`.
All five carry `status: draft`, and a draft authorises nothing: the repository's own rule
is that nothing may be implemented from a specification until a human approves it at an
exact digest. Four of the twenty requirements the 2026-08-15 audit records as FAILED sit
inside those drafts — the merge queue, the SBOM, the skill-evaluation runner and the
capability executor — and implementing any of them without an approval would be executing
a decision nobody had taken.

The status vocabulary is closed at `draft`, `shipped` and `superseded`
(`intent.py`, `madr.py`). There is no `approved`, and that is correct: approval is not a
state of the work, it is a fact about a person and a moment. It belongs in a record that
names the authority, the date and the bytes.

## Considered options

1. **Add an `approved` status to the vocabulary.** One word, and every reader of a spec
   would see it. It would also mean a fourth state in two validators and a schema, for a
   fact that is not about the specification's progress but about who agreed to it and when
   — and a status word carries no authority, no date and no digest.
2. **Record the approval as a decision, with the digest of each specification.** Nothing
   in the vocabulary changes; the specifications stay `draft` until their work ships. What
   exists afterwards is a record that a named authority approved exactly these bytes, which
   is the thing an auditor needs and a status word cannot carry.

## Decision outcome

Option 2. The five specifications are approved as of 2026-08-15 at these digests, each the
SHA-256 of `spec.md` at the moment of approval:

| specification | wave | digest (first 16) |
|---|---|---|
| `specs/011-surface-adapter-contract` | P1 | `7ab95b297fc0d937` |
| `specs/012-seven-capabilities-with-proof` | P2 | `6a0396bc8efd8a2a` |
| `specs/013-origin-first-coordination` | P3 | `41d79c4acfbdbc90` |
| `specs/014-security-baseline-no-false-pass` | P4 | `d19fbeffb619e02f` |
| `specs/015-pilot-without-instruments` | P5 | `01f955976d0fe09a` |

The authority is the repository owner, recorded in `.ai/intent.md` as
`lifecycle.approval.authority_role`. The approval covers the specifications as written and
nothing else: it approves no plan, and each wave's plan is a separate approval.

Two constraints survive it unchanged, because a specification cannot grant itself an escape
from the thing that governs it:

- **The one-writer rule stands.** Specification 013 approves the *shape* of origin-first
  coordination. `.ai/intent.md` conditions lifting one-writer on a separately approved P3
  **plan**, and D-013-07 says no plan derived from 013 may lift it without a human approval
  at an exact digest. This record is not that approval.
- **Nothing here authorises a push, a tag, a release, a publication, a global installation
  or a network call.** Specification 014's SBOM and attestation work needs a release, and a
  release needs its own consent.

## Consequences

Better: the four requirements blocked on an unapproved decision can be implemented, and an
auditor reading this repository in six months can check whether the specification that was
approved is the specification that shipped, byte for byte, rather than taking the word
`approved` on trust.

Worse: a digest is only as good as the discipline around it. Editing any of the five
specifications now invalidates its approval, and nothing in `just check` recomputes these
five hashes — so this record can go stale silently, which is the exact failure mode the
audit found in specification 010's own plan, where an invalidated plan digest sat beside an
approved one and no check read either. A test that recomputes them is owed, and until it
exists this table is a claim a reader has to verify by hand with `shasum -a 256`.
