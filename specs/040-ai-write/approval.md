---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "040"
title: "Specification 040 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "040"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-040"
---

# Specification 040 and its plan are approved at exact digests

## What is approved

`specs/040-ai-write/spec.md` adds the framework's technical-documentation surface:
**B-040-1** the `ai-write` skill (model-invoked, under the audit contract, pointing at
`.agents/skills/ai-report/references/documentation-writer.md` (039) as its single standard, no-cache and checkable
completion criteria), **B-040-2** routing without duplicating (changelog→/ai-ship,
spec→/ai-spec, note→/ai-note, issue→/ai-report, and the reverse routes into ai-write),
**B-040-3** a verification gate (real files, no environment restatement, checkable
sections; the three states and the `not-covered` vocabulary defined by the fixture, and a
second reader via the normal diff review). **D-040-01** keeps the claude-agents
technical-writer an insumo and names the surface `ai-write`, not `ai-docs` — which spec 010
`:414` records as an absorbed skill. The spec records the count pin (README/AGENTS move to
"eighteen"), the map situation (208 pre-existing reals; this block accepts only its own
references with a dated record), and the complete capability entry.
`specs/040-ai-write/plan.md` sequences the work into seven atomic TDD tasks, red fixture
first.

The repository owner approved this record in conversation on 2026-08-26 (the /ai-goal
instruction and the "dale, vamos a ello" for the ai-docs→ai-write surface) and directed
this plan's execution. Approved at these exact bytes (canonical — the plan's tick column is
masked before signing):

| file | SHA-256 |
|---|---|
| `specs/040-ai-write/spec.md` | `bb58013786634c7b209957bcefbc7354be8479cb9fca16ea9625644a1540ed7a` |
| `specs/040-ai-write/plan.md` | `f28ca85c0bd687fd4d5e375e299d26fce7e2a8fd8e6a365ecd256fe47b1b9004` |

Spec 040 was challenged and counselled before this record: `challenge.md` (18 findings:
4 WRONG — the roadmap rows anchor, the count pin, the not-covered citation (035/038, not
036/039), the map absorption claim — 3 UNPROVEN, 11 OK) and `council.md` (4 gaps found only
by the cross-read, 4 deleted; `just council` agrees: `040 … 4 found only by the cross-read,
4 deleted`). The spec at this digest incorporates every correction, including the critical
M1: the name `ai-docs` is recorded as an absorbed skill in spec 010 `:414`, so the surface
is named `ai-write`.

## The one gated step

As with specs 028-039, the canonical approval record is a Structured MADR under
`docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree
returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 040 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

Task 7 runs the gate on the block. Nothing in this record claims a green that has not
happened: the 040 fixture, the skill, the capability entry and the count move do not exist
until the approved plan writes them.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's seven tasks are the exact authorised
  work, one atomic commit each, nothing past task 7 opened by this record.
- It does not port the claude-agents technical-writer, does not revive the absorbed
  `ai-docs` name, does not clean the 208 pre-existing map reals, and does not modify
  `.ai/intent.md` (updated earlier this session), `CONSTITUTION.md` or the one-writer rule
  beyond the README/AGENTS count prose task 5 names.