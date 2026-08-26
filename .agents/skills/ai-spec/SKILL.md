---
name: ai-spec
description: >-
  Writes the governed record of a decision before code exists: evidence, the problem,
  at least two real options, one recommendation and self-challenge, assumptions, unresolved
  risks, observable examples and the authority for proceeding. Trigger for "let's add",
  "how should we handle", "what's the best approach", "I'm thinking about", "what should
  we build for", "write the spec". Not for turning an approved spec into tasks — use
  /ai-plan. Not for writing code — use /ai-plan after approval. Not for judging a diff —
  use /ai-review.
license: Apache-2.0
compatibility: needs git; needs the ai-eng CLI on PATH
disable-model-invocation: true
---

# Write the spec

## The tier to ask for

Spec writing is mechanical once the research has done the hard thinking; ask the **low**
tier, the model the repository's `[models]` section configures for it — never a model
name coded here, and never a provider the repository did not choose. `model_router` maps
research and spec to the low tier; if the pin leaves it unconfigured, fall back to
`default_tier`. Say which tier you ran on so the command event's `tier_model` can be
read against reality.

## Procedure

0. Validate the intake (spec 037 / B-037-3): run the opening request through
   `intake.validate_intake`; when it returns `INCOMPLETE` naming missing fields (goal,
   constraints, acceptance), ask those intake questions first — capped, the way the
   research's grill recommends — before any discovery. `specs/new-goal-template.md` is the
   copy-paste fallback; a well-formed free request passes without it. The input is the
   contract: a malformed goal produces a malformed spec.

1. Read `CONSTITUTION.md`, the related records and repository evidence and current primary
   sources relevant to the decision before asking anyone. State what was read, what is true
   now and what remains unknown. Never infer a control from its documentation alone.
   If `CONSTITUTION.md` is absent or incomplete, the spec records what is missing rather
   than assuming it exists — a repo without it is a repo without the framework's identity.
2. State the problem in words a non-technical reader can follow. Separate fixed
   constraints, current facts, intended outcomes and the harm of leaving it unchanged.
3. Present at least two real options. For each, say what it gives, costs, risks and rules
   out; do not invent a weak option merely to lose.
4. Recommend one, explain why the others lose, then challenge the recommendation once with
   the strongest realistic failure case. Revise it or keep it and say why.
5. Record assumptions and unresolved risks separately. Do not turn either into fact or an
   accepted risk, and do not invent an owner, approval or green result.
6. Give observable BDD examples for the important success, denial and undecidable paths,
   using Given/When/Then and outcomes somebody can check.
7. Ask only questions whose answers change the decision, after presenting the evidence and
   provisional recommendation. A human answer overrides inference; update the options,
   recommendation and risks it changes rather than appending a contradictory answer.
8. Create the draft with `ai-eng spec new <slug>`; add `--ref owner/repo#45` only when that
   is the real work item. If this supersedes shipped work, create a new spec, link the old
   record and explain the change; never rewrite history.
9. Architecture advice belongs inside the options, never beside them. Where a boundary, a
   dependency, a duplicated source of truth or the cost of reversing it decides between two
   options, say so in the option that carries it. A separate architectural opinion nobody
   has to answer is the advisor this project chose not to build.
10. Keep decisions in their spec unless they constrain future specs. For the ones that do
   — architectural and cross-cutting: a boundary (API, auth, storage) or a global
   convention later specs must know and respect — list them under `## Decisions` marked
   `- [X]` and promote with `ai-eng decide "<title>"`; the
   verb promotes only marked titles, and proposal is not approval. Everything else stays
   inside the spec, which is its record. Leave every production-ready box unticked until
   the named command supplies fresh evidence.

## Authority boundary

Without a person, choose only a reversible, least-scope option within existing permissions
and record the permission and reversibility. Never expand a write, execution, network or
publication boundary because the preferred option needs it.

For an irreversible, high-risk, contradictory or cross-cutting decision without an
accountable human decision or exact preapproved policy, return `INCOMPLETE`. Record what
authority is missing with `ai-eng report blocked`, so the page in `docs/` shows it and the
person who is not at the keyboard can see it — say what is missing, never that it arrived.
Then stop before plan, code, publication or risk acceptance.

A fresh reviewer may find defects or recommend escalation, but never grants authority,
accepts risk or approves its own work. More reviewers do not change this boundary.

If `CONSTITUTION.md` is absent or incomplete, discovery may prepare it, but writing the
project identity is cross-cutting and requires the same authority. Never overwrite one.

## Done when

- The spec says what is wrong, what evidence supports it, what could be done and why the
  recommendation survived its challenge.
- Assumptions, unresolved risks and observable BDD examples are explicit.
- The authority basis is named, or the result is `INCOMPLETE` with the missing decision.

## What this is not

Not a discussion transcript, implementation or risk acceptance. Delete empty ceremony;
keep the evidence and decisions a future reader must be able to audit.

- "Only one option is worth considering, so two options would be theatre" — the procedure demands at least two real options and forbids inventing a weak one to lose, because the comparison is what makes the recommendation auditable.
