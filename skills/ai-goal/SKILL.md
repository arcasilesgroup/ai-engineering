---
name: ai-goal
description: >-
  Use when the user wants to build in an autonomous loop — "loop this feature", "run these
  overnight", "write the goal for this" — pinning the loop contract: what it consumes, which
  gates it closes, when it stops, and what it reports, without ever reimplementing the loop
  itself (the surface's native goal mode runs it). Not for one-shot verification — use
  /ai-verify. Not for writing the plan the loop executes — use /ai-plan.
license: MIT
---

# ai-goal — the loop contract (Loop Engineering)

The loop is NOT reimplemented: the surface's native goal mode runs it. This skill pins the
loop contract from three source skills that cover the full method: feature setup with two
human stops (mock and approval), the goal condition for one feature, and an overnight
multi-feature queue.

- Feature setup: folder, approved mock, re-entrant spec → [new-feature/SKILL.md](new-feature/SKILL.md)
- The goal condition for one feature: pointer, reporting clause, met condition → [goal-writer/SKILL.md](goal-writer/SKILL.md)
- Multi-feature queue with a builder subagent + adversary verifier → [feature-batch/SKILL.md](feature-batch/SKILL.md)

## Step 0 — find the contract, never be told it

A fresh session is launched as `/ai-goal` and nothing else. The slot is the briefing, so
discovery comes first, in this order, before any step is taken:

1. `ai-eng doctor` — the `spec slot` line is the gate. `contract approved (sha256 in lock)`
   means there is a loop to run. `live spec.html WITHOUT approval` means STOP 1 is pending:
   the loop does not start, and it says so. No spec at all means nothing to execute.
2. `.ai-engineering/spec.html` — the WHAT, immutable once approved (self-protect denies the
   edit, and re-opening it costs a human). Read its `00 Context chain` block first: it links
   the research and the handshake doc this milestone consumes, so those are read before the
   first step, never after the first failure.
3. `.ai-engineering/plan.html` — the HOW. The loop consumes it, takes the first step that is
   not green, and marks it in place as gates close. This file is the agent's workbench and is
   exempt from self-protect; spec.html is not.
4. `.ai-engineering/brainstorm.html` — the handshake doc behind the gates: the decisions already
   taken, the ones still open, and what is out of scope. A step that depends on an open unknown
   stops and asks; it never invents the answer to keep moving. This slot lives beside spec.html
   and plan.html and dies with them at `spec close`, so the loop reads it while it is live and
   never writes a second map next to it.
5. `[budget]` in `.ai-engineering/config.toml` — the ceiling and the stop list. An absent
   section means no pinned ceiling: say it once, then the human is the clock.

None of this belongs in the prompt. What the loop needs lives in the slot, which is why
`/ai-goal` by itself is the whole invocation.

## Lifecycle

Lane: standard, full
Writes: .ai-engineering/plan.html
Read by: the human, the next iteration of the loop
Dies: with the milestone, when plan.html dies
Next: ai-proof after each step, then the closing chain — ai-verify, the fired triggers and ai-visual-recap — once plan.html is fully green (see The closing chain)

Source: Loop-Engineering, Loop Salon demo repo (attributed — no author or URL declared
upstream; open license issue H4).

## The ai-engineering seam

1. The loop is NOT reimplemented: a surface with a native goal mode runs it (contract mode),
   and a surface without one runs under facilitator mode below — ai-goal fixes the contract
   either way.
2. It consumes `.ai-engineering/plan.html` and closes `.ai-engineering/spec.html` gates with
   receipts (`ai-eng spec run`). Each iteration marks that artifact in place: the markup and
   the style come from [ai-design › references/artifact-design.md](../ai-design/references/artifact-design.md), and the loop adds none of its own.
3. The three stops of blueprint §5.1 become exit conditions: approved contract / loop guard
   deny / destructive action above budget.
4. The token/turn budget comes from `.ai-engineering/config.toml` (`[budget]`), not from the
   conversation.
5. The closing report is produced by ai-visual-recap (`.ai-engineering/recap.html`) — step 5
   of the closing chain below, which the loop runs to the end rather than stopping at the
   last green gate.
6. The "enough" criterion is KISS/YAGNI: the smallest thing that closes the gate.

## The closing chain

Green gates are not the end of the loop. The loop ends here, in this order, and it yields
nowhere inside this chain except at one of the three stops:

1. **`ai-eng spec run`** — every gate, rechecked. A red gate is the next step, never a
   report.
2. **Read the greens.** A CHECK that cannot fail for the reason its own text states is a
   finding about the contract, not evidence: an `ls` of an artifact any earlier run already
   satisfies, a proof script whose case is never exercised, a `-t` filter that matches no
   test. Name it to the human with the gate id and what would settle it. `spec.html` is
   approved, so that CHECK is theirs to reopen — never the loop's to quietly count as met.
3. **ai-verify** — the requirement-level pass, run by an agent that did not build it: one
   verdict per requirement (MET / PARTIAL / DIVERGED / MISSING / UNASKED / UNVERIFIABLE),
   each with file:line and the command that proves it. `DIVERGED` is a decision for the
   human, not a fix.
4. **The fired triggers' own artifacts**, per the spec's trigger list — `security` →
   ai-security (`findings.json` + `REPORT.md`), `public-interface` → ai-write,
   `arch-change` → the arch rules and their test. A fired trigger left without its artifact
   keeps the milestone open, whatever the gates say.
5. **ai-visual-recap** → `.ai-engineering/recap.html`. The loop does not write this file by
   hand: the recap is that skill's artifact, and its markup comes from the artifact design,
   never from the loop's taste.
6. **Hand over the close.** `ai-eng spec close` is the human's: it is the act that unfreezes
   the contract, and un-freezing a contract nobody signed off is not the loop's call.

In facilitator mode the chain is the same, run once at the end of the plan. Between steps it
is still one step, its receipt, then stop.

## Facilitator mode

The surface's declared capability decides which mode applies. A surface that declares a
native goal loop runs **contract mode**: this skill pins the contract and the loop executes
it. A surface that declares none is not handed off to a loop — this skill runs **facilitator
mode** itself and walks `.ai-engineering/plan.html` one step at a time inside the session.

Facilitator mode changes who advances the loop, not what the loop guarantees. The same three
stops apply (approved contract / loop guard deny / destructive action above the `[budget]`),
every closed gate gets the same receipt (`ai-eng spec run`), and the human is the clock: one
step, its receipt, then stop and wait. No timer, no unattended queue, no implicit approval.

An `unverified` surface runs facilitator mode until a receipt says otherwise. Native goal
capability is a claim like any other, and the first honest receipt is what upgrades it;
until that receipt exists, the slow path is the true one.

## Routing

In scope: autonomous construction loops, overnight batches, goal contracts with gates and
stop conditions. Not for: diagnosing a failure (/ai-debug), verifying a finished diff
(/ai-verify), deciding what to build (/ai-brainstorm then /ai-plan).
