---
id: "006"
slug: "agent-parity-sync-validator"
status: "in-progress"
created: "2026-02-11"
---

# Spec 006 — Agent Parity & Sync Validator

## Problem

The project does not have 100% native support for any of the 3 target AI agent platforms:

- **GitHub Copilot (~85%)**: `.github/instructions/**` has no template counterpart for target projects. `copilot-instructions.md` contains Claude-specific text. 3 skills are unregistered.
- **Claude Code (~80%)**: `.claude/commands/**` (37 template files) exist but are not wired into `_PROJECT_TEMPLATE_MAP` — they are never installed or updated. 3 skills missing from listings.
- **Codex (~40%)**: `codex.md` is a 22-line stub with no skills/agents/contract. `AGENTS.md` is not in `_PROJECT_TEMPLATE_MAP`. No repo-root `codex.md` exists.

Additionally, no programmatic enforcement of content synchronization exists. The content-integrity skill is a procedural markdown document that agents read and execute manually. There is no CLI command, no CI job, and no git hook that validates the 6 integrity categories. Changes to `.ai-engineering/` can silently desync from templates, instruction files, mirrors, and manifests.

Specific structural inconsistencies:

- `_PROJECT_TEMPLATE_MAP` has 7 entries but 10+ template files exist on disk.
- `defaults.py` ownership map tracks `.github/instructions/**` but no templates exist for it.
- `manifest.yml` lists `.claude/commands/**` as `external_framework_managed` but the installer never deploys them.
- `AGENTS.md` is tracked in ownership but absent from both `_PROJECT_TEMPLATE_MAP` and `manifest.yml`.
- 3 skills (`utils/git-helpers`, `utils/platform-detection`, `validation/install-readiness`) exist on disk but are unregistered in all 6 instruction files.
- `product-contract.md` reports 29 skills; actual count is 32.

## Solution

1. **Programmatic content-integrity validator** — a new `ai-eng validate` CLI command implementing all 6 categories from the content-integrity skill, with CI integration.
2. **Platform parity** — bring all 3 platforms to 100% coverage by fixing templates, template maps, instruction files, and ownership declarations.
3. **Cross-cutting fixes** — reconcile `_PROJECT_TEMPLATE_MAP`, `defaults.py` ownership map, and `manifest.yml` to eliminate structural inconsistencies.

## Scope

### In Scope

- New `src/ai_engineering/validator/` package with programmatic 6-category validation.
- New `ai-eng validate` CLI command with category filtering and JSON output.
- New `content-integrity` CI job in `.github/workflows/ci.yml`.
- Expand `codex.md` template to full parity with `CLAUDE.md`/`AGENTS.md`.
- Install `codex.md` at repo root.
- Add `AGENTS.md` and `.claude/commands/**` to `_PROJECT_TEMPLATE_MAP`.
- Create `.github/instructions/**` templates.
- Register 3 missing skills in all 6 instruction files.
- Fix `manifest.yml` and `defaults.py` inconsistencies.
- Update `product-contract.md` counters (29 → 32 skills).
- Unit tests for validator (≥ 90% coverage).

### Out of Scope

- `.vscode/settings.json` Copilot IDE configuration (low priority, optional).
- Codex task-specific instruction files (no native support confirmed).
- Rewriting existing skills or agents content.
- Changes to the procedural content-integrity skill (it remains as-is).
- Updater service refactoring for directory-tree copy (tracked but deferred to implementation decision).

## Acceptance Criteria

1. `ai-eng validate` runs all 6 integrity categories and exits 0 on this repo.
2. `ai-eng validate --category <name>` supports filtering by individual category.
3. `ai-eng validate --json` produces machine-readable output.
4. CI job `content-integrity` runs in parallel with existing jobs and gates the build.
5. `_PROJECT_TEMPLATE_MAP` includes `AGENTS.md`, `.github/instructions/**`, and a mechanism for `.claude/commands/**`.
6. `codex.md` exists at repo root with full skills/agents/contract listing.
7. All 6 instruction files list identical skills (32) and agents (8).
8. `product-contract.md` shows 32 skills, 8 agents.
9. `defaults.py` ownership map, `manifest.yml`, and `_PROJECT_TEMPLATE_MAP` are fully reconciled.
10. `ai-eng validate` exits 0 after all changes — self-validating.
11. Unit test coverage for `validator/` ≥ 90%.
12. All existing tests continue to pass.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Validator is a top-level CLI command (`ai-eng validate`), not a sub-group | High visibility, single purpose, matches `ai-eng doctor` pattern |
| D2 | CI job runs in parallel with lint/typecheck/test/security | No dependency on other jobs; pure filesystem validation |
| D3 | Procedural content-integrity skill is kept alongside programmatic implementation | Agents benefit from readable procedure; CLI provides enforcement |
| D4 | `codex.md` gets full parity content, not minimal | Consistent experience across all platforms |
| D5 | `.github/instructions/**` gets templates | Enables framework-managed path-scoped Copilot instructions in target projects |
| D6 | `.claude/commands/**` installed via directory-tree copy mechanism | File-level mapping impractical for 37+ files; extend `copy_project_templates` |
