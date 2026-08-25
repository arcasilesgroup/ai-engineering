---
name: ai-goal
description: >-
  Runs one request through the whole governed cycle in a single pass — research, spec,
  challenge, council, build, review, verify, security, audit, ship — and stops only to
  hand a person a tested thing to try. Your invocation is the standing approval; nobody
  else steps in until the end. The bar is the green gate plus an independent critic's
  verdict on the real artifact, looped until both hold. Trigger for "finish this without
  me, give me something to test", "run the whole gauntlet to a green gate". Not for one
  stage on its own — call that stage directly. Not for approving anything: you finish,
  then hand over.
license: Apache-2.0
compatibility: needs git
disable-model-invocation: true
---

# One run, no mid-run stop

`/ai-goal <goal>` is the person saying "this one runs without me". The whole cycle runs
in one pass and the person comes back only when there is a finished thing to test. The
invocation is the standing approval; you never ask again, and you never claim an approval
you did not earn.

## What it produces

The finished thing handed to the person: the change committed at `HEAD`, the
`ai-eng audit verify` gate output shown in full, and the acceptance checklist the person
runs against the real artifact.

## The order

Read `policy/skill-sequence.toml` and follow it; if that file is absent, refuse to
continue — the order is data, not prose. Load each stage's own skill and follow it:
`/ai-research`, `/ai-spec`, `/ai-challenge`, `/ai-council`, `/ai-build`, `/ai-review`,
`/ai-verify`, `/ai-security`, the audit verb, then `/ai-ship`.

## Tools are whatever the client has

The cycle uses only the tools present on this machine: the local floor (the repository,
the IDE and the assigned surface, the `ai-eng` harness, the model available) is always on,
and a web provider or NotebookLM is used only when the client configured it. An absent tool
degrades the stage that would use it — the research stage names `degraded-tool: <name>`
and carries on with the local floor. Nothing in this skill depends on a tool the client
does not have.

## Two bars, both green, neither negotiated

1. The governed gate: run `ai-eng audit verify` and show its output. Nothing silenced, no
   suppressed test, no loosened bound. Green means the gate a person runs is green.
2. The goal: measurable acceptance criteria written into the spec. A critic in its own
   context, with no memory of the builder's reasoning, compares the real artifact against
   those criteria and answers met or not — one or the other, never maybe.

Not green is not done. A red bar sends the work back through build and the critics.

## The loop is bounded

Every red is a chance to build again, not an infinite chase. Two attempts per task and
failing recipe before you change course. When the verdict is close, the critic judges
blind: it never sees your reasons, only what you built. A fixed cap on automatic work and
a short no-progress guard stop a loop that is not converging. When the cap or the guard
fires, write a page a person can act on: what failed, what was tried, what the honest fix
costs. Never a silent stop, and never "until perfect" — that is not a stop condition.

## Simplicity is the standing bar

KISS, YAGNI, DRY, SOLID, BDD, TDD, Clean Code, Clean Architecture. When two answers both
work, the smaller one wins. Keep the change the smallest thing that works and delete what
the change obsoletes. A simpler path exists and you did not take it — that is a defect.

## What this is not

- "The gate is green, so the critic's verdict is redundant" — the bars are two and neither is negotiated: an independent critic with no memory of your reasoning must compare the real artifact against the acceptance criteria.

## Done when — stop, and hand over

Both bars are green, the committed change and its gate output are shown, and the person
holds the acceptance checklist to test the handover like a client. You do not approve the
work and you do not claim a green you did not produce — you finish, then you hand over.