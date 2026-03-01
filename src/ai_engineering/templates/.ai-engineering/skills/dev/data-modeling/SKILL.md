---
name: data-modeling
description: "Design and validate domain data models with constraints, relationships, and migration safety."
version: 1.0.0
category: dev
tags: [data, modeling, schema, migration]
metadata:
  ai-engineering:
    scope: read-write
    token_estimate: 760
---

# Data Modeling

## Purpose

Provide a repeatable process to define robust data models aligned with domain behavior and change safety.

## Trigger

- New domain entities or schema evolution.
- Architecture review requires model clarification.

## Procedure

1. Identify entities, value objects, and invariants.
2. Define relationships/cardinality and lifecycle rules.
3. Specify constraints, indexes, and ownership boundaries.
4. Plan migration path and rollback safety.
5. Validate model against API/service contracts and tests.

## Output Contract

- Data model spec (entities, constraints, relations) and migration plan.

## Governance Notes

- Prefer explicit constraints over implicit assumptions.

## References

- `agents/architect.md`
- `agents/database-engineer.md` — agent for complex database decisions.
- `skills/dev/migration/SKILL.md`
- `skills/dev/database-ops/SKILL.md` — operational database procedures (schema DDL, query optimization, connection pooling).
- `standards/framework/stacks/dotnet.md` — EF Core entity mapping, Fluent API, migration patterns.
