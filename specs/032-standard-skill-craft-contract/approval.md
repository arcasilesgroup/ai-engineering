---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "032"
title: "Specification 032 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "032"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-25-032"
---

# Specification 032 and its plan are approved at exact digests

## What is approved

`specs/032-standard-skill-craft-contract/spec.md` supersedes part of spec 010's target with
the four authoring disciplines the research marked and this repository did not yet check —
B-032-1 anti-rationalization table (a skill names an excuse and answers it), B-032-2 output
contract (`## What it produces` names the artifact), B-032-3 Incorrect/Correct rule pairs
(where a rules section exists), B-032-4 load tiers (body ≤500 lines, scripts in `scripts/`)
— added as checked rules in `contract.audit_one`, the same way spec 027 added its four
smell rules — and `specs/032-standard-skill-craft-contract/plan.md` sequences them into
seven atomic TDD tasks (four rules, one repair, two proofs), each with its red fixture
first.

The repository owner approved this record in conversation on 2026-08-25 (the same
instruction that directed specs 028-031) and directed this plan's execution. Approved at
these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/032-standard-skill-craft-contract/spec.md` | `0552c29a5517edf3eb345f529ad89d8ca4a5c42d6f0cb88a83619841bfb77c75` |
| `specs/032-standard-skill-craft-contract/plan.md` | `047af421730a5e44527b08e7e37440e2406fd892e0622f587690951f5eeffc2d` |

## The one gated step

As with specs 028-031, the canonical approval record for this repository is a Structured
MADR under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this
tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026 (recorded in
`.ai/reports/014` and specs 028-031). Spec 032 does not authorise rewriting that history.
This record is the dossier-level approval at exact digests; the MADR promotion is the single
re-runnable step after an approved block repairs ADR 0025.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's seven tasks are the exact authorized
  work, one atomic commit each, nothing past task 7 opened by this record.
- It does not modify the four spec 027 smell rules, the corpus or routing files.
- It does not modify `.ai/intent.md`, `CONSTITUTION.md` or the one-writer rule.