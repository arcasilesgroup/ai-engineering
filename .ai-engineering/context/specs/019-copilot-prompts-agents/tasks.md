---
status: in-progress
started: "2026-02-23"
---

# Tasks: Spec-019

## Phase 0: Scaffold & Activate
- [x] Create branch `feat/copilot-prompts-agents` from main
- [x] Create spec directory with spec.md, plan.md, tasks.md
- [ ] Update `_active.md` to spec-019
- [ ] Update `product-contract.md` Active Spec to spec-019

## Phase 1: Create Prompt & Agent Files
- [ ] Create 46 prompt files in `.github/prompts/`
- [ ] Create 9 agent files in `.github/agents/`
- [ ] Mirror to `src/ai_engineering/templates/project/prompts/`
- [ ] Mirror to `src/ai_engineering/templates/project/agents/`

## Phase 2: Framework Registration
- [ ] Add tree entries to `_PROJECT_TEMPLATE_TREES`
- [ ] Add ownership entries to `_DEFAULT_OWNERSHIP_PATHS`
- [ ] Add `external_framework_managed` entries to both manifests
- [ ] Add validator mirror check functions

## Phase 3: Documentation
- [ ] Add Copilot Integration sections to 8 instruction files
- [ ] Update CHANGELOG.md

## Phase 4: Tests & Verification
- [ ] Add installer tests
- [ ] Add validator tests
- [ ] Add updater tests
- [ ] Run full test suite with 100% coverage
- [ ] Run quality checks (ruff, ty, gitleaks)
- [ ] Run `ai-eng validate`
