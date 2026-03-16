---
name: ai-standards
description: "Propose and apply standards updates from measurable evidence (gate failures,"
---


# Adaptive Standards

## Purpose

Define a controlled loop for proposing standards updates from measurable evidence.

## Trigger

- Recurring failures/friction in governed workflows.
- New risks or platform changes requiring policy updates.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"standards"}'` at skill start. Fail-open — skip if ai-eng unavailable.

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

- `.claude/agents/ai-verify.md` — governance scan mode.
- `.claude/skills/ai-governance/SKILL.md` — integrity, compliance, ownership.
$ARGUMENTS
