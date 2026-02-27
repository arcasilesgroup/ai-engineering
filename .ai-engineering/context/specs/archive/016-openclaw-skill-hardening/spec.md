---
id: "016"
slug: "openclaw-skill-hardening"
status: "in-progress"
created: "2026-02-23"
---

# Spec-016: OpenClaw-Inspired Skill & Standards Hardening

## Problem

Skills lack structured dependency metadata, anti-pattern documentation, and machine-readable frontmatter. The test strategy defines coverage targets but has no tier classification (unit/integration/e2e/live). No diagnostic command consolidates environment verification into a single pass. Agent orchestration patterns are undocumented.

These gaps were identified through a comparative audit of the OpenClaw project, which implements mature versions of these patterns in its skill system (YAML frontmatter with install gating, anti-pattern sections, multi-agent coordination, tiered test configuration).

## Solution

Six enhancements inspired by OpenClaw patterns:

1. **YAML frontmatter** on all 43 skills — structured metadata (name, version, category, tags) enabling machine validation, indexing, and catalog generation.
2. **Anti-pattern sections** — explicit "When NOT to Use" on skills with high confusion risk, reducing incorrect invocations.
3. **Test tiers** — formal unit/integration/e2e/live classification in Python stack contract and quality standards, mapped to gate stages.
4. **Doctor skill** (`utils:doctor`) — unified environment diagnostics covering binaries, hooks, git state, governance health, and stack detection.
5. **Multi-agent orchestration skill** (`dev:multi-agent`) — documented patterns for parallel agent execution, result consolidation, and workspace isolation.
6. **Skill install gating** — `requires.bins` field in frontmatter for skills that depend on external binaries, enabling pre-execution dependency verification.

## Scope

### In Scope

- YAML frontmatter addition to all 43 existing skills.
- Anti-pattern sections on 6+ confusable skill pairs.
- Test tier classification in `standards/framework/stacks/python.md` and `standards/framework/quality/core.md`.
- New skill: `utils:doctor` with slash command wrapper.
- New skill: `dev:multi-agent` with slash command wrapper.
- `requires.bins` field on skills with external binary dependencies.
- Governance updates: `integrity-check.md` frontmatter validation, `create-skill.md` template update.
- Cross-reference updates: instruction files, product-contract counters (43 to 45 skills).

### Out of Scope

- Python runtime changes (no code modifications to `src/`).
- CLI implementation of doctor or multi-agent commands.
- OpenClaw code reuse (patterns are adapted, not copied).
- Frontmatter schema enforcement in CI/CD (future spec).

## Acceptance Criteria

1. All 43 existing skills have valid YAML frontmatter with at least `name`, `version`, `category` fields.
2. All skills with external binary dependencies declare `requires.bins` in frontmatter.
3. At least 6 skills have explicit "When NOT to Use" anti-pattern sections.
4. Python stack contract defines 4 test tiers (unit, integration, e2e, live) with gate mapping.
5. `utils:doctor` skill created, registered, with slash command wrapper.
6. `dev:multi-agent` skill created, registered, with slash command wrapper.
7. `integrity-check` skill updated to validate frontmatter presence.
8. `create-skill` template updated to include YAML frontmatter.
9. Instruction file counters updated to reflect 45 skills.
10. `integrity-check` passes with zero violations after all changes.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| S016-001 | Supersede spec-015 as active spec | Spec-015 work is stable; this spec addresses different scope (skill quality vs multi-stack security) |
