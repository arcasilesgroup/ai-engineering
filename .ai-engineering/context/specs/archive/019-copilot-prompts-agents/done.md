# Done: Spec-019 — GitHub Copilot Prompt Files & Custom Agents Integration

## Summary

Added 46 GitHub Copilot prompt files and 9 custom agent files to the framework, deployed to both the dogfooding repo (`.github/prompts/`, `.github/agents/`) and installer templates (`src/ai_engineering/templates/project/`). Wired into installer, ownership, manifest, validator mirror-sync, and all 8 instruction files.

## Deliverables

- **110 new files**: 46 prompts + 9 agents × 2 locations
- **Installer**: `_PROJECT_TEMPLATE_TREES` includes `prompts` and `agents`
- **Ownership**: `.github/prompts/**` and `.github/agents/**` are FRAMEWORK_MANAGED
- **Manifest**: `external_framework_managed` entries added to both copies
- **Validator**: `_check_copilot_prompts_mirror()` and `_check_copilot_agents_mirror()` added
- **Documentation**: Copilot Integration section added to all 8 instruction files
- **Tests**: 12 new tests (3 installer, 8 validator, 1 updater)

## Verification

- 641 tests pass, 100% coverage
- ruff check + format: 0 issues
- ty check: 0 errors
- pip-audit: 0 vulnerabilities
- `ai-eng validate`: 7/7 categories pass
