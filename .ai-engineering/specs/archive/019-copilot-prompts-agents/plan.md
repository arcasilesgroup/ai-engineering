# Plan: Spec-019 — Copilot Prompts & Agents

## Phases

### Phase 0: Scaffold & Activate [S]
- Create spec directory and files.
- Update `_active.md` and `product-contract.md`.

### Phase 1: Create Prompt & Agent Files [L]
- 46 prompt files in `.github/prompts/` and `templates/project/prompts/`.
- 9 agent files in `.github/agents/` and `templates/project/agents/`.
- Thin wrapper pattern matching `.claude/commands/`.

### Phase 2: Framework Registration [M]
- Add `("prompts", ".github/prompts")` and `("agents", ".github/agents")` to `_PROJECT_TEMPLATE_TREES`.
- Add ownership entries for `.github/prompts/**` and `.github/agents/**`.
- Add `external_framework_managed` entries to both manifest files.
- Add `_check_copilot_prompts_mirror()` and `_check_copilot_agents_mirror()` to validator.

### Phase 3: Documentation [M]
- Add Copilot Integration section to all 8 instruction files.
- Update CHANGELOG.md.

### Phase 4: Tests & Verification [M]
- Add installer, validator, and updater tests.
- Run full test suite, quality checks, validation.
