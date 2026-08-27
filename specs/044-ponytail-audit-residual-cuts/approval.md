---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "044"
title: "Specification 044 and its plan are approved at exact digests"
date: "2026-08-27"
spec: "044"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-27-044"
---

# Specification 044 and its plan are approved at exact digests

## What is approved

`specs/044-ponytail-audit-residual-cuts/spec.md` records the residual over-engineering
cuts after spec 043's pass: **D-044-01** deletes the twelve true caller-less modules
(constellation, decision_fw, decision_boundary, intake, trim, versions, lane_merge,
loopgate, skillify, verify_cold, evidencing, answer_key) together with every test file
the AST sweep shows importing them, the orphan register (`policy/module-status.toml`,
`wiring.module_status`, `tests/test_orphan_register.py`), and corrects the register's
stale rows for `sbom`/`scan`/`skillmap`/`coverage` by removing the rows, not the
modules — the council proved those four have gate-time callers (justfile:47,107,268;
tests/evals/score.py:131). **D-044-02** keeps the spec_transaction Windows backend,
`imagery.findings`, `surface.receipt_binds_version` and `executor.Sandbox.connect`
under the same governance enclosure 043 recorded. **D-044-03** dedups the shared
primitives (one digest-pinned loader, `text.flat_yaml` behind `acceptance`, one
ls-files reader, `wiring.cli_answers` behind `doctor`, `functools.cache` console memo,
`re.fullmatch` hex check) preserving exit codes, refusal messages (codes and fragments,
the contract the suite actually asserts) and fail-closed arms. Family (c) removes the
zero-caller constants (`spec.self_contained`/`_LEAKS`, `model_router.bail_out`,
`audit.replay`, root `answer-key.yaml`) and folds the one-caller relics
(`cli.UNEXPECTED`, `solution_intent.NOT_HASHED`, `spec._document_relations`).
Family (d) migrates the test-suite duplication and deletes the `noqa: E402` idiom from
the fifteen surviving pytest modules, enforcing rule 3.

`specs/044-ponytail-audit-residual-cuts/plan.md` sequences the work into eight atomic
tasks: family (a) first, dedup families (b1-b3), the dead-weight family (c), the
test-migration families (d1-d2), and the block-close gate run. Rollback per task is a
commit-family `git revert`.

The repository owner approved this record in conversation on 2026-08-27 (the `/ai-goal`
instruction: "finish this without me, give me something to test", applied to the
2026-08-27 ponytail audit) and directed this plan's execution. Approved at these exact
bytes (canonical — the plans' tick columns are masked before signing; the current plan
file carries no ticks yet, so the digest below is of the file as written):

| file | SHA-256 |
|---|---|
| `specs/044-ponytail-audit-residual-cuts/spec.md` | `b213c1d7d7660b93df7c82960526e3ba447ad18ca4310cee4fc51ab476808d5d` |
| `specs/044-ponytail-audit-residual-cuts/plan.md` | `193cb17b6da88ef1f54eb1647382e7a4036cb14d34aacc15bb5404733228b397` |

## The two critic rounds, and what they changed

The spec was challenged once and counselled once against this branch. **Challenge round
one** (specs/044-ponytail-audit-residual-cuts/challenge.md: nine findings, two
load-bearing) proved the deletion list incomplete without the two dynamic-import test
consumers, corrected the register census (19 rows, 16 non-consumer), re-dated 043's cut
commits, corrected three zero-caller claims to one-caller relics, and forced the
baseline sentence to name the branch-side `test_one_home` behaviour. All corrections are
in the approved digest.

**Council round one** (specs/044-ponytail-audit-residual-cuts/council.md: 8 gaps found
only by the cross-read, 13 findings deleted for carrying no command or refuted; `just
council` agrees at 59/66) proved four sentences wrong as written and they are corrected
in the approved digest: `sbom` and `scan` have gate-time callers so are not cut
candidates (G-1, U-2); `skillmap` is the sixteenth named row and also keeps its module
(G-2); `git revert` restores a commit family, not one file (R-1); the noqa residual
after family (a) is fifteen, not twenty (C-2); D-044-03's "byte-for-byte" claim now
describes the contract the suite actually asserts (G-6/E-3); and the undecidable-path
example now records kept modules in the changelog's existing `### Removed` section
rather than inventing an "Excluded list" convention (U-3/E-5). The chairman's first
step — re-run the two greps beside the register — was executed and is reflected in the
spec's census paragraph.

## The one gated step

As with specs 028-043, the canonical approval record for a cross-cutting decision is a
Structured MADR under `docs/adr/`; `madr.validate` on this tree returns
`INCOMPLETE [MADR_HOME_INVALID]` from the `specs/*/approval.md` dossiers, an inherited
red this record does not authorise rewriting. D-044-01 is promotion-marked in the spec;
the MADR promotion is the single re-runnable step after an approved block repairs the
inherited red.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty).
- It is not a standing autonomous grant: the plan's eight tasks are the exact
  authorised work, one atomic commit each, nothing past task 8 opened by this record.
- It does not cut `sbom`, `scan`, `skillmap`, `coverage` (gate-time callers), the
  Windows transaction backend (D-044-02), `imagery.findings`, `surface.receipt_binds_version`,
  `executor.Sandbox.connect`, or anything the council kept; does not add a verb,
  dependency or justfile recipe; does not tick a production-ready box; and does not
  modify `.ai/intent.md`, `CONSTITUTION.md`, `docs/adr/` or any spec file outside
  `specs/044-ponytail-audit-residual-cuts/`.
