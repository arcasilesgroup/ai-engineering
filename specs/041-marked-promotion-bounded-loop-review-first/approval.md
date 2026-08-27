---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "041"
title: "Specification 041 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "041"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-041"
---

# Specification 041 and its plan are approved at exact digests

## What is approved

`specs/041-marked-promotion-bounded-loop-review-first/spec.md` closes the three gaps spec
031 left in the orchestration story: **B-041-1** the `[X]` promotion trigger (a decision
is born in its spec and `ai-eng decide` promotes only entries its author marked `[X]`
under `## Decisions` — `marked_decisions` in `spec.py`, the refusal in `decide.py`, the
criteria in ai-spec paso 10), **B-041-2** the spec↔challenge/council loop bounded at two
rounds per spec digest on the skill layer (canonical digest — the bytes `approval_bytes`
signs — and `loopgate.done()` wired when an orchestrator automates the cycle), and
**B-041-3** the `[parallel] policy` recording review-first (ai-review gates
ai-verify/ai-security, which may pair as fork contexts when review is green and the host
can run both). The spec documents the sourced evidence (report 019: [1][2][4][5][8][12])
and the council's two cross-read corrections — the canonical-digest identity of the round
count and the marker's position away from the plan tick column.
`specs/041-marked-promotion-bounded-loop-review-first/plan.md` sequences the work into
seven atomic TDD tasks, red fixture first.

The repository owner approved this record in conversation on 2026-08-26 (the /ai-goal
instruction that corrected the plan to six steps and recorded the option-1 decision:
skill-layer bound now, loopgate wiring when the orchestrator exists) and directed this
plan's execution. Approved at these exact bytes (canonical — the plan's tick column is
masked before signing):

| file | SHA-256 |
|---|---|
| `specs/041-marked-promotion-bounded-loop-review-first/spec.md` | `4b517c55a63279aa51d4b164fcaef1b42c89775b43fd4b29c7dbf8c2d6c6d388` |
| `specs/041-marked-promotion-bounded-loop-review-first/plan.md` | `34e12196438873d2b0fd3178d81bc9d1ea2383d7e6a785411d97e5927411c3dc` |

Spec 041 was challenged and counselled before this record: `challenge.md` (7 findings:
1 WRONG — ai-spec paso 10 still teaches the deleted `--madr` flag, which the CLI refuses
with exit 2, and plan task 4 removes it — 2 UNPROVEN, 4 OK) and `council.md` (2 gaps
found only by the cross-read, 2 deleted; `just council` agrees:
`041 … 2 found only by the cross-read, 2 deleted`). The spec at this digest incorporates
every correction, including the critical one: the two-round cap counts the canonical
digest `approval_bytes` signs, not the raw file bytes.

## The one gated step

As with specs 028-040, the canonical approval record is a Structured MADR under
`docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree
returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 041 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's seven tasks are the exact authorised
  work, one atomic commit each, nothing past task 7 opened by this record.
- It does not wire `loopgate.done()` into an orchestrator (D-041-02: that is a later
  spec's task, when the orchestrator exists), does not hard-delete the
  `ai-eng decide "<title>"` path (D-041-01: the marker filter is the gate), and does not
  modify `.ai/intent.md`, `CONSTITUTION.md` or the one-writer rule.