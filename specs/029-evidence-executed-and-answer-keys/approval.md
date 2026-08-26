---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "029"
title: "Specification 029 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "029"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-25-029"
---

# Specification 029 and its plan are approved at exact digests

## What is approved

`specs/029-evidence-executed-and-answer-keys/spec.md` supersedes the four research gaps of
spec 010 target (B-029-1 skill evals with planted defects; B-029-2 answer key decided
before the gate; B-029-3 recheck / claimed-is-not-passed; B-029-4 cost calibration gate)
and `specs/029-evidence-executed-and-answer-keys/plan.md` sequences them into ten atomic
TDD tasks, each with its red fixture first.

The repository owner approved this record in conversation on 2026-08-25 and directed the
plan's execution. Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/029-evidence-executed-and-answer-keys/spec.md` | `b9dff346ed117ced7f981eb50584b2b21a90230b537c2dcdd693be412f13d601` |
| `specs/029-evidence-executed-and-answer-keys/plan.md` | `86fa1337a7b0e57a37ca6dfcf1ac5c0bcdb075c1da4ba01e2f74974f008540dd` |

## The one gated step

The canonical approval record for this repository is a Structured MADR under `docs/adr/`
(`ai-eng decide "<title>" --spec 029` writes `status: proposed`; a named person accepts).
Creation is gated on `madr.validate` returning PASS, which on this tree returns
`INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026 (forbidden frontmatter fields
baked into that block's history `bde39e75`→`8f25f903`, documented in `.ai/reports/014` and
`specs/028-writer-model-recorded`). Spec 029 does not authorize rewriting that history.

This record is therefore the dossier-level approval at exact digests, and the MADR
promotion is the single re-runnable step after an approved block repairs ADR 0025. Until
then, this goal claims no ADR promotion and adds no new MADR failure; unlike spec 028 there
is no `blocked.md` because the work itself is not blocked — only the formal promotion is.

## What this approval does not do

- It is not an acceptance of any risk (see the spec's `## Accepted risks`, which stays
  empty until a named owner accepts).
- It is not a standing autonomous grant: the plan's ten tasks are the exact authorized
  work, each commit atomic, each running its module's suite in the same chain as the
  commit, and nothing past task 10 is opened by this record.
- It does not modify `.ai/intent.md`, `CONSTITUTION.md`, the one-writer rule or any skill.