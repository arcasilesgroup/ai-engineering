# Changelog

All notable changes to the AI Engineering Framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-02-04

### Breaking Changes

- **Commands migrated to Skills**: `.claude/commands/` replaced by `.claude/skills/` with YAML frontmatter and model invocation control.
- **Agents consolidated**: `build-validator`, `test-runner`, `security-scanner`, `quality-checker` merged into single `verify-app` agent.
- **Install script**: `scripts/install.sh` now installs skills instead of commands. Use `--update` flag for existing projects.

### Added

- **`/commit-push-pr` skill**: Full cycle — secret scan, commit, push, create PR. Supports both GitHub (`gh`) and Azure DevOps (`az repos`).
- **Hooks system**: 4 hook scripts for auto-formatting, security guards, .env protection, and desktop notifications.
- **Platform detection**: Auto-detect GitHub vs Azure DevOps from git remote URL. Verify CLI and auth.
- **`verify-app` agent**: The "finisher" — build, tests, lint, secret scan, dependency audit, duplication check in one pass.
- **`code-architect` agent**: Read-only analysis — designs implementation approaches, proposes 2 options for high-stakes decisions.
- **`oncall-guide` agent**: Production incident debugging — root cause analysis, fix proposals, rollback plans.
- **CLAUDE.md production rules**: Verification Protocol, Reconnaissance Before Writing, Two Options for High Stakes, Danger Zones, Layered Memory, Reliability Template.
- **`CLAUDE.local.md` support**: Personal session context (sprint, work items, preferences). Not committed.
- **Versioning system**: `VERSION` file, `CHANGELOG.md`, `UPGRADING.md`, `.ai-version` per project.
- **Custom directories**: `.claude/skills/custom/` and `.claude/agents/custom/` for team extensions (never overwritten by updates).
- **Platform-specific Copilot instructions**: `.github/instructions/platform.instructions.md`.
- **Workshop module 09**: Boris Cherny workflow — the complete production reliability loop.
- **Workshop module 10**: Versioning — updates, personalization, contributing.

### Changed

- **CLAUDE.md**: Enhanced with 6 new production sections from Boris Cherny workflow.
- **`code-simplifier` agent**: Now includes reconnaissance step — searches for existing patterns before simplifying.
- **`/validate` skill**: Now includes platform configuration detection.
- **`/pr` skill**: Now supports Azure DevOps (`az repos pr create`) in addition to GitHub.
- **`.claude/settings.json`**: Added hooks configuration and `az` CLI permission.
- **`.github/copilot-instructions.md`**: Enhanced with verification protocol, danger zones, and cross-references.
- **Install script**: Added `--update` flag, skills/hooks/agents copy, platform detection, version management.

### Removed

- `.claude/commands/` directory (replaced by `.claude/skills/`)
- `build-validator` agent (merged into `verify-app`)
- `test-runner` agent (merged into `verify-app`)
- `security-scanner` agent (merged into `verify-app`)
- `quality-checker` agent (merged into `verify-app`)

## [1.0.0] - 2025-01-15

### Added

- Initial release of AI Engineering Framework.
- 21 slash commands for Claude Code.
- 6 background agents.
- 10 coding standards files.
- 4 learnings files.
- Workshop with 9 modules.
- CI/CD templates for GitHub Actions and Azure Pipelines.
- GitHub Copilot instructions.
- Install script.
