---
id: "028"
slug: writer-model-recorded
status: draft
date: 2026-08-25
ref: ""
supersedes: ""
---

# The writer model of ai-goal, recorded as a governed decision

## Who this is for, and what it is worth to them

The person who runs `/ai-goal` on this repository and the person who approves what it
produces. Today the model of who may write is spread across three files — the intent's
fixed constraints, the skill-sequence policy, and the ai-build skill — and it has never
been recorded as a single reviewable decision. The change for them: one ruled record (a
proposed Structured ADR, which grants no authority) states the model, and the one skill
that routes by it (`ai-goal` corpus) gains a labelled refusal for the case that currently
has no route. Nothing else changes and nothing is authorized.

## Context and problem

**What is true today, measured in this tree on 2026-08-25:**

- The Solution Intent (`.ai/intent.md`, approved digest `ae523990`) fixes: "Until a
  separately approved P3 plan proves safe coordination, one writer owns repository
  changes."
- `policy/skill-sequence.toml` records the governed order; its `[parallel] policy` is
  "fork contexts only; task-level parallelism inside ai-build per the approved plan", and
  its `[gate] approval` requires "a human approval record carrying the specification's
  exact digest".
- `.agents/skills/ai-build/SKILL.md` step 1: "Take the task, not the plan... It refuses when that digest
  no longer matches the file on disk... If the task is not in a plan, or the plan is not
  approved, stop here: nothing to execute."
- `specs/013-origin-first-coordination/spec.md` (draft) records the future P3 target:
  "One task, one work item... One remote branch, one worktree, one writer. Reviewers may
  be many; writers may not."
- The `merge_group` trigger already exists in `.github/workflows/check.yml`.
- The coordination shape is guarded: `tests/test_coordination_shape.py` refuses bare
  force, background rebase, per-commit publish, an ownership store, a heartbeat and a TTL
  takeover.

**The problem, in words a non-technical reader can follow:**

When two people asked whether the four-term formula "one task = one branch = one
worktree = one writer" is the model of this repository, the answer lived in three places
and nowhere. It is: that formula is the future P3 target recorded in spec 013, not the
model today. Today the model is a single writer — the invoked agent — who implements
only a spec/plan approved at its exact digest, stops when the plan is not approved, and
stops before publishing or approving. Because that model is only written in fragments,
the next reader will answer the same question the same way again and nothing will have
changed.

**The harm of leaving it:** the same judgement keeps being resolved by a person instead
of by a record. The third time it resolves the same way it should be a script
(`AGENTS.md` rule 12). Spec 013 remains a draft and the one-writer rule remains the
constraint; that is the decision, and it deserves one home.

## Options considered

1. **Record the model as a proposed Structured MADR under `docs/adr/` and add a labelled
   refusal to the `ai-goal` corpus for the case that currently has no route.**
   Gives: one reviewable home for the decision; the routing gap fixed; the refusal count
   in `tests/skill_eval.py` rises by one, with `policy/pilot-register.toml` baseline
   moved and argued. Costs: one new ADR, one corpus row, a baseline movement. Risks: the
   ADR must be schema-conformant (it will be, and is a permitted `proposed` state); the
   corpus row must not collide with another skill's claim or refusal (it will not, and
   `skill_eval` would catch it). Rules out: changing the intent, 013, or the one-writer
   rule. **Blocked today:** `ai-eng decide` refuses to promote while `madr.validate` is
   INCOMPLETE on this tree, which it is — `MADR_SCHEMA_INVALID` from ADR 0025 of spec 026
   (documented in `.ai/reports/014`). The ADR creation is therefore gated on an approved
   repair of that inherited record, which this decision does not authorize.

2. **Do nothing; keep the model implicit.**
   Gives: nothing to review. Costs: the same question keeps being asked and resolved by
   hand; the routing gap stays open; the third identical verdict stays a prompt instead
   of a record. Risks: the model drifts silently across the three files. Rules out:
   fixing the gap.

## Decision

**Option 1.** The reason is not elegance — it is that option 1 gives the decision a home
a reader and a gate can find, and it does not change the constraint. The decision is
recorded, not implemented: `ai-eng decide "<title>" --spec 028` writes the proposed ADR
(the positional title is the verb's promotion path; accepting it is a named person's
act), and the corpus refusal makes the routing machine-readable. If it constrains a spec
that does not exist yet, this is that record.

## Challenged once

The strongest case against recording: this is "documenting for its own sake" — the model
is already written in the intent, the sequence policy and the ai-build skill, so a fourth
place is a duplicate home for the same truth.

Answer: the three existing places are fragments, one of them (`specs/013`) is a *draft
target* and not the current model, and none of them is a decision record that a person
approves. The ADR is the one place where the current model is stated as a decision and
can be accepted or rejected as such. And the corpus refusal is not prose: it changes a
count a gate measures (`skill_eval`), so it is a real, checked change. The conflict
against a claim (`ai-goal` also "runs the whole cycle") is resolved by the refusal's
quoted case being specifically about *recording the model*, which no other skill claims.
The promotion is today gated by the inherited MADR red; that gate is recorded, not
hidden, by this spec.

## Assumptions and unresolved risks

- Assumption: the reader of `.ai/reports/015` and this script already accept that
  "one writer today, parallel P3 as the gated future" is the true model. It is measured
  in this spec.
- Unresolved: the four-term formula in spec 013 stays a draft until a P3 plan is
  approved. This record does not change that.
- Unresolved: the gate (`just check`) is currently red in four `tests/test_madr.py`
  failures caused by ADR 0025 of spec 026, whose state lives in git history — a known,
  dated acceptance documented in `.ai/reports/014`. This change does not authorise
  rewriting that history; the red is inherited, not introduced by this change. The
  project's standing bar for `/ai-goal` is the green gate; with an inherited red, no
  completion of this goal can honestly claim a green gate. That is recorded here as the
  honest ceiling of this goal. **Consequence for this goal:** `ai-eng decide` refuses to
  create the proposed ADR while `madr.validate` returns INCOMPLETE, so the ADR promotion
  is the one step of this goal that is blocked until an approved block repairs ADR 0025
  (its forbidden frontmatter fields and its history). The blocker, its exact cost and
  the page a person can act on are recorded in this block; every other step of this
  goal is reachable.

## Examples somebody can check

The post-change examples below hold after two conditions: (a) this change is committed,
and (b) an approved repair has made `madr.validate` PASS again. Condition (b) is the
inherited red of spec 026, documented in `.ai/reports/014`.

Given the model is recorded as a proposed ADR and committed,
When a reader runs `ai-eng decide --list`,
Then the output contains `0028` with status `proposed`.

Given `docs/adr/0028-*.md` exists with `status: "proposed"`,
When the MADR graph validates the repository,
Then ADR 0028 validates and is not the cause of a new MADR failure.

Given the corpus refusal is added and committed,
When `uv run python tests/skill_eval.py` runs,
Then it exits 0 and prints `RAN skilleval=350`.

Given the refusal and the register move are committed, and the inherited `madr.validate`
INCOMPLETE is still un-repaired,
When a reader runs `ai-eng decide --list`,
Then the listing still ends at `0026` and no `0028` exists — the honest reachable state,
which the blocked page names.

Given the intent, `.ai/intent.md`, `specs/013-origin-first-coordination`, the
skill-sequence policy, the ai-build skill, or the one-writer rule,
When this change is implemented,
Then none of them is modified.

Given the current tree, where `madr.validate` is `MADR_SCHEMA_INVALID` from ADR 0025 of
spec 026,
When `ai-eng decide "The writer model of ai-goal is one writer implementing an approved
plan; the four-term formula is the gated future P3 target, not today" --spec 028` runs,
Then the verb refuses with `INCOMPLETE [MADR_SCHEMA_INVALID]` and writes nothing.

## Decisions

The post-change examples below hold **after** two conditions: (a) this change is
committed, and (b) an approved repair has made `madr.validate` PASS again. Condition (b)
is the inherited red of spec 026, documented in `.ai/reports/014`; until it holds, the
first two examples are BLOCKED and the blocked page says exactly what unblocks them.

**Given** the model is recorded as a proposed ADR and committed,
**When** a reader runs `ai-eng decide --list`,
**Then** the output contains `0028` with status `proposed`.

**Given** `docs/adr/0028-*.md` exists with `status: "proposed"`,
**When** the MADR graph validates the repository,
**Then** ADR 0028 validates and is not the cause of a new MADR failure.

**Given** the corpus refusal is added — the literal row `- "record the writer model as a
decision" — use \`/ai-spec\`; a decision is born and reviewed inside its spec, and an ADR
is promoted only when a person accepts it at an exact digest` — and committed,
**When** `uv run python tests/skill_eval.py` runs,
**Then** it exits 0, prints `RAN skilleval=350`, and the baseline in
`policy/pilot-register.toml` was moved to `350` in the same commit with the reason given.

**Intermediate — Given** the refusal and the register move are committed, and the
inherited `madr.validate` INCOMPLETE is still un-repaired,
**When** a reader runs `ai-eng decide --list`,
**Then** the listing still ends at `0026` and no `0028` exists — the honest reachable
state of this tree, which the blocked page names.

**Denial — Given** the intent, `.ai/intent.md`, `specs/013-origin-first-coordination`, the
skill-sequence policy, the ai-build skill, or the one-writer rule,
**When** this change is implemented,
**Then** none of them is modified.

**Blocked — Given** the current tree, where `madr.validate` is `MADR_SCHEMA_INVALID` from
ADR 0025 of spec 026 (`.ai/reports/014`),
**When** `ai-eng decide "<title>" --spec 028` is run,
**Then** the verb refuses with `INCOMPLETE [MADR_SCHEMA_INVALID]` and writes nothing; the
blocked page names the approved repair that unblocks it.

## Decisions

**D-028-01 — the current model is one writer implementing an approved plan; the
four-term formula is the gated future P3 target, not today.**
**Rationale:** the intent, the sequence policy and the ai-build skill all record exactly
this; 013 records the future.

**D-028-02 — the model is recorded as a proposed Structured MADR with a pinned title**
(`ai-eng decide "The writer model of ai-goal is one writer implementing an approved plan;
the four-term formula is the gated future P3 target, not today" --spec 028`), which
grants no authority. The accept act is the repository owner role in `.ai/intent.md`.
**Rationale:** a decision record is a reviewable home; `proposed` is the schema's
non-authorizing state; accepting it is the named person's act, and the named role is the
one the intent already records. The promotion is blocked today by the inherited
`madr.validate` INCOMPLETE from ADR 0025 of spec 026; that is recorded, not hidden.

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command. This
specification records a decision (the writer model of `/ai-goal`) and constrains one
skill text; it adds no service, no URL and no second hop, so the service-shaped boxes
are `not applicable`.

- [x] CI/CD — `just check`, run by `.github/workflows/check.yml` on every push; nothing here is deployed and `.github/workflows/release.yml` is what publishes the wheel
- [x] Logs — not applicable, and that is the rule: this spec adds a record and a corpus refusal; every verb still emits the one JSON line `ai-eng digest` reads
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — not applicable: the change is a proposed ADR and one corpus line; there is no new runtime path for an uncaught exception to leave through
- [x] Health and data age — `python tests/skill_eval.py` asserts the `skill-routing` baseline moved 349 → 350 and the corpus refusal routes the decision to `/ai-spec`; the record only stops being current when a person accepts the proposed `docs/adr/0028`
- [x] External check — `.github/workflows/check.yml` runs the whole gate on every push to this repository, and what it cannot check — the ADR 0028 promotion, blocked by the inherited ADR 0025 red — is written down in `specs/028-writer-model-recorded/blocked.md`
- [x] Second path — the same decision is recorded twice by routes that share no line: the `ai-goal` corpus refusal (read by `tests/skill_eval.py`) and the proposed `docs/adr/0028` (read by `tests/test_madr.py`), so the decision cannot drift between them
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push, over a change that adds no dependency and no network call