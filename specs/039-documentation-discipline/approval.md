---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "039"
title: "Specification 039 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "039"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-039"
---

# Specification 039 and its plan are approved at exact digests

## What is approved

`specs/039-documentation-discipline/spec.md` makes the framework's documentation discipline
a reachable standard: **B-039-1** a `references/documentation-writer.md` beside `ai-report`
(the writing-for-agents levers — context pointers, the two loads, leading words, pruning,
completion criteria — plus ASD-STE100 controlled-language rules), reached only through the
three authoring corpus routes, never always-loaded; **B-039-2** three differentiated quoted
routes (one per `ai-spec`, `ai-plan`, `ai-report`) plus a `Not for … — …` refusal for a doc
that hands an agent a vague completion bound or restates the environment. **D-039-01**
records the technical-writer decision: the claude-agents agent stays an insumo (runtime-
specific, STE100-free); the discipline — and STE100, which the agent lacks — ships in the
reference. **D-039-02** states file governance: the homes stay the machine-listed ones
(doctor, PO-16, `docs/tools.md`); the spec adds the writing standard, no new home.
`specs/039-documentation-discipline/plan.md` sequences the work into four atomic TDD tasks,
red fixture first.

The repository owner approved this record in conversation on 2026-08-26 (the /ai-goal
instruction, the documentation discipline request, and the technical-writer/STE100
analysis) and directed this plan's execution. Approved at these exact bytes (canonical —
the plan's tick column is masked before signing):

| file | SHA-256 |
|---|---|
| `specs/039-documentation-discipline/spec.md` | `d7afbbcbded45b7ea47c1132c5a9e1167b90a9c966706036deaf6c0c646f333e` |
| `specs/039-documentation-discipline/plan.md` | `f4804d24017fd62a3ff32b9447a744e9233b1792fd91bed7e9f415b5c06f8069` |

Spec 039 was challenged and counselled before this record: `challenge.md` (5 WRONG — the
roadmap rows 8/10 anchor, `just doctor` vs `ai-eng doctor`, the homes description, the
self-falsifying STE100 grep-zero, the pre-ticked Production-ready boxes — 3 UNPROVEN,
8 OK) and `council.md` (3 gaps found only by the cross-read, 4 deleted; `just council`
agrees: `039 … 3 found only by the cross-read, 4 deleted`). The spec at this digest
incorporates every correction: row 10 only, `ai-eng doctor`/PO-16 wording, differentiated
routes (no fork), un-ticked fixture-dependent boxes, and the STE100-scope reword.

## The one gated step

As with specs 028-038, the canonical approval record is a Structured MADR under
`docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree
returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 039 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

Task 4 runs the gate on the block. Nothing in this record claims a green that has not
happened: the 039 fixture and reference do not exist until the approved plan writes them.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's four tasks are the exact authorised
  work, one atomic commit each, nothing past task 4 opened by this record.
- It does not port the technical-writer agent, does not add a skill, does not add a hard
  STE100 parser, does not modify `.ai/intent.md` (updated this session by the owner's
  instruction), `CONSTITUTION.md` or the one-writer rule.
- It is not a claim that the documentation discipline ships: until
  `tests/test_039_documentation.py` passes its three cases inside `just check`, the
  reference and routes are red fixtures pending, exactly as the council's chairman wrote.