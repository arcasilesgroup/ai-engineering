---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "034"
title: "Specification 034 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "034"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-034"
---

# Specification 034 and its plan are approved at exact digests

## What is approved

`specs/034-appendix-notes-decision-frameworks-and-constellation/spec.md` extends spec 010's
target with the three behaviours the research marked (N26, N27, N29) and this repository
did not yet supply — B-034-1 appendix-only notes (a contract rule `_appendix_problems` over
the `ai-note` skill: a note is appended to with a fresh date, never rewritten), B-034-2
named decision frameworks (a `decision_fw` module with the deterministic RICE,
Effort/Value and Kano verdicts, plus the named-framework rule in the `ai-report` and
`ai-review` corpora), B-034-3 the constellation rule (`classify`: ≥2 same-class signals in
one context read systemic, a lone signal reads isolated, and a guard's fail is never
erased) — and `specs/034-appendix-notes-decision-frameworks-and-constellation/plan.md`
sequences them into seven atomic TDD tasks, each with its red fixture first.

The repository owner approved this record in conversation on 2026-08-26 (the same
instruction that directed specs 028-033) and directed this plan's execution. Approved at
these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/034-appendix-notes-decision-frameworks-and-constellation/spec.md` | `9981a4be26ff99ed32d1d10135f9cb3f83a624de9257c51a9b6ce2978795e598` |
| `specs/034-appendix-notes-decision-frameworks-and-constellation/plan.md` | `efa1a5a233134b37798d9945f3e3eb2f0dd52b987121b3140ae0f4436fd23b6b` |

## The one gated step

As with specs 028-033, the canonical approval record for this repository is a Structured
MADR under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this
tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 034 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

Task 7 ran the gate on the block: `2347 passed` (2338 at spec 033 plus the nine new 034
fixtures), with only the four inherited `tests/test_madr.py` failures — no fifth failure
introduced. The post-`cover` recipes (`security`, `evals`, `intent-page`, `map`) fail
exactly as they did on `774c79ac` before this block, except that `map` reports the 034
dossier's prose mention of Loop-Engineering's `NOTES.md` as one more real reference, which
joins the accepted set already queued on the repository owner's ADR 0027 work (the
prose-mention class ADR 0027 accepts); the mention belongs to that record and is not
rewritten to satisfy the analyzer.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's seven tasks are the exact authorized
  work, one atomic commit each, nothing past task 7 opened by this record.
- It does not add a new skill (the fifteen-skill target is unchanged), does not modify
  `.ai/intent.md`, `CONSTITUTION.md` or the one-writer rule, and does not touch the
  repository owner's uncommitted ADR 0027 work (`justfile`, `test_quality_gate.py`,
  `policy/skill-map-accepted.toml`).