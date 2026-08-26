---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "035"
title: "Specification 035 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "035"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-035"
---

# Specification 035 and its plan are approved at exact digests

## What is approved

`specs/035-adoption-of-reference-patterns/spec.md` adopts the eight meta-patterns the
research (`.ai/research`, 17 leaf reports + `SINTESIS.md`, 16 references) distilled as
checked behaviours of the framework, sequenced R0 → R1 → R2: B-035-1 executed evidence in
gates (CHECK/EXPECT/EVIDENCE, ticked-without-evidence reads unmet), B-035-2 verifier
isolation (auditor reports with no edit tools, `NOT COVERED` never `PASS`, reconciled with
the one-writer rule), B-035-3 one shared scope/severity/honesty contract, B-035-4 boundary
classifier (Always/Ask-first/Never), B-035-5 anti-rationalization + red flags + exit
criteria, B-035-6 cost pre-flight with a configurable threshold and route-by-model, B-035-7
skill schema at `policy/skill-schema.json` with tool gating, B-035-8 context economy
primitives (R0 slice; area-gated rules and instruction minimalism sequenced to R1), B-035-9
named decision frameworks (RICE / Effort/Value / Kano, unnamed ranking refused) — R1
(review-router, full-review, goal-writer, two-job CI gate) sequenced behind the R0 wave
criterion, and R2 deliberately unauthorised until an owned spike validates its cost and
state risk (D-035-06) — and `specs/035-adoption-of-reference-patterns/plan.md` sequences
R0 + R1 into seventeen atomic TDD tasks, each with its red fixture first, an explicit
wave-completion criterion, and a stated list of deliberate omissions.

The repository owner approved this record in conversation on 2026-08-26 (the `/ai-goal`
instruction that also directed the research and the spec) and directed this plan's
execution. Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/035-adoption-of-reference-patterns/spec.md` | `0bf6cb029f4c858bda7502c73b69eb72cab33f9b1b16c8962f13c62f88ca0677` |
| `specs/035-adoption-of-reference-patterns/plan.md` | `22c24bbbb907d9cde40a7db2ba1d3e4ddbe0fe7cc0a415ed7769152bec45062d` |

The spec was challenged and counselled before this record: `challenge.md` (0 WRONG,
13 OK, 11 UNPROVEN — the seven `-k` fixture lines and four Production-ready bullets all
target the not-yet-written `tests/test_035_adoption.py`, reported honestly, never faked)
and `council.md` (five lenses, cross-read, chairman) with 4 gaps found only by the
cross-read and 5 findings cut or refuted, `just council` agreeing with the written counts.
The revision commit `92016631` closes every standing council finding: the wave-completion
criterion, the B-035-4→B-035-7 schema dependency, the temporal-guard resolution for
B-035-3, the one-writer reconciliation in B-035-2, the cost threshold in B-035-6, the
named comparison method for this record's own options, the explicit eight meta-patterns,
and the red-first framing of every example.

## The one gated step

As with specs 028-034, the canonical approval record for this repository is a Structured
MADR under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this
tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 035 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

Task 17 runs the R1 gate on the block; task 12 runs the R0 gate. Neither has run yet —
nothing in this record claims a green that has not happened. The inherited
`tests/test_madr.py` failures are the only red this block may leave, asserted as unchanged
by the plan's gate tasks.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's seventeen tasks are the exact
  authorized work, one atomic commit each, nothing past task 17 opened by this record, and
  R2 begins only through a new spec change that names a spike result.
- It does not add a new skill, does not modify `.ai/intent.md`, `CONSTITUTION.md` or the
  one-writer rule, and does not touch the repository owner's uncommitted work on the
  `justfile`, `test_quality_gate.py` or `policy/skill-map-accepted.toml`.
- It is not a claim that the adopted behaviours exist: until `tests/test_035_adoption.py`
  passes its seven cases inside `just check`, the R0 kernel is a proposal with a
  fixture-shaped hole, exactly as the council's chairman wrote.