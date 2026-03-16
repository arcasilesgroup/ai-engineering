# ai-engineering

Governance framework that turns any repository into a governed AI workspace with mandatory local enforcement, observability, and DevSecOps.

## Quick Start

```bash
pip install ai-engineering
ai-eng install .
ai-eng doctor
```

## Agents (8)

Agents are roles with judgment about WHEN and WHY. Invoke with `/ai:<name>`.

| Agent | When to use |
|-------|-------------|
| **plan** | Architecture design, spec creation, roadmap guidance |
| **build** | Implementation across all stacks (ONLY code writer) |
| **verify** | 7-mode scanning: governance, security, quality, performance, a11y, feature-gap, architecture |
| **guard** | Proactive governance advisory, drift detection |
| **guide** | Teaching, onboarding, architecture tours |
| **operate** | Runbook execution, incident response |
| **explorer** | Deep codebase research, context gathering before other agents |
| **simplifier** | Code simplification: guard clauses, extract methods, flatten nesting |

## Skills (38)

Skills are procedures about HOW. Each agent composes skills at runtime.

| Domain | Skills |
|--------|--------|
| Planning (5) | plan, discover, spec, risk, dispatch |
| Build (10) | code, test, debug, refactor, simplify, api, schema, pipeline, infra, migrate |
| Verify (7) | security, quality, governance, performance, accessibility, architecture, gap |
| Delivery (5) | commit, pr, release, changelog, triage |
| Observe (2) | dashboard, evolve |
| Governance & Ops (9) | guard, standards, lifecycle, contract, cleanup, ops, document, explain, onboard |

## Workflow

```
/ai:plan → creates spec + execution plan → STOP
(human reviews and approves)
/ai:build → implements per plan
/ai:verify → scans for governance, security, quality issues
/ai:guard → proactive governance check
```

Three-step cycle: **plan** then **build** then **verify/guard**.

## Standards

Layered (higher tightens, never weakens):
1. `standards/framework/core.md` — non-negotiables
2. `standards/framework/stacks/` — per-technology (21 stacks)
3. `standards/framework/cross-cutting/` — error handling, testing, etc.
4. `standards/team/` — team overrides (never overwritten by framework)

## State

| File | Purpose |
|------|---------|
| `state/decision-store.json` | Persistent decisions with SHA-256 context hash |
| `state/audit-log.ndjson` | Append-only event trail (90-day retention) |
| `state/session-checkpoint.json` | Session recovery |
| `state/health-history.json` | Health score trend |

## CLI

```bash
ai-eng observe [engineer|team|ai|dora|health]
ai-eng gate [pre-commit|pre-push|all]
ai-eng doctor [--fix-hooks] [--fix-tools]
ai-eng validate
ai-eng spec [verify|catalog|list|compact]
ai-eng decision [list|expire-check]
ai-eng checkpoint [save|load]
```
