---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0021"
title: "The owner approves specifications and nothing else"
date: "2026-08-21"
spec: "023"
status: "accepted"
authority_role: "repository owner"
approval_ref: "spec-023-2026-08-21"
approved_at: "2026-08-21T12:00:00Z"
supersedes: ""
---

# 0021. The owner approves specifications and nothing else

## Context and problem statement

`docs/adr/0016` granted a scoped standing authority for one run: commit on a dedicated
branch, open a pull request, approve the specifications written for that work. Everything
else stayed with the owner, and the list of everything else was long enough that the run
ended with seven decisions queued in a brief and none of them taken.

That queue is the defect this record answers. Seven items sat waiting while the work they
governed sat still, and six of the seven were engineering judgements with a measurement
behind them — the kind of thing an agent is supposed to settle and write down, not escalate.

On 2026-08-21, after merging pull request #681, the owner said:

> de aquí, todos deberías de poder decidir tú. La persona/equipo solo interviene en la
> aprobación del spec. Pero a partir de ahí, debería de ser la llm que pueda implementar
> con el goal.

A permission that is not written is not a permission, which is why this exists before
anything runs under it.

## Considered options

1. **Read it as unlimited.** It is the shortest reading and the wrong one. The sentence
   names one intervention the person keeps; it does not say the acts a person must perform
   because they are a person — merging, releasing, accepting a dated risk — have moved.
   Nothing in it mentions them, and an agent that reads silence as permission is the failure
   this repository is built to refuse.
2. **Read it as decision-making authority, bounded by the acts that were never on the
   table.** The person approves a specification and its plan at exact digests. Every
   judgement after that approval is the agent's, written down where it can be overturned by
   reverting one commit.

## Decision outcome

Option 2.

**Granted.** Deciding, and building what was decided: commits on a dedicated branch in a
worktree of its own, a pull request, records that refute or reopen an earlier decision when
a measurement says so, and the choice of how a task in an approved plan is carried out.

**Still refused, and not this agent's to widen.** Pushing to the default branch. Merging.
Cutting a release or a tag. Accepting a dated risk. Lowering any floor — mutation, coverage,
severity. Passing `--no-verify` in any spelling. Shipping a suppression comment. Approving a
specification, including this run's own.

That last one is the load-bearing exclusion. Two approvals recorded in `docs/adr/0013` no
longer cover the bytes they signed, and the repair for that is a fresh signature. An agent
that could sign one would have made the whole approval chain decorative. So the two files
are named with their digests inside `specs/023`, and approving `023` is what reaches them.

The owner approved these bytes on 2026-08-21:

| file | SHA-256 |
|---|---|
| `specs/023-seven-decisions-the-owner-handed-back/spec.md` | `f30853415720dc2bb849dfdcec5766c71b6094e6be968f6ca6b4942ad477c7b0` |
| `specs/023-seven-decisions-the-owner-handed-back/plan.md` | `2420f008b55905cd161d8436cc787c7e8fc4eab1e597745a6c567358e82ede57` |

The answer was given in the exact form the pull request published, against digests the owner
could read before answering: `apruebo 023 en f30853415720 y 2420f008b559`.

## Consequences

The cost of a decision drops and the cost of a wrong decision does not. Six judgements that
would have waited are taken in this run, each with the measurement that produced it and each
in its own commit, so overturning one is `git revert` and does not disturb the others.

What gets worse is the density of the review. One reading now covers a specification, a plan
and eight decisions rather than one question, and a reader who skims it authorises more than
a reader who skims a brief. The mitigation is structural rather than procedural: every
decision in `023` states the command that would overturn it, so disagreeing does not require
re-deriving the measurement.

This does not supersede `docs/adr/0016`. That record's refusals stand word for word; this one
widens what may be decided and leaves what may be *done* exactly where it was.
