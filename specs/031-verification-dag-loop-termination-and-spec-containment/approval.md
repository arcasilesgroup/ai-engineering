---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "031"
title: "Specification 031 and its plan are approved at exact digests"
date: "2026-08-25"
spec: "031"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-25-031"
---

# Specification 031 and its plan are approved at exact digests

## What is approved

`specs/031-verification-dag-loop-termination-and-spec-containment/spec.md` supersedes part
of spec 010's target with the three research gaps that specs 029 and 030 did not close —
B-031-1 verification DAG and lane merge (each node's output verified before the next
consumes it; dedupe by file:line, global re-rank, surfaced conflicts); B-031-2 loop
termination (done only after two consecutive identical green runs; a no-op pass counts);
B-031-3 spec self-containment (`self_contained` refuses conversation leaks; `section`
resolves a part by number) — and `specs/031-verification-dag-loop-termination-and-spec-containment/plan.md`
sequences them into seven atomic TDD tasks, each with its red fixture first.

The repository owner approved this record in conversation on 2026-08-25 (the same
instruction that directed specs 029 and 030) and directed this plan's execution. Approved at
these exact bytes:

| file | SHA-256 |
|---|---|
| `specs/031-verification-dag-loop-termination-and-spec-containment/spec.md` | `d9faa431916bf25cb6511ca868e2966e5d679c3879395ae3f9c8b670293c2600` |
| `specs/031-verification-dag-loop-termination-and-spec-containment/plan.md` | `909e3310ef81c66d59c1e0ec3f8f630ca6acd853e16a7eff655a78dba98c27d1` |

## The one gated step

As with specs 029 and 030, the canonical approval record for this repository is a Structured
MADR under `docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this
tree returns `INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026 (recorded in
`.ai/reports/014` and specs 028/029/030). This was re-confirmed on 2026-08-25: `ai-eng
decide "Specification 029 approved" --spec 029` refused INCOMPLETE. Spec 031 does not
authorise rewriting that history. This record is the dossier-level approval at exact
digests; the MADR promotion is the single re-runnable step after an approved block repairs
ADR 0025.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It does not modify `src/ai_engineering/dag.py` (spec 013's claim ordering); B-031-1 is a
  distinct verification module.
- It is not a standing autonomous grant: the plan's seven tasks are the exact authorized
  work, one atomic commit each, nothing past task 7 opened by this record.
- It does not modify `.ai/intent.md`, `CONSTITUTION.md`, the one-writer rule or (beyond the
  ai-spec corpus rule it explicitly adds) any skill's authority.