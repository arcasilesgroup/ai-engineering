# ADR-0007 — Screaming Architecture (Folder Structure)

- **Status**: Accepted
- **Date**: 2026-04-27

## Context

Robert Martin's "Screaming Architecture" principle: when you look at the
top-level folder structure, it should *scream* the domain, not the
framework.

## Decision

Bounded contexts at the top of each runtime package:

```
packages/runtime/src/
├── governance/   ← Gate, Decision, RiskAcceptance, Policy, ReleaseGate
├── skills/       ← Skill, Spec, Plan, Effort, Trigger
├── agents/       ← Agent, Role, Capability, Dispatch
├── observability/← Event, Lesson, Instinct, Span, Metric
├── platform/     ← IDE, Mirror, Hook, Install
├── delivery/     ← PullRequest, Branch, ReleaseCandidate
└── shared/       ← kernel + ports + schemas
```

Each context has the same internal shape:

```
<context>/
├── domain/         ← pure types + invariants
├── application/    ← use cases that compose ports + domain
└── adapters/       ← driven adapter implementations
```

A glance at `packages/runtime/src/` tells you: this is a **governance
framework with skills, agents, observability, platform support, and
delivery automation**.

## Consequences

- **Pro**: new contributors orient in seconds — "where do I add an audit
  trail rule?" → `governance/`.
- **Pro**: enforces bounded-context discipline.
- **Con**: requires upfront thinking about which bounded context something
  belongs to. Mitigated by ADR-driven decisions.
