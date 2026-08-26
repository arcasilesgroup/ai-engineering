---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "037"
title: "Specification 037 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "037"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-037"
---

# Specification 037 and its plan are approved at exact digests

## What is approved

`specs/037-model-router-and-intake-validation/spec.md` adds three behaviours: **B-037-1**
per-repository model tiers in `.ai/config.toml` (`[models]` top/medium/low/default_tier,
any provider name, schema in `policy/models.schema.json`), **B-037-2** a pure-function step
router (`src/ai_engineering/model_router.py`: `route(step, config)` mapping mechanical
steps to `low`, hard reasoning to `top`, the rest to `medium`, falling back to
`default_tier`; `bail_out(request)`), and **B-037-3** a validated intake
(`src/ai_engineering/intake.py` `validate_intake` + `specs/new-goal-template.md`, and
ai-spec step 0 asking the intake questions when the opening request is malformed). The spec
also records the sixteen reviewed roadmap points as a committed table (D-037-04) so the
approved roadmap survives the session: covered rows, P0 (this spec), P1/P2 candidate specs,
rejected rows with reasons. `specs/037-model-router-and-intake-validation/plan.md`
sequences the P0 work into five atomic TDD tasks, red fixtures first, and explicitly does
not authorise the P1/P2 rows.

The repository owner approved this record in conversation on 2026-08-26 (the /ai-goal
instruction, the roadmap approval, and the request that nothing approved be forgotten) and
directed this plan's execution. Approved at these exact bytes (canonical — the plan's tick
column is masked before signing):

| file | SHA-256 |
|---|---|
| `specs/037-model-router-and-intake-validation/spec.md` | `875f3fd5ff037257f159b5b029946a4736846037ee1dee10284522b1bca658f2` |
| `specs/037-model-router-and-intake-validation/plan.md` | `5bbb009a22987fb3e73fd5be27d63b5764148c070efcc04605274eba00127906` |

Spec 037 was challenged and counselled before this record: `challenge.md` (24 findings:
6 WRONG — citations to wayfinder W-01 and spec 036's lock-in rejection corrected, the
`[models]` section timing, `just test` vs `just cover`, `ai-eng report digest`, the config
schema reader — 8 UNPROVEN, 10 OK) and `council.md` (4 gaps found only by the cross-read,
6 deleted; `just council` agrees: `037 … 4 found only by the cross-read, 6 deleted`). The
spec at this digest incorporates every WRONG correction and the roadmap table (D-037-04).

## The one gated step

As with specs 028-036, the canonical approval record is a Structured MADR under
`docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree returns
`INCOMPLETE [MADR_SCHEMA_INVALID]` from ADR 0025 of spec 026. Spec 037 does not authorise
rewriting that history. This record is the dossier-level approval at exact digests; the
MADR promotion is the single re-runnable step after an approved block repairs ADR 0025.

Task 5 runs the gate on the block. Nothing in this record claims a green that has not
happened: the 037 fixtures do not exist until the approved plan writes them.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's five tasks are the exact authorised
  work, one atomic commit each, nothing past task 5 opened by this record.
- It does not implement the P1/P2 roadmap rows (gate-check-runner CLI, intake depth,
  code-simplifier skill, large-codebases template, two-job CI gate, skillify CLI, a11y
  guard): those are candidate specs, recorded in the roadmap table, not scope.
- It does not modify `.ai/intent.md`, `CONSTITUTION.md` or the one-writer rule; the pin's
  `[models]` section is the one config change, made by this spec's own commit
  (`30f8ec1e` for the section, `86c9f39e` for `default_tier`).