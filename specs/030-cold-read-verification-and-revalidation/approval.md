---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "030"
title: "Specification 030 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "030"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-25-030"
---

# Specification 030 and its plan are approved at exact digests

## What is approved

`specs/030-cold-read-verification-and-revalidation/spec.md` supersedes part of spec 010's
target with the three research gaps that spec 029 did not close — B-030-1 cold-read verifier
with no write access and no access to the constructor's reasoning; B-030-2 guard coverage
declared as data, separated from reasoning prompts; B-030-3 finding-granular revalidation
that marks `fixed` only when the diff removed the trigger — and
`specs/030-cold-read-verification-and-revalidation/plan.md` sequences them into nine atomic
TDD tasks, each with its red fixture first.

The repository owner approved this record in conversation on 2026-08-25 (the same
instruction that directed spec 029's execution) and directed this plan's execution.
Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/030-cold-read-verification-and-revalidation/spec.md` | `17d08ba4b4e1fbfc51e48bd06551a4b27b49466f2f1699c3e712fe28271778a5` |
| `specs/030-cold-read-verification-and-revalidation/plan.md` | `0fce226edd9fd86d75b8f2dcfeae64d45bc28b1f8a473153c5021e4798e9d82d` |

## The one gated step

As with spec 029, the canonical approval record for this repository is a Structured MADR
under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree
returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026 (recorded in
`.ai/reports/014` and spec 028). Spec 030 does not authorise rewriting that history. This
record is the dossier-level approval at exact digests; the MADR promotion is the single
re-runnable step after an approved block repairs ADR 0025.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's nine tasks are the exact authorized
  work, one atomic commit each, nothing past task 9 opened by this record.
- It does not modify `.ai/intent.md`, `CONSTITUTION.md`, the one-writer rule or (beyond the
  cold-read corpus route it explicitly adds) any skill's authority.