# ai-engineering

Governance framework that turns any repository into a governed AI workspace with mandatory local enforcement, observability, and DevSecOps.

## Quick Start

```bash
pip install ai-engineering
ai-eng install .
ai-eng doctor
```

## Agents (10)

Agents are roles with judgment about WHEN and WHY. Invoke with `/ai:<name>`.

| Agent | What it does | When to use |
|-------|-------------|-------------|
| **plan** | Plans work, creates specs | Starting any non-trivial work |
| **execute** | Coordinates agent dispatch | Running an approved plan |
| **guard** | Proactive governance advisory | Checking compliance before committing |
| **build** | Writes code (ONLY code writer) | Implementing features, fixing bugs |
| **verify** | Assesses quality, security, governance | Reviewing code, pre-release checks |
| **ship** | Commits, PRs, releases, triage | Delivering work |
| **observe** | Metrics, dashboards, self-improvement | Checking project health |
| **guide** | Teaches, onboards, explains | Understanding code or architecture |
| **write** | Authors documentation | Creating or improving docs |
| **operate** | Runs runbooks, handles incidents | Operational automation |

## Skills (40)

Skills are procedures about HOW. Each agent composes skills at runtime.

| Domain | Skills |
|--------|--------|
| Planning | plan, discover, spec, risk, standards, lifecycle, contract, cleanup |
| Build | code, test, debug, refactor, simplify, api, cli, schema, pipeline, infra, migrate |
| Verify | security, quality, governance, performance, accessibility, architecture, gap |
| Ship | commit, pr, release, changelog, triage |
| Observe | dashboard, evolve |
| Guide | guide, onboard, explain |
| Write | document |
| Operate | ops |
| Guard | guard |
| Execute | dispatch |

## Workflow

```
/ai:plan → creates spec + execution plan → STOP
(human reviews and approves)
/ai:execute → dispatches agents per plan → build, verify, ship
/ai:observe → check health metrics
/ai:guard → proactive governance check
/ai:guide → learn about the codebase
```

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
