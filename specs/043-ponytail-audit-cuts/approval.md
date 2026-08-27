---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "043"
title: "Specification 043 is approved at its exact digest"
date: "2026-08-27"
spec: "043"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-27-043"
---

# Specification 043 is approved at its exact digest

## What is approved

`specs/043-ponytail-audit-cuts/spec.md` authorizes the surviving ponytail-audit cuts as
four ordered commits — (a) duplicated primitives into shared homes, (b) production-dead
wrappers deleted with their tests dying in the same commit, (c) engine shrinks that
preserve exact public behavior, (d) hook-layer unsanctioned duplication cuts only.
Five audit findings are withdrawn as governance-enclosed and are NOT authorized for
deletion: `answer_key`, `decision_boundary` (spec-042 orphan register),
`imagery.findings` (PROVEN row EP-254's evidence command executes it),
`surface.receipt_binds_version` (PROVEN row EP-016 names it), and
`executor.Sandbox.connect/.secret` + `capability.Action.connect/use_secret`
(EP-176's secret-gating evidence exercises `.secret`; `.connect` is kept pending an
owner wiring it into a named evidence command or accepting its removal). The
spec_transaction Windows backend stays this run: deleting a platform arm of spec-010's
publication design decision needs a superseding spec with an owner behind it.

## The two critic rounds, and what they changed

**Round one** (challenge.md: 2 WRONG, 4 UNPROVEN, 6 verified; council.md: 5 standing
WRONG/UNPROVEN clusters plus 4 cross-read gaps) corrected the draft before approval:
the invented gate numbers (`2403 passed/5 failed`) were replaced by an honest
post-commit baseline sentence; the false claim that a spec-010 "dated risk record"
shelters the Windows backend was withdrawn — spec-010's Accepted risks section reads
"None", and the shelter is now stated correctly as prudence about a design decision,
not governance obedience; the half-fabricated CONSTITUTION paraphrase ("unaccepting
needs the same authority") was dropped; the backwards baseline assumption now names the
tests that die with their subject in the same commit (`ui.ask` → tests/test_ui.py);
the premature `[X]` tick on D-043-01 was unticked (the box stays open until the commits
land); E-3's missing dedup-criterion example was added (grep count == 1 per primitive);
the two sanctioned hook duplications were named so D-043-01(d) is executable by a
stranger; ADRs carry no changelog duty conflict — rule 4's second clause is now inside
D-043-01's own text.

**Post-challenge research sweep** (.ai/reports/020, gitignored): every dynamic-resolver
site in the tree was checked against the cut list; none reaches any target. The five
withdrawals above came from that sweep.

## Approved at these exact bytes

| file | SHA-256 |
|---|---|
| `specs/043-ponytail-audit-cuts/spec.md` | `sha256:35c27a2f7c5f12e61a13e06897b607ca375c2a679c8632e2628d30d63c1f8be8` |

## Known blockers at approval time

The repository gate reads 4 red in `tests/test_madr.py` on clean HEAD (verified on a
pristine checkout of e78bcb2f): docs/adr 0024-0027 declare MADR v1 but lack the schema-
required `supersedes` field, so `madr.validate` returns INCOMPLETE for reasons that
predate spec 043 and are independent of it. A parallel repair of exactly those records
is in flight in this worktree from another writer. Spec 043's commits therefore claim
green for their own diffs, not for the whole suite; `ai-eng audit verify` output is
reported verbatim with the four failures attributed to HEAD.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` section carries
  none; unresolved risks stay unresolved).
- It is not a promotion of D-043-01 to a MADR: the box is unticked until the commits
  land, and `ai-eng decide` remains the person-gated step after that.
- It does not authorize touching `.ai/intent.md`, `CONSTITUTION.md`, the one-writer
  rule, any PROVEN ledger row's evidence, or the files another writer currently holds
  dirty (`src/ai_engineering/madr.py`, `docs/adr/002[4567]-*.md`).
