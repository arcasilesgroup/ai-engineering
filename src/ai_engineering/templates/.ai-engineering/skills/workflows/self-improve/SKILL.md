---
name: self-improve
description: "Run analyze→plan→execute→verify→learn loop for continuous governed improvement."
version: 1.0.0
category: workflows
tags: [improvement, iteration, governance, workflow]
metadata:
  ai-engineering:
    scope: read-write
    token_estimate: 700
---

# Self-Improve Workflow

## Purpose

Codify a deterministic continuous-improvement loop across strategy and governance execution.

## Trigger

- User requests iterative improvement.
- End of phase/spec retrospectives.

## Procedure

1. **Analyze (Planning Mode)** — gather ALL context. Search the codebase, read active specs, and review diagnostics before forming conclusions. Do NOT propose code changes yet.
2. **Plan (Planning Mode)** — formulate focused next actions with dependencies and acceptance checks based on gathered context. Output the plan and switch to Standard Mode.
3. **Execute (Standard Mode)** — apply the smallest high-impact change set. Always batch independent code modifications/tool calls in parallel to maximize efficiency.
4. **Verify (Standard Mode)** — ensure all tests, quality gates, and integrity checks pass before declaring completion.
5. **Learn** — capture outcomes and hand off: `navigator` (strategy) -> `governance-steward` (enforcement). Persist key learnings to the decision-store.

## Output Contract

- Improvement cycle report with actions, evidence, and next loop inputs.

## Governance Notes

- No loop iteration may skip mandatory governance checks.

### Iteration Limits

- Max 3 attempts to resolve the same issue within a loop iteration. After 3 failures, escalate to user with evidence of attempts.
- Each attempt must try a different approach — repeating the same action is not a valid retry.

## References

- `agents/navigator.md`
- `agents/governance-steward.md`
- `standards/framework/core.md`
