---
id: "023"
slug: "multi-stack-audit-hardening"
status: "in-progress"
created: "2026-02-26"
---

# Spec 023 — Multi-Stack Expansion + Audit-Driven Hardening

## Problem

ai-engineering supports only 3 stack standards (Python, .NET, Next.js) and lacks behavioral patterns discovered by auditing 35+ AI tool system prompts. The framework cannot serve as a definitive multi-stack governance baseline for teams using diverse tech stacks (.NET/C#, TypeScript, React, React Native, Rust, NestJS, Astro, Azure, database, infrastructure, etc.).

## Solution

1. **Expand stack coverage** — add 8 new stack standards and 3 cross-cutting standards covering the full target surface.
2. **Harden behavioral baselines** — integrate patterns from 35+ AI tool audit (holistic analysis, exhaustiveness, parallel-first execution) into framework standards, agents, and skills.
3. **Fill capability gaps** — create 4 new agents and 4 new skills for infrastructure, database, frontend, and API domains.
4. **Expand references** — populate stub reference files with actionable multi-stack patterns.

## Scope

### In Scope

- 8 new stack standards: TypeScript, React, React Native, NestJS, Astro, Rust, Node.js, Bash/PowerShell.
- 3 cross-cutting standards: Azure, Infrastructure, Database.
- 3 new behavioral baselines: Holistic Analysis, Exhaustiveness, Parallel-First.
- 6 existing agent improvements: devops-engineer, architect, security-reviewer, orchestrator, principal-engineer, test-master.
- 3 existing skill improvements: cicd-generate, deps-update, security.
- 6 reference file expansions: delivery-platform-patterns, language-framework-patterns, database-patterns, api-design-patterns, platform-detect, git-helpers.
- 4 new agents: infrastructure-engineer, database-engineer, frontend-specialist, api-designer.
- 4 new skills: api-design, infrastructure, accessibility, database-ops.
- Full registration: manifest, instruction files, template mirrors, command wrappers.

### Out of Scope

- Python runtime changes (CLI, installer, updater).
- Remote skills infrastructure.
- VCS provider integration changes.
- CI/CD pipeline execution (generation only, not runtime).
- Documentation site.

## Acceptance Criteria

1. All 11 new stack/cross-cutting standards exist in `standards/framework/stacks/` and follow `python.md` structure.
2. All 4 new agents follow the agent template (frontmatter + full persona sections).
3. All 4 new skills follow the skill schema (frontmatter + SKILL.md body with references).
4. 3 new behavioral baselines added to `core.md` and `skills-schema.md`.
5. 6 existing agents updated with audit-derived improvements.
6. 3 existing skills updated with multi-stack support.
7. 6 reference files expanded from stubs to substantive content.
8. `integrity-check` passes all 7 categories after completion.
9. Template mirrors are byte-identical with canonical files.
10. All 6 instruction files list identical agents/skills/standards.
11. Manifest counts match actual directory contents.
12. Agent count stays under 20 (decision D021-002).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D023-001 | Extend D021-004: add database-engineer agent alongside data-modeling skill | Complex DB work requires judgment (schema trade-offs, perf tuning); skill provides procedure, agent provides judgment. |
| D023-002 | Cross-cutting standards (azure, infrastructure, database) in stacks/ directory | Same path pattern as existing stacks; no enforcement gates, advisory only. Clearly marked as cross-cutting. |
| D023-003 | typescript.md as base for React/NestJS/Astro stacks | Avoids content duplication; framework-specific stacks reference TS base for shared patterns. |
