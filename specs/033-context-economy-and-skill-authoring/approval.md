---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "033"
title: "Specification 033 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "033"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-25-033"
---

# Specification 033 and its plan are approved at exact digests

## What is approved

`specs/033-context-economy-and-skill-authoring/spec.md` supersedes part of spec 010's target
with the four behaviours the research marked and this repository did not yet supply —
B-033-1 context trimmer (head/tail kept, elision marked, failure lines never dropped),
B-033-2 skillify extractor (a transcript becomes a contract-clean SKILL.md skeleton naming
steps, never chat), B-033-3 dispatcher/examples craft rule (branch bodies past the tier
bound must split into on-demand files), B-033-4 installed-version rule (a finding that
contradicts the installed bytes is dropped or unverified) — and
`specs/033-context-economy-and-skill-authoring/plan.md` sequences them into seven atomic
TDD tasks, each with its red fixture first.

The repository owner approved this record in conversation on 2026-08-25 (the same
instruction that directed specs 028-032) and directed this plan's execution. Approved at
these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/033-context-economy-and-skill-authoring/spec.md` | `320ae50f0b43e42f9d8f02e928435b81dcb148b03d12611540dce96d4083addc` |
| `specs/033-context-economy-and-skill-authoring/plan.md` | `5e85343bfecb9e3faa3a1805ff16240a0fe32bdb4c5b047f3af5c96aa91ba0e8` |

## The one gated step

As with specs 028-032, the canonical approval record for this repository is a Structured
MADR under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this
tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 033 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's seven tasks are the exact authorized
  work, one atomic commit each, nothing past task 7 opened by this record.
- It does not add a new skill (the fifteen-skill target is unchanged), does not modify
  `.ai/intent.md`, `CONSTITUTION.md` or the one-writer rule.