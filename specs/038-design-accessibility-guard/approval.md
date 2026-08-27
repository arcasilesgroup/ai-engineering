---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "038"
title: "Specification 038 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "038"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-038"
---

# Specification 038 and its plan are approved at exact digests

## What is approved

`specs/038-design-accessibility-guard/spec.md` completes ai-design's accessibility floor:
the council and challenge proved the premise "nothing in the framework says it" false
(ai-design already names `WCAG 2.2 AA` as the release floor and measures contrast; the
ai-review motion lens respects reduced-motion), so the spec's delta is the two missing
pieces and the honest exit — **B-038-1** a `_accessibility_problems` contract lane (a
designed surface either names the a11y basics — contrast/keyboard/focus/reduced-motion —
confirmed by the existing verify steps, or exits `INCOMPLETE: a11y not-covered <reason>`;
a silent pass is refused), and **B-038-2** `references/accessibility.md` beside ai-design
(the concrete checks and the `not-covered` rule, laden only on verify; the roadmap's design
skills stay insumos, never framework skills). `specs/038-design-accessibility-guard/plan.md`
sequences the work into five atomic TDD tasks, red fixture first.

The repository owner approved this record in conversation on 2026-08-26 (the /ai-goal
instruction, roadmap row 16, and the request that accessibility be inside ai-engineering's
design, not an agent) and directed this plan's execution. Approved at these exact bytes
(canonical — the plan's tick column is masked before signing):

| file | SHA-256 |
|---|---|
| `specs/038-design-accessibility-guard/spec.md` | `567a29d216b9508878b75efb8e63bb264f3d1abc72584ef36351cd65fccbde6e` |
| `specs/038-design-accessibility-guard/plan.md` | `42aba4af89af117042e821b8ff09d31838434d7a53fa4d7e461ccec835487800` |

Spec 038 was challenged and counselled before this record: `challenge.md` (20 findings:
2 WRONG — the floor's existence and the 17-AL-Design citation — 6 UNPROVEN, 12 OK) and
`council.md` (4 gaps found only by the cross-read, 5 deleted; `just council` agrees:
`038 … 4 found only by the cross-read, 5 deleted`). The spec at this digest incorporates
every WRONG correction: the delta is the *completion* of the floor (keyboard, focus,
`not-covered`), never its duplication, and the false premise is replaced by the measured
state.

## The one gated step

As with specs 028-037, the canonical approval record is a Structured MADR under
`docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree
returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 038 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

Task 5 runs the gate on the block. Nothing in this record claims a green that has not
happened: the 038 fixture does not exist until the approved plan writes it.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's five tasks are the exact authorised
  work, one atomic commit each, nothing past task 5 opened by this record.
- It does not add a skill, does not re-audit the insumo design skills (`~/.claude/skills`
  stay outside the framework's audit), does not modify `.ai/intent.md`, `CONSTITUTION.md`
  or the one-writer rule, and does not accept, weaken or relabel any normative requirement
  of the specs it completes.