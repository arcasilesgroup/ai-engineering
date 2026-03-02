---
id: "031"
slug: "framework-optimization"
status: "in-progress"
created: "2026-03-02"
---

# Spec 031 — Architecture Refactor: Agents, Skills & Standards

## Problem

19 narrow-specialist agents + 44 skills across 6 nested categories = 76+ synchronized files. This is misaligned with the vision of few powerful agents composing skills. The current structure creates:

- **Agent sprawl**: 19 agents with overlapping capabilities and unclear boundaries.
- **Nested complexity**: 6 skill categories (`dev/`, `review/`, `docs/`, `govern/`, `quality/`, `workflows/`) with 7 different command prefixes (`dev:`, `review:`, etc.).
- **Sync burden**: every agent/skill change requires updates across ~4 mirror locations (`.ai-engineering/`, `.github/agents/`, `.github/prompts/`, `.claude/commands/`, `src/ai_engineering/templates/`).
- **No work-item integration**: specs exist locally but don't sync to Azure Boards / GitHub Issues.
- **Missing planning pipeline**: no structured discovery → prompt → spec → dispatch flow.

## Solution

Consolidate to 6 role-based agents with `ai:` prefix, flatten skills to a single directory, unify command namespace, add work-item integration and a default planning pipeline.

### Core Changes

1. **6 agents** (`ai:plan`, `ai:build`, `ai:review`, `ai:scan`, `ai:write`, `ai:triage`) replace 19.
2. **Flat skill organization** — `skills/<name>/` replaces `skills/<category>/<name>/`.
3. **Unified `ai:` command prefix** — replaces 7 prefixes.
4. **47 skills** — 44 renamed + 3 new (`work-item`, `agent-card`, `triage`).
5. **Work-item integration** — Azure Boards + GitHub Issues bidirectional sync.
6. **Planning pipeline** — plan → discover → prompt → spec → work-item → dispatch.
7. **Only `ai:build` has code write permissions** — all other agents are read-only or docs-only.

## Scope

### In Scope

- Author 6 new agent definitions.
- Restructure 44 skills from nested categories to flat.
- Author 3 new skills (`work-item`, `agent-card`, `triage`).
- Update `manifest.yml`, `skills-schema.md`, `CLAUDE.md`, `AGENTS.md`.
- Restructure `.github/agents/`, `.github/prompts/`, `.claude/commands/`.
- Update `src/ai_engineering/templates/` mirrors.
- Delete 19 old agent files + old mirrors (~160+ files).
- Update all cross-references.

### Out of Scope

- Runtime Python code changes (except template mirrors).
- CI workflow changes.
- New test coverage for new skills (follow-up spec).
- Actual Azure Boards / GitHub Issues API implementation (skill defines the contract only).
- Agent card export implementation (skill defines the contract only).

## Acceptance Criteria

1. Exactly 6 agent files in `.ai-engineering/agents/`.
2. Exactly 47 skill directories in `.ai-engineering/skills/` (flat, no category subdirs).
3. `manifest.yml` reports 6 agents, 47 skills.
4. `CLAUDE.md` and `AGENTS.md` reference 6 agents, 47 skills, `ai:` prefix only.
5. All `.github/agents/` files match new 6-agent structure.
6. All `.github/prompts/` files match new 47-skill structure with `ai-` prefix.
7. All `.claude/commands/` files restructured under `ai/` namespace.
8. Template mirrors in `src/ai_engineering/templates/` are byte-identical to source.
9. Zero orphaned references to old agent names or old category paths.
10. `ruff check` + `ruff format --check` pass.
11. Each agent has clearly defined permissions (read-only vs read-write) and skill roster.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-031-001 | 6 role-based agents replace 19 narrow specialists | Aligns with vision of few powerful agents composing skills; reduces sync overhead |
| D-031-002 | Flat skill organization (no categories) | Eliminates nesting complexity; skills are tagged instead of categorized |
| D-031-003 | Unified `ai:` command prefix | Single namespace is simpler to discover and type |
| D-031-004 | Only `ai:build` has code write permissions | Security principle: minimize write surface |
| D-031-005 | `ai:review` uses individual modes (not sub-agents) | Single agent with mode flags is simpler than specialized sub-agents |
| D-031-006 | `ai:scan` is read-only spec-vs-code gap analysis | Distinct from review (which checks code quality); scan checks feature completeness |
| D-031-007 | `ai:triage` manages work-item prioritization | Inspired by Scanner → Triage → Executor → Validation pipeline pattern |
| D-031-008 | 3 new skills: work-item, agent-card, triage | Work-item enables external integration; agent-card enables platform portability; triage enables auto-prioritization |
