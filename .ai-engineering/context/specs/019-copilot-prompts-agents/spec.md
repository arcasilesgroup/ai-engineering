# Spec-019: GitHub Copilot Prompt Files & Custom Agents Integration

## Objective

Add GitHub Copilot prompt files (`.github/prompts/*.prompt.md`) and custom agent files (`.github/agents/*.agent.md`) to the framework, providing interactive `/command` and `@agent` experiences in VS Code Copilot Chat equivalent to the existing Claude Code slash commands.

## Scope

- Create 46 prompt wrapper files mapping to all 46 skills.
- Create 9 agent wrapper files mapping to all 9 agents.
- Deploy to both dogfooding (`.github/`) and installer templates (`src/ai_engineering/templates/project/`).
- Wire into installer (`_PROJECT_TEMPLATE_TREES`), ownership (`defaults.py`), manifest (`manifest.yml`), and validator (mirror sync checks).
- Update all 8 instruction files with Copilot Integration documentation.
- Add tests for installer, validator, and updater coverage.

## Design Decisions

- **Flat naming with category prefix** for prompts: `dev-debug.prompt.md` (Copilot Chat shows a flat list).
- **Thin wrappers**: same pattern as `.claude/commands/` -- point to canonical skill/agent file, no content duplication.
- **Agent files in `.github/agents/`**: appear in VS Code agent dropdown, not the `/` command list.

## Success Criteria

- 46 prompt files + 9 agent files exist in both `.github/` and `templates/project/`.
- `ai-eng install` creates `.github/prompts/` and `.github/agents/` directories.
- `ai-eng validate` mirror-sync check covers prompts and agents.
- 100% test coverage maintained.
- All quality gates pass.
