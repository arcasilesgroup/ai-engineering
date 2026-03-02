---
name: standards
description: "Propose and apply standards updates from measurable evidence (gate failures, audits, incidents). Use when recurring workflow friction, new risks, or platform changes require policy updates."
metadata:
  version: 1.0.0
  tags: [governance, standards, adaptation, policy]
  ai-engineering:
    scope: read-write
    token_estimate: 760
---

# Adaptive Standards

## Purpose

Define a controlled loop for proposing standards updates from measurable evidence.

## Trigger

- Recurring failures/friction in governed workflows.
- New risks or platform changes requiring policy updates.

## Procedure

1. Collect evidence from gates, audits, and incident patterns.
2. Draft standards delta with rationale/expected gain/impact.
3. Validate non-negotiables and ownership boundaries.
4. Apply updates with mirror synchronization and integrity-check.

## Output Contract

- Standards change proposal with evidence and risk impact.

## Governance Notes

- Never weaken non-negotiables without explicit risk acceptance.

### Post-Action Validation

- After modifying standards, run integrity-check to verify 7/7 categories pass.
- Run contract-compliance against framework-contract.md to verify no regression.
- If validation fails, fix issues and re-validate (max 3 attempts per iteration limits).

## References

- `agents/review.md`
- `skills/integrity/SKILL.md`
