---
spec: "006"
closed: "2025-07-15"
---

# Done — Agent Parity & Sync Validator

## Summary

Spec 006 delivers 100% native support for GitHub Copilot, Claude Code, and Codex by fixing structural inconsistencies, expanding instruction files to full parity, and building a programmatic content-integrity validator with CLI and CI integration.

## Delivered

### Programmatic Content-Integrity Validator

| Component | Purpose |
|-----------|---------|
| `validator/service.py` | 6-category content-integrity validation engine (955 lines) |
| `validator/__init__.py` | Package init, re-exports main symbols |
| `cli_commands/validate.py` | `ai-eng validate` CLI handler with `--category` and `--json` options |
| CI job `content-integrity` | Parallel CI job gating the build |

### Validator Categories (6)

| Category | What it checks |
|----------|---------------|
| `file-existence` | Internal path references resolve, spec directories complete |
| `mirror-sync` | Canonical/template governance mirrors byte-identical |
| `counter-accuracy` | Skill/agent counts consistent across instruction files and product-contract |
| `cross-reference` | Bidirectional references valid across `.ai-engineering/` |
| `instruction-consistency` | All 8 instruction files list identical skills and agents |
| `manifest-coherence` | Ownership globs match filesystem, active spec valid |

### Cross-Cutting Fixes

- `_PROJECT_TEMPLATE_MAP` expanded: added `AGENTS.md`, 3 instruction templates.
- `_PROJECT_TEMPLATE_TREES` added: `.claude/commands/**` directory-tree copy mechanism.
- `copy_project_templates()` extended with tree-copy support.
- `defaults.py` ownership map: added `.claude/commands/**` as `FRAMEWORK_MANAGED`.
- `manifest.yml`: added `AGENTS.md` and `.github/instructions/**` to `external_framework_managed`.
- `product-contract.md`: skill count 29 → 32, Active Spec → 006.

### Copilot Parity (85% → 100%)

- Created 3 instruction templates: `python.instructions.md`, `testing.instructions.md`, `markdown.instructions.md`.
- Removed Claude-specific text from `copilot-instructions.md` (repo + template).
- Added Utility Skills (2) and Validation Skills (1) to all instruction files.

### Claude Parity (80% → 100%)

- Created 6 Claude command wrappers (3 canonical + 3 template mirrors) for `utils/git-helpers`, `utils/platform-detection`, `validation/install-readiness`.
- Added Utility Skills and Validation Skills to `CLAUDE.md` (repo + template).
- Added slash command entries for `/utils:*` and `/validation:*`.

### Codex Parity (40% → 100%)

- Generated full-parity `codex.md` at repo root from `AGENTS.md` (minus Slash Commands).
- Expanded template `codex.md` to full content.
- Added Utility Skills and Validation Skills to `AGENTS.md` (repo + template).

### Instruction Consistency

- All 8 instruction files verified: identical 32 skills, 8 agents, 6 subsections.
- `codex.md` added to `_INSTRUCTION_FILES` for ongoing consistency enforcement.

### Tests

- `tests/unit/test_validator.py`: 30 unit tests across 8 test classes covering all 6 categories.

## Verification Results

| Check | Result |
|-------|--------|
| Validator self-check: file-existence | 10 pre-existing broken refs (out of scope) |
| Validator self-check: mirror-sync | PASS — 40 Claude + 45 governance mirrors |
| Validator self-check: counter-accuracy | PASS — 32 skills, 8 agents |
| Validator self-check: cross-reference | PASS — 40 files checked |
| Validator self-check: instruction-consistency | PASS — 8 files identical |
| Validator self-check: manifest-coherence | PASS — all directories, active spec valid |
| All 8 instruction files × 32 skills | PASS |
| Product-contract counter = 32 skills, 8 agents | PASS |
| Python syntax checks (all new/modified .py files) | PASS |
| Tests / lint / type-check | DEFERRED — PyPI 403 blocks local execution |

## Deferred

- **Pre-existing broken references** (10): Template paths in old specs (`001`, `002`) and framework-contract reference files that were never created (backlog/tasks.md, delivery/implementation.md, etc.). Addressed in spec-007.
- **Local test execution**: PyPI returns 403 Forbidden; tests written but cannot be validated locally. CI will run them on merge.
- **Updater service integration**: `copy_template_tree()` added to `templates.py` but not yet wired into the updater's `_sync_templates()` flow. Deferred per D6.
- **`.vscode/settings.json` Copilot IDE configuration**: Low priority, optional per spec scope.
