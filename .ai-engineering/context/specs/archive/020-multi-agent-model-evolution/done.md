# Done: Spec-020 — Multi-Agent Model Evolution

## Summary

Evolved the agent/skill model from flat `.md` files to a directory-based architecture with machine-readable metadata. Migrated all 46 skills to `SKILL.md` directories with AgentSkills-compatible YAML frontmatter, added structured frontmatter to all 9 agents, renamed `utils/` to `patterns/`, implemented progressive disclosure guidelines, and documented token budgets. Created `standards/framework/skills-schema.md` as the definitive schema reference.

## Deliverables

- **46 skill directories**: flat `<name>.md` → `<name>/SKILL.md` with YAML frontmatter (name, description, version, category, tags, metadata)
- **9 agent frontmatter blocks**: structured metadata (name, version, scope, capabilities, inputs, outputs, references)
- **Skills schema standard**: `standards/framework/skills-schema.md` — directory layout, gating metadata, agent schema, token budgets
- **Rename**: `skills/utils/` → `skills/patterns/` (6 skills) with all cross-references updated
- **3 pilot resources**: `commit/scripts/`, `debug/references/`, `security/references/`
- **Progressive disclosure**: three-level loading model (metadata → body → resources) documented in CLAUDE.md
- **Token budget**: session start ~500 tokens (99.14% deferred), full inventory by category and agent
- **Cross-references**: all 8 instruction files, command wrappers, prompts, agents, manifest updated
- **Mirror sync**: all canonical files replicated to `src/ai_engineering/templates/.ai-engineering/`

## Decisions

| ID | Decision |
|----|----------|
| D020-001 | Skills migrate to directories with SKILL.md (AgentSkills-compatible) |
| D020-002 | Agent metadata is additive frontmatter, not replacement |
| D020-003 | `utils/` renamed to `patterns/` |
| D020-004 | Skill gating is metadata-only (no runtime enforcement yet) |
| D020-005 | Progressive disclosure is advisory, not enforced |

## Verification

- Content integrity check: 7/7 categories PASS
- 12/12 acceptance criteria verified
- 46/46 skills with valid frontmatter
- 9/9 agents with structured frontmatter
- All cross-references resolved (0 stale refs)
- Mirror sync: canonical ↔ template byte-identical
- Token efficiency: 0.86% loaded at session start

## Commits

| Commit | Phase | Description |
|--------|-------|-------------|
| Phase 0 | Scaffold | Spec directory, branch, active pointer |
| Phase 1 | Schema & Standards | skills-schema.md, core.md updates |
| Phase 2 | Migration (workflows + govern) | 16 skills migrated |
| Phase 3 | Migration (dev + review + quality) | 20 skills migrated |
| Phase 4 | Migration (docs + patterns) | 10 skills migrated, utils → patterns |
| Phase 5 | Agent Frontmatter | 9 agents with structured metadata |
| Phase 6 | Pilot Resources | 3 skills with scripts/references |
| Phase 7 | Cross-References | All 8 instruction files + wrappers updated |
| Phase 8 | Progressive Disclosure | CLAUDE.md guidelines, token budget table |
| Phase 9 | Integrity Check | Remediation of stale refs + mirror sync |
