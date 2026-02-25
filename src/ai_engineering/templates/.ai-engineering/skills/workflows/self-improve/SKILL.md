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

1. **Analyze** current outcomes using active spec artifacts and diagnostics.
2. **Plan** focused next actions with dependencies and acceptance checks.
3. **Execute** smallest high-impact change set.
4. **Verify** gates/tests/integrity.
5. **Learn** capture outcomes and hand off: `navigator` (strategy) -> `governance-steward` (enforcement).

## Output Contract

- Improvement cycle report with actions, evidence, and next loop inputs.

## Governance Notes

- No loop iteration may skip mandatory governance checks.

## References

- `agents/navigator.md`
- `agents/governance-steward.md`
- `standards/framework/core.md`
