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

Source: Loop-Engineering, Loop Salon demo repo (attributed — no author or URL declared
upstream; open license issue H4).

## The ai-engineering seam

1. The loop is NOT reimplemented: the surface's native goal mode runs it. ai-goal fixes the
   contract.
2. It consumes `.ai-engineering/plan.html` and closes `.ai-engineering/spec.html` gates with
   receipts (`ai-eng spec run`).
3. The three stops of blueprint §5.1 become exit conditions: approved contract / loop guard
   deny / destructive action above budget.
4. The token/turn budget comes from `.ai-engineering/config.toml` (`[budget]`), not from the
   conversation.
5. The closing report is produced by ai-visual-recap (`.ai-engineering/recap.html`).
6. The "enough" criterion is KISS/YAGNI: the smallest thing that closes the gate.

## Routing

In scope: autonomous construction loops, overnight batches, goal contracts with gates and
stop conditions. Not for: diagnosing a failure (/ai-debug), verifying a finished diff
(/ai-verify), deciding what to build (/ai-brainstorm then /ai-plan).
