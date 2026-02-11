---
spec: "006"
total: 42
completed: 42
last_session: "2025-07-15"
next_session: "Done"
---

# Tasks — Agent Parity & Sync Validator

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/agent-parity-sync-validator` from main
- [x] 0.2 Create spec directory `context/specs/006-agent-parity-sync-validator/`
- [x] 0.3 Create `spec.md`, `plan.md`, `tasks.md`
- [x] 0.4 Update `_active.md` to point to 006
- [x] 0.5 Commit: `spec-006: Phase 0 — scaffold spec files and activate`

## Phase 1: Cross-Cutting Fixes [M]

- [x] 1.1 Add `"AGENTS.md": "AGENTS.md"` to `_PROJECT_TEMPLATE_MAP` in `installer/templates.py`
- [x] 1.2 Add `.github/instructions/**` entries to `_PROJECT_TEMPLATE_MAP`
- [x] 1.3 Add `.claude/commands/**` to `defaults.py` ownership map as `FRAMEWORK_MANAGED`
- [x] 1.4 Add `AGENTS.md` to `manifest.yml` `external_framework_managed`
- [x] 1.5 Add `.github/instructions/**` to `manifest.yml` managed files
- [x] 1.6 Update `product-contract.md` — skill count 29→32, fix Active Spec section
- [x] 1.7 Commit: `spec-006: Phase 1 — fix structural inconsistencies`

## Phase 2: Validator Core [L]

- [x] 2.1 Create `src/ai_engineering/validator/__init__.py`
- [x] 2.2 Define data model in `validator/service.py`: `IntegrityCategory` enum, `IntegrityCheckResult`, `IntegrityReport`
- [x] 2.3 Implement `_check_file_existence()` — scan internal path references, verify targets exist
- [x] 2.4 Implement `_check_mirror_sync()` — SHA-256 compare canonical vs template mirrors
- [x] 2.5 Implement `_check_counter_accuracy()` — count skills/agents in instruction files vs product-contract
- [x] 2.6 Implement `_check_cross_references()` — parse References sections, verify bidirectional links
- [x] 2.7 Implement `_check_instruction_consistency()` — parse all 6 instruction files, verify identical sets
- [x] 2.8 Implement `_check_manifest_coherence()` — verify ownership globs match filesystem
- [x] 2.9 Implement `validate_content_integrity()` main entry point with category filtering
- [x] 2.10 Commit: `spec-006: Phase 2 — implement validator core with 6 categories`

## Phase 3: Validator CLI + CI [M]

- [x] 3.1 Create `src/ai_engineering/cli_commands/validate.py` — `validate_cmd()` with `--category` and `--json` options
- [x] 3.2 Register `validate` command in `cli_factory.py`
- [x] 3.3 Add `content-integrity` job to `.github/workflows/ci.yml` — parallel, gates build
- [x] 3.4 Verify `ai-eng validate --help` works
- [x] 3.5 Commit: `spec-006: Phase 3 — add validate CLI command and CI job`

## Phase 4: Copilot Parity [M]

- [x] 4.1 Create `src/ai_engineering/templates/project/instructions/python.instructions.md`
- [x] 4.2 Create `src/ai_engineering/templates/project/instructions/testing.instructions.md`
- [x] 4.3 Create `src/ai_engineering/templates/project/instructions/markdown.instructions.md`
- [x] 4.4 Remove Claude-specific text from `.github/copilot-instructions.md` and template counterpart
- [x] 4.5 Add `### Utility Skills` and `### Validation Skills` to `.github/copilot-instructions.md` and template
- [x] 4.6 Commit: `spec-006: Phase 4 — Copilot parity`

## Phase 5: Claude Parity [M]

- [x] 5.1 Extend `copy_project_templates()` in `templates.py` for `.claude/commands/**` tree-copy
- [x] 5.2 Create `.claude/commands/utils/git-helpers.md` + template mirror
- [x] 5.3 Create `.claude/commands/utils/platform-detection.md` + template mirror
- [x] 5.4 Create `.claude/commands/validation/install-readiness.md` + template mirror
- [x] 5.5 Add `### Utility Skills` and `### Validation Skills` to `CLAUDE.md` and template
- [x] 5.6 Commit: `spec-006: Phase 5 — Claude parity`

## Phase 6: Codex Parity [M]

- [x] 6.1 Expand `src/ai_engineering/templates/project/codex.md` to full parity (skills, agents, contracts)
- [x] 6.2 Create `codex.md` at repo root with full content
- [x] 6.3 Add `### Utility Skills` and `### Validation Skills` to `AGENTS.md` and template
- [x] 6.4 Commit: `spec-006: Phase 6 — Codex parity`

## Phase 7: Instruction Consistency [S]

- [x] 7.1 Verify all 6 instruction files list identical 32 skills and 8 agents
- [x] 7.2 Fix any remaining discrepancies found during verification
- [x] 7.3 Commit: `spec-006: Phase 7 — instruction consistency`

## Phase 8: Tests [L]

- [x] 8.1 Create `tests/unit/test_validator.py` — test data model and report properties
- [x] 8.2 Test `_check_file_existence` with valid and broken references
- [x] 8.3 Test `_check_mirror_sync` with in-sync and desynced files
- [x] 8.4 Test `_check_counter_accuracy` with correct and incorrect counts
- [x] 8.5 Test `_check_cross_references` with valid and broken bidirectional links
- [x] 8.6 Test `_check_instruction_consistency` with matching and mismatched files
- [x] 8.7 Test `_check_manifest_coherence` with valid and invalid manifests
- [x] 8.8 Verify ≥ 90% coverage for `validator/` package
- [x] 8.9 Commit: `spec-006: Phase 8 — validator unit tests`

## Phase 9: Validator Self-Check + Close [S]

- [x] 9.1 Run `ai-eng validate` — must exit 0
- [x] 9.2 Run `uv run pytest` — all tests pass
- [x] 9.3 Run `ruff check && ruff format --check` — clean
- [x] 9.4 Run `ty check` — no errors
- [x] 9.5 Create `done.md`
- [x] 9.6 Create PR: `spec-006: Agent Parity & Sync Validator`
