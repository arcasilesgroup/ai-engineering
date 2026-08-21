---
name: ai-cycle
description: >-
  Walks one request through the governed cycle by loading each stage's own skill body and
  following it — research, spec, challenge, council, then a brief a person reads. After
  that person says go, `ai-cycle build <NNN>` runs the second half: build, review, verify,
  security, audit, ship. Trigger for "run the whole cycle on this", "/ai-cycle build 021".
  Not for one stage on its own — call that stage directly. Not for approving anything: it
  stops at the brief and has no field in which an approval could be written.
license: Apache-2.0
compatibility: needs git
disable-model-invocation: true
---

# Two halves, and a person between them

Not an engine. Each stage below is a skill with its own file; load that file and follow it,
the way the generated slash command already says. There is no state file, no new verb and
nothing here that decides anything a stage would not decide on its own.

## First half — up to the person

`/ai-cycle <what you want>`

1. `ai-research` — find out, and write `.ai/reports/NNN-name.html`.
2. `ai-spec` — one specification, with its own "Challenged once" section.
3. `ai-challenge` — a different reader executes the specification's sentences.
4. `ai-council` — lenses that never see each other say what is absent.
5. A brief, published as a page: what is proposed, what was refuted, what is missing, and
   what it costs. Then **stop**.

Stopping is the whole of this half. `ai-eng report blocked` already lists a drafted
specification nobody has approved, so the halt exists and fires; this hands the person the
thing they need to decide instead of a status line. The approval is a record with the
specification's exact digest in it, and until that record exists the second half has
nothing to run against — the task envelope refuses outright when the bytes moved.

## Second half — after them

`/ai-cycle build <NNN>`

6. `ai-build` — one task at a time, through `ai-eng spec show <NNN> --task <n>`. Two
   kilobytes, not the whole plan. Where the plan's order allows two tasks at once and the
   host can start two agents, start two; where it cannot, do them in turn.
7. `ai-review`, `ai-verify`, `ai-security` — the critics, each in its own context.
8. `ai-eng audit verify`, then `ai-ship`.

## When the gate goes red

It does not stop at the first red and it does not get to cheat.

- `just` stops at the first failing recipe, so a red gate has exactly one guilty recipe.
  An attempt is counted per **task and failing recipe**, never per message and never per
  gate run: counting messages would give one mistake that broke six tests twelve attempts,
  and counting runs lets somebody else's failure eat this task's budget.
- Before spending an attempt, run the same command again, unchanged, the way the gate runs
  it — in parallel, because a test that only fails in parallel fails where it matters.
  Green on the repeat spends nothing and is written down as non-determinism. Two of those
  notes on the same test in one build is not repair any more: escalate.
- **Two attempts.** Only a whole green gate resets the count. A recipe that went green and
  goes red again keeps its count — measured: one review went red three times in a row
  before passing, and resetting would have spent six attempts and never escalated.
- Never repair by silencing: no `--no-verify`, no suppression comment, no skip mark, no
  loosened bound, no raised ceiling. If the honest fix is a raised ceiling, that is the
  escalation, with the arithmetic.
- If the count cannot be read, treat the attempts as spent and escalate.
- Escalating means a page a person can act on: what failed, what was tried, what it would
  cost to fix properly. Never a terminal paragraph and never a silent stop.

## Done when

Half one ends with a brief and no approval written by anybody here. Half two ends with a
green gate whose output is shown, or with a page saying exactly why it is not green.
