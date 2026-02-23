---
spec: "020"
total: 38
completed: 22
last_session: "2026-02-23"
next_session: "Phase 5 — Agent Frontmatter Evolution"
---

# Tasks — Multi-Agent Model Evolution

## Phase 0: Scaffold [S]

- [x] 0.1 Create feature branch `feat/multi-agent-model-evolution`
- [x] 0.2 Create spec directory `020-multi-agent-model-evolution/`
- [x] 0.3 Create spec.md, plan.md, tasks.md
- [x] 0.4 Update `_active.md` to point to spec-020
- [x] 0.5 Update `product-contract.md` active spec reference

## Phase 1: Schema & Standards [M]

- [x] 1.1 Define skill directory schema in `standards/framework/core.md` (SKILL.md format, directory layout, frontmatter requirements)
- [x] 1.2 Define skill gating metadata schema (stacks, bins, env, os fields, always flag)
- [x] 1.3 Define agent structured frontmatter schema (capabilities, scope, inputs, outputs, tool restrictions)
- [x] 1.4 Create `standards/framework/skills-schema.md` with full schema documentation and examples
- [x] 1.5 Document token budget guidelines (measurement formula, per-category estimates)

## Phase 2: Skill Directory Migration — Workflows + Govern [L]

- [x] 2.1 Migrate `skills/workflows/commit.md` → `skills/workflows/commit/SKILL.md`
- [x] 2.2 Migrate `skills/workflows/pr.md` → `skills/workflows/pr/SKILL.md`
- [x] 2.3 Migrate `skills/workflows/acho.md` → `skills/workflows/acho/SKILL.md`
- [x] 2.4 Migrate `skills/workflows/pre-implementation.md` → `skills/workflows/pre-implementation/SKILL.md`
- [x] 2.5 Migrate `skills/workflows/cleanup.md` → `skills/workflows/cleanup/SKILL.md`
- [x] 2.6 Migrate all 11 `skills/govern/*.md` → `skills/govern/*/SKILL.md`

## Phase 3: Skill Directory Migration — Dev + Review + Quality [L]

- [x] 3.1 Migrate all 8 `skills/dev/*.md` → `skills/dev/*/SKILL.md`
- [x] 3.2 Migrate all 5 `skills/review/*.md` → `skills/review/*/SKILL.md`
- [x] 3.3 Migrate all 7 `skills/quality/*.md` → `skills/quality/*/SKILL.md`

## Phase 4: Skill Directory Migration — Docs + Patterns (rename) [M]

- [x] 4.1 Migrate all 4 `skills/docs/*.md` → `skills/docs/*/SKILL.md`
- [x] 4.2 Rename `skills/utils/` → `skills/patterns/`
- [x] 4.3 Migrate all 6 `skills/patterns/*.md` → `skills/patterns/*/SKILL.md`

## Phase 5: Agent Frontmatter Evolution [M]

- [ ] 5.1 Add structured frontmatter to `agents/architect.md`
- [ ] 5.2 Add structured frontmatter to `agents/debugger.md`
- [ ] 5.3 Add structured frontmatter to `agents/principal-engineer.md`
- [ ] 5.4 Add structured frontmatter to `agents/security-reviewer.md`
- [ ] 5.5 Add structured frontmatter to `agents/quality-auditor.md`
- [ ] 5.6 Add structured frontmatter to `agents/codebase-mapper.md`
- [ ] 5.7 Add structured frontmatter to `agents/code-simplifier.md`
- [ ] 5.8 Add structured frontmatter to `agents/platform-auditor.md`
- [ ] 5.9 Add structured frontmatter to `agents/verify-app.md`

## Phase 6: Pilot Resources [M]

- [ ] 6.1 Create `skills/workflows/commit/scripts/` with deterministic pre-commit gate helper
- [ ] 6.2 Create `skills/dev/debug/references/` with on-demand diagnostic reference
- [ ] 6.3 Create `skills/review/security/references/` with OWASP quick-reference loaded on-demand

## Phase 7: Cross-Reference Update [L]

- [ ] 7.1 Update CLAUDE.md — all skill/agent path references, progressive disclosure section
- [ ] 7.2 Update AGENTS.md — all path references
- [ ] 7.3 Update codex.md — all path references
- [ ] 7.4 Update `.github/copilot-instructions.md` — all path references
- [ ] 7.5 Update `.github/instructions/**` — all path references
- [ ] 7.6 Update `.github/prompts/**` — all command paths
- [ ] 7.7 Update `.github/agents/**` — all agent paths
- [ ] 7.8 Update `.claude/commands/**` — all skill paths
- [ ] 7.9 Update `manifest.yml` — reflect directory structure
- [ ] 7.10 Update all internal cross-references within skills and agents

## Phase 8: Progressive Disclosure & Token Budget [M]

- [ ] 8.1 Add progressive disclosure guidelines to CLAUDE.md (on-demand loading instructions)
- [ ] 8.2 Create token budget table (characters/tokens per skill category, per agent)
- [ ] 8.3 Update `product-contract.md` KPIs with token efficiency metric

## Phase 9: Integrity Check & Close [S]

- [ ] 9.1 Run `govern/integrity-check` — verify all 6 categories pass
- [ ] 9.2 Verify all 12 acceptance criteria
- [ ] 9.3 Create `done.md`
- [ ] 9.4 Update `tasks.md` frontmatter to CLOSED
