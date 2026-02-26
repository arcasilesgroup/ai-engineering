---
spec: "024"
total: 22
completed: 22
last_session: "2026-02-26"
next_session: "Complete"
---

# Tasks — Model Tiering + Documentation Enforcement

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/024-model-tiering-doc-enforcement`
- [x] 0.2 Scaffold spec files (spec.md, plan.md, tasks.md)
- [x] 0.3 Update `_active.md` to point to spec-024
- [x] 0.4 Record D024-001 and D024-002 in `decision-store.json`

## Phase 1: Schema [S]

- [x] 1.1 Add `model_tier` to skill frontmatter Optional Fields in `skills-schema.md`
- [x] 1.2 Add Model Tier Standard section to `skills-schema.md`
- [x] 1.3 Add `model_tier` as optional field in agent frontmatter schema

## Phase 2: Tier Assignment [S] ║ Phase 4

- [x] 2.1 Add `model_tier: fast` to `skills/workflows/commit/SKILL.md`
- [x] 2.2 Add `model_tier: fast` to `skills/workflows/pr/SKILL.md`
- [x] 2.3 Add `model_tier: fast` to `skills/workflows/acho/SKILL.md`
- [x] 2.4 Add `model_tier: fast` to `skills/workflows/cleanup/SKILL.md`
- [x] 2.5 Add `model_tier: fast` to `skills/workflows/pre-implementation/SKILL.md`

## Phase 3: Wrappers [S] ║ Phase 4

- [x] 3.1 Update 5 Claude Code command wrappers with model tier hints
- [x] 3.2 Update 5 Copilot prompt wrappers with advisory model tier notes

## Phase 4: Documentation Gate [M] ║ Phase 2-3

- [x] 4.1 Add documentation gate step to `/commit` SKILL.md (step 5)
- [x] 4.2 Add documentation gate step to `/pr` SKILL.md + PR checklist
- [x] 4.3 Add documentation gate inheritance note to `/acho` SKILL.md

## Phase 5: Standards Alignment [S]

- [x] 5.1 Add doc gate to `core.md` non-negotiables
- [x] 5.2 Add doc gate to `quality/core.md` gate table
- [x] 5.3 Add `model_tier` to `manifest.yml` commands section

## Phase 6: Registration + Integrity [S]

- [x] 6.1 Sync template mirrors
- [x] 6.2 Update CHANGELOG.md with spec-024 entries
- [ ] 6.3 Run `integrity-check`
