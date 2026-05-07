# Operational Principles

This document is the canonical operational standard for everyday implementation and review guidance. Hard-rule governance for spec-driven development, TDD, and proof-before-done remains in the Constitution surfaces; this file carries the operational subset those surfaces delegate.

## Principles

### YAGNI

Build only what the approved spec and the current failing tests require. Defer speculative extensions until a concrete need exists.

### DRY

Eliminate duplication when repeated logic or knowledge would otherwise drift. Do not introduce shared abstractions before the repetition is real and stable.

### KISS

Prefer the simplest design that fully satisfies the requirement, keeps intent obvious, and minimizes moving parts.

### SOLID

Use object boundaries and abstractions only when they materially improve changeability, cohesion, or substitution. Keep responsibilities explicit and proportionate to the actual problem.

### Clean Architecture

Keep business rules isolated from framework, IO, and delivery details when the problem warrants that separation. Dependencies should point toward policy, not infrastructure.

### Clean Code

Optimize for readability, small cohesive units, explicit names, and straightforward control flow so the next engineer can change the code safely.

## Consumption Rule

Core implementation and review surfaces should reference `.ai-engineering/contexts/operational-principles.md` instead of restating this operational subset ad hoc.