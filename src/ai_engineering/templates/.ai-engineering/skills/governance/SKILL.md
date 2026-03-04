---
name: governance
description: "Unified governance validation: integrity, compliance, ownership, operational readiness. Modes: integrity | compliance | ownership | operational."
metadata:
  version: 2.0.0
  tags: [governance, integrity, compliance, ownership, validation]
  ai-engineering:
    scope: read-write
    token_estimate: 1000
---

# Governance

## Purpose

Unified governance validation covering cross-reference integrity, contract compliance, ownership boundaries, and operational readiness. Consolidates integrity, compliance, ownership, and install skills.

## Trigger

- Command: `/ai:scan governance` or `/ai:governance [integrity|compliance|ownership|operational]`
- Context: governance audit, pre-release governance check, post-install verification.

## Modes

### integrity — Cross-reference validation
Validate manifest counters, agent-skill references, command files, state files.
CLI: `ai-eng integrity`

### compliance — Contract validation
Validate framework contracts against implementation. Check that documented rules are enforced.
CLI: `ai-eng compliance`

### ownership — Boundary validation
Validate ownership boundaries: who can modify what, boundary violations.
CLI: `ai-eng ownership`

### operational — Install verification
Verify post-install readiness: tools, hooks, state files, permissions.
CLI: `ai-eng doctor`

## Procedure

1. **Run CLI** -- `ai-eng integrity|compliance|ownership` for deterministic checks.
2. **Interpret** -- LLM analyzes findings for systemic patterns.
3. **Report** -- uniform scan output contract with score 0-100.
