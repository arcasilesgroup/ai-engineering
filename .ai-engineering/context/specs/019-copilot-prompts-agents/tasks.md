---
status: done
started: "2026-02-23"
completed: "2026-02-23"
---

# Tasks: Spec-019

## Phase 0: Scaffold & Activate
- [x] Create branch `feat/copilot-prompts-agents` from main
- [x] Create spec directory with spec.md, plan.md, tasks.md
- [x] Update `_active.md` to spec-019
- [x] Update `product-contract.md` Active Spec to spec-019

## Phase 1: Create Prompt & Agent Files
- [x] Create 46 prompt files in `.github/prompts/`
- [x] Create 9 agent files in `.github/agents/`
- [x] Mirror to `src/ai_engineering/templates/project/prompts/`
- [x] Mirror to `src/ai_engineering/templates/project/agents/`

## Phase 2: Framework Registration
- [x] Add tree entries to `_PROJECT_TEMPLATE_TREES`
- [x] Add ownership entries to `_DEFAULT_OWNERSHIP_PATHS`
- [x] Add `external_framework_managed` entries to both manifests
- [x] Add validator mirror check functions

## Phase 3: Documentation
- [x] Add Copilot Integration sections to 8 instruction files
- [x] Update CHANGELOG.md

## Phase 4: Tests & Verification
- [x] Add installer tests (3 new tests)
- [x] Add validator tests (8 new tests)
- [x] Add updater tests (1 new test)
- [x] Run full test suite with 100% coverage (641 tests, 100%)
- [x] Run quality checks (ruff, ty, pip-audit — all pass)
- [x] Run `ai-eng validate` (7/7 categories pass)
