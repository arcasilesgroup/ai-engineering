---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "036"
title: "Specification 036 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "036"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-036"
---

# Specification 036 and its plan are approved at exact digests

## What is approved

`specs/036-validate-adoption-and-close-boundary-delta/spec.md` supersedes spec 035's
implementation scope: a pre-flight audit found eight of 035's nine kernel behaviours already
ship in this tree (specs 013-034), recorded by module, contract symbol and provenance in the
validation table. The approved delta is three behaviours: **B-036-1** a
`decision_boundary` module (`Classified` = verdict + indexed reason; in-scope →
Always/Ask-first/Never; out-of-declaration → `None`/`U1..` + `CANNOT DECIDE` + blocks;
undeclared/malformed → `None`/`U0`; reads declarations from the `capability.py` manifest
surface; the thirteen `boundary` uses elsewhere avoid the name collision), **B-036-2** the
boundary rule on the two parse surfaces the routing harness admits (a `Not for … — …`
refusal in each of `ai-spec`/`ai-review`/`ai-verify` `SKILL.md` descriptions — the
`_REFUSAL` surface — and one quoted boundary case in each `corpus.md` — the `cases()`
surface — with the `skill_eval` baseline move argued in the same commit), and **B-036-3**
the validation freshness test (every table row: module + contract symbol + provenance
marker in the docstring). The spec names 035's digests by value, and 035's `approval.md`
carries the supersede note (commit 90286a0d); 035's spec and plan bytes are frozen.
`specs/036-validate-adoption-and-close-boundary-delta/plan.md` sequences the delta into six
atomic TDD tasks, red fixtures first.

The repository owner approved this record in conversation on 2026-08-26 (the `/ai-goal`
instruction, including the re-scope decision for spec 036 supersede 035) and directed this
plan's execution. Approved at these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/036-validate-adoption-and-close-boundary-delta/spec.md` | `8981a3bafd4c4ae2fe3c1635e5c5e7a2817d53a56634957e23120bed6140f218` |
| `specs/036-validate-adoption-and-close-boundary-delta/plan.md` | `f39a63b88ba19647aea1eef31a2457a048b078796f2aea4c1a7e5fe71874c222` |

Spec 036 was challenged twice and counselled twice before this record: challenge at the
first draft (the crashed run's findings — capability/evidence provenance, the "task T1"
wording — all incorporated), re-challenge at `b351f267` (**15 OK, 3 UNPROVEN**: the
fixture-less acceptance pytest runs, module↔spec-number provenance depth, the semantics of
all thirteen `boundary` uses), first council at the earlier draft (G1/G2/G3 incorporated),
and the re-council at `b351f267` (3 cross-read gaps + 5 cut/refuted; `just council` agreed:
`036 … 3 found only by the cross-read, 5 deleted`). The final spec at this digest closes
every re-council finding: the corpus rule relocated to the two real parse surfaces,
per-row contract symbols with a provenance assertion, the by-value supersede link written
(not promised), the thirteen-count correction, and the indexed `U0`/`U1..` reasons so
out-of-declaration is never confused with undeclared. The critique records were written
against the `b351f267` draft; the delta from that draft to this digest is exactly the list
above, re-checkable by reading the spec's diff (`git diff b351f267..HEAD -- specs/036-`).

## The one gated step

As with specs 028-035, the canonical approval record for this repository is a Structured
MADR under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this
tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 036 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

Task 6 runs the gate on the block. Nothing in this record claims a green that has not
happened: the boundary and validation fixtures do not exist until the approved plan writes
them (the spec's example counts are the goal, not a claim). The inherited
`tests/test_madr.py` failures are the only red this block may leave.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's six tasks are the exact authorized
  work, one atomic commit each, nothing past task 6 opened by this record.
- It does not touch specs 028-034 modules (`evidence.py`, `verify_cold.py`, `contract.py`,
  `cost.py`, `capability.py`, `trim.py`, `decision_fw.py` stay byte-identical; B-036-3 only
  asserts them), does not add a skill, does not modify `.ai/intent.md`, `CONSTITUTION.md` or
  the one-writer rule, and does not accept, weaken or relabel any normative requirement of
  the specs it validates.
- It is not a claim that the boundary behaviour exists: until `tests/test_036_boundary.py`
  passes its two cases inside `just check`, the delta is a proposal with red fixtures
  pending, exactly as the council's chairman wrote.
---

## Revision note (2026-08-26, after verification)

The spec at this approval's digests was verified; verification and review found three
concrete edits, applied and committed (`08c7cd8d`). The spec's digest moved:
`40491ca7199838f22f903c03ea28716589dfa0c0434a8252d34d9f0dcada130a`. The three edits:
(1) the Success example's count corrected `2 passed` → `5 passed` (the fixture ships five
tests; verify marked the old count stale); (2) the B-036-2 wording updated to the two real
parse surfaces `_REFUSAL`/`cases()`; (3) no normative behaviour changed. The plan digest
`f39a63b8` is unchanged. The build, review, verify and security records at `eecb10eb` cover
this revised spec.
