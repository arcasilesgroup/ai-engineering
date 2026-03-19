---
spec: "023"
approach: "mixed"
---

# Plan — Multi-Stack Expansion + Audit-Driven Hardening

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `standards/framework/stacks/typescript.md` | Generic TypeScript stack standard |
| `standards/framework/stacks/react.md` | React stack standard (extends TS) |
| `standards/framework/stacks/react-native.md` | React Native stack standard |
| `standards/framework/stacks/nestjs.md` | NestJS stack standard |
| `standards/framework/stacks/astro.md` | Astro stack standard |
| `standards/framework/stacks/rust.md` | Rust stack standard |
| `standards/framework/stacks/node.md` | Node.js backend stack standard |
| `standards/framework/stacks/bash-powershell.md` | Shell scripting stack standard |
| `standards/framework/stacks/azure.md` | Azure cross-cutting standard |
| `standards/framework/stacks/infrastructure.md` | IaC/cloud cross-cutting standard |
| `standards/framework/stacks/database.md` | SQL/data cross-cutting standard |
| `agents/infrastructure-engineer.md` | IaC and cloud provisioning agent |
| `agents/database-engineer.md` | Database engineering agent |
| `agents/frontend-specialist.md` | Frontend/UI architecture agent |
| `agents/api-designer.md` | Contract-first API agent |
| `skills/dev/api-design/SKILL.md` | API design skill |
| `skills/dev/infrastructure/SKILL.md` | Infrastructure provisioning skill |
| `skills/review/accessibility/SKILL.md` | Accessibility review skill |
| `skills/dev/database-ops/SKILL.md` | Database operations skill |

### Modified Files

| File | Change |
|------|--------|
| `standards/framework/core.md` | Add 3 behavioral baselines |
| `standards/framework/skills-schema.md` | Add 3 behavioral patterns + token inventory |
| `standards/framework/stacks/nextjs.md` | Add TS base reference |
| `agents/devops-engineer.md` | Multi-platform deployment |
| `agents/architect.md` | Infrastructure architecture |
| `agents/security-reviewer.md` | Cloud security |
| `agents/orchestrator.md` | Parallel-first, exhaustiveness |
| `agents/principal-engineer.md` | Exhaustiveness, multi-stack |
| `agents/test-master.md` | Multi-stack testing |
| `skills/dev/cicd-generate/SKILL.md` | Azure Pipelines, Railway, Cloudflare |
| `skills/dev/deps-update/SKILL.md` | Multi-stack deps |
| `skills/review/security/SKILL.md` | Cloud + IaC security |
| `skills/dev/references/delivery-platform-patterns.md` | Expand from stub |
| `skills/dev/references/language-framework-patterns.md` | Expand from stub |
| `skills/dev/references/database-patterns.md` | Expand from stub |
| `skills/dev/references/api-design-patterns.md` | Expand from stub |
| `skills/dev/references/platform-detect.md` | Expand from stub |
| `skills/dev/references/git-helpers.md` | Expand from stub |

### Mirror Copies

All new files require template mirrors in `src/ai_engineering/templates/.ai-engineering/`.

## Session Map

| Phase | Name | Size | Sessions | Parallel |
|-------|------|------|----------|----------|
| 0 | Scaffold | S | 1 | — |
| 1 | Stack Standards | L | 1-2 | ║ Phase 2 |
| 2 | Cross-Cutting Standards | M | 1 | ║ Phase 1 |
| 3 | Behavioral Hardening | L | 2-3 | Serial |
| 4 | New Agents + Skills | L | 2 | Serial |
| 5 | Registration + Integrity | L | 2 | Serial |

## Patterns

- Follow `python.md` as template for all stack standards.
- Follow `principal-engineer.md` as template for all agents.
- Follow `code-review/SKILL.md` as template for all skills.
- One atomic commit per phase.
- Decisions recorded in `decision-store.json`.
- integrity-check at Phase 5 closure.
