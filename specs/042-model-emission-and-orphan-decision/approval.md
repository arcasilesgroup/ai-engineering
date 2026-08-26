---
schema: "urn:ai-engineering:spec-approval:1"
schema_version: "1"
type: "approval"
id: "042"
title: "Specification 042 and its plan are approved at exact digests"
date: "2026-08-26"
spec: "042"
status: "accepted"
authority_role: "repository owner"
approval_ref: "conversation-2026-08-26-042"
---

# Specification 042 and its plan are approved at exact digests

## What is approved

`specs/042-model-emission-and-orphan-decision/spec.md` closes the three gaps the five
goal items named: **B-042-1** the router is consumed — every `ai-eng` command event
carries `tier_model` (the model string the pin's `[models]` tiers say the verb routes to,
both emit paths), and `ai-goal` + the cycle skills name the tier each stage requests;
**B-042-2** `_emit` records a `model` field from `AI_ENG_MODEL` like every other identity
field, with the four states (missing/undetermined/actual/intent) named, not merged, and
the chain hook passing through only a real payload `model` string; **B-042-3** every
orphan module gets exactly one checked status in `policy/module-status.toml` —
consumer (AST-verified import), orchestrator-future (reason cites the orchestrator spec),
or deferred-with-reason; **B-042-4** `loop_guard` keeps failing closed and escalates the
repeated verdict from the third identical denial in a window, naming the call by its
human-visible signature and the person channel verbatim. The spec corrects a misattribution
earlier specs carried: the inherited `madr` red is `MADR_HOME_INVALID` from the thirteen
`specs/*/approval.md` dossiers, not `MADR_SCHEMA_INVALID` from ADR 0025 — a conflation
this record measures (`madr.validate(Path('.'))` → `INCOMPLETE [MADR_HOME_INVALID]`) and
names correctly.

`specs/042-model-emission-and-orphan-decision/plan.md` sequences the work into twelve
atomic TDD tasks, red fixture first, mirroring the order the spec's dependencies demand:
the event field lands before the router consumption, the register after its red fixture,
the loop_guard escalation last.

The repository owner approved this record in conversation on 2026-08-26 (the `/ai-goal`
instruction naming the five concrete items) and directed this plan's execution. Approved
at these exact bytes (canonical — the plan's tick column is masked before signing):

| file | SHA-256 |
|---|---|
| `specs/042-model-emission-and-orphan-decision/spec.md` | `4ae25465240e7e55db7044b284fc7f959350876abd79d640673be53d44645b4e` |
| `specs/042-model-emission-and-orphan-decision/plan.md` | `77015bbd6a2cb222e53e66b537a4d3ec931d84710184ca4e985a458a687a8d2c` |

## The two critic rounds, and what they changed

Spec 042 was challenged and counselled twice. **Round one** (challenge.md: 4 WRONG,
18 OK; council.md: 5 cross-read gaps) executed the spec's claims against the tree and the
machine chain. Its corrections are in the approved digest: the inherited-red attribution
(MADR_HOME_INVALID, not MADR_SCHEMA_INVALID from ADR 0025); the two cli.py emit paths
(`--json` carries `outcome`, plain mode carries `ms`) written as two paths rather than
one field list; the digest's `by_reason` counter already collapsing identical reasons to
one row — the spec no longer claims it printed 8,745 rows; the 48% / 916 s figures
attributed as surface observations, not product measurements; the four-state model column;
the mechanical (import-graph) definition of a production caller; `tier_model` as a model
string, not a tier label; the escalation as the script rule 12 owes.

**Round two** (challenge.md: 7 WRONG, 8 UNPROVEN-as-future; council.md: 5 cross-read gaps)
attacked the revision. Its corrections are also in the approved digest: the escalation
example no longer claims an unreachable "made 7 times" (the window caps at 6) and names
the call by its `signature()` form (`Bash:pytest`), never the hex digest — and the second
denial in a window is the full verdict again (a 15-hit session's real shape: 13 denials,
four variant sentences today); the example event shows `model:"undetermined"` on the
Claude Code surface (which sends no model key) with `adapter:"undetermined"`, never the
invented `1.0`; the register example states that `model_router` is `consumer` only after
B-042-1's import lands; the chain hook's pass-through guards `isinstance(..., str)`
because `setdefault` with `None` would crash the fail-closed hook; the command-event
`model` field's process boundary is named (a surface must export `AI_ENG_MODEL` to the
`ai-eng` process — the hook pass-through does not reach a separate process); the
inherited-red count says thirteen dossiers today, this record making the fourteenth; and
the "no latency field" claim was corrected to "nothing aggregates `ms` into a
percentile" (8,010 command events carry `data.ms`).

`just council` agrees with 042's counts on the round-two digest: 5 gaps appeared only
after the cross-read, 3 findings were deleted or refuted.

## The one gated step

As with specs 028-041, the canonical approval record is a Structured MADR under
`docs/adr/`; creation is gated on `madr.validate` returning PASS, which on this tree
returns `INCOMPLETE [MADR_HOME_INVALID]` from the `specs/NNN-*/approval.md` dossiers
scoring as ambiguous MADR candidates outside `docs/adr/`. Spec 042 does not authorise
rewriting that history. This record is the dossier-level approval at exact digests; the
MADR promotion is the single re-runnable step after an approved block repairs the
inherited red.

## What this approval does not do

- It is not an acceptance of any risk (the spec's `## Accepted risks` stays empty until a
  named owner accepts).
- It is not a standing autonomous grant: the plan's twelve tasks are the exact authorised
  work, one atomic commit each, nothing past task 12 opened by this record.
- It does not wire `loopgate.done()` into an orchestrator (it stays `orchestrator-future`
  in the register, per specs 031/041 and B-042-3), does not change the tier mapping
  (spec 037's `_LOW_STEPS`/`_TOP_STEPS` are the contract), does not add a verb, does not
  compute a tool-failure rate or latency percentile (the 48% / 916 s figures are surface
  observations; the product-measured facts are blocked counts and rule-12 rows), and does
  not modify `.ai/intent.md`, `CONSTITUTION.md` or the one-writer rule.