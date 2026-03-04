---
name: architecture
description: "Analyze software architecture: drift detection, coupling, cohesion, boundaries, tech debt assessment."
metadata:
  version: 2.0.0
  tags: [architecture, dependencies, coupling, drift, tech-debt]
  ai-engineering:
    scope: read-only
    token_estimate: 800
---

# Architecture

## Purpose

Analyze software architecture for drift from spec, coupling issues, cohesion problems, boundary violations, and technical debt. Part of the scan agent's 7-mode assessment. Renamed from arch-review for clarity.

## Trigger

- Command: `/ai:scan architecture`
- Context: architecture review, drift detection, design decision assessment.

## Procedure

1. **Read architecture docs** -- specs, ADRs, documented decisions.
2. **Map actual structure** -- imports, dependencies, call graphs, module boundaries.
3. **Detect drift** -- compare documented architecture vs actual implementation.
4. **Assess coupling** -- identify tight coupling, circular dependencies, boundary violations.
5. **Evaluate cohesion** -- modules that do too many things (God Objects).
6. **Score tech debt** -- classify findings by severity and remediation effort.
7. **Report** -- uniform scan output contract with score 0-100.

## Output

Follows uniform scan output contract (see scan agent).
Specific findings: drift items, coupling violations, cohesion issues, tech debt items.
