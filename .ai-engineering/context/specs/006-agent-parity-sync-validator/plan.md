---
spec: "006"
approach: "serial-phases"
---

# Plan — Agent Parity & Sync Validator

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/validator/__init__.py` | Package init |
| `src/ai_engineering/validator/service.py` | Core validation logic — 6 categories |
| `src/ai_engineering/cli_commands/validate.py` | CLI handler for `ai-eng validate` |
| `src/ai_engineering/templates/project/instructions/python.instructions.md` | Path-scoped Copilot template |
| `src/ai_engineering/templates/project/instructions/testing.instructions.md` | Path-scoped Copilot template |
| `src/ai_engineering/templates/project/instructions/markdown.instructions.md` | Path-scoped Copilot template |
| `codex.md` (repo root) | Full Codex instruction file |
| `tests/unit/test_validator.py` | Validator unit tests |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/cli_factory.py` | Register `validate` command |
| `src/ai_engineering/installer/templates.py` | Extend `_PROJECT_TEMPLATE_MAP`, add tree-copy for `.claude/commands/**` |
| `src/ai_engineering/state/defaults.py` | Add `.claude/commands/**` to ownership map |
| `src/ai_engineering/templates/project/codex.md` | Expand from 22-line stub to full parity |
| `src/ai_engineering/templates/project/AGENTS.md` | Add 3 missing skills |
| `src/ai_engineering/templates/project/CLAUDE.md` | Add 3 missing skills |
| `src/ai_engineering/templates/project/copilot-instructions.md` | Add 3 missing skills, remove Claude-specific text |
| `.github/copilot-instructions.md` | Add 3 missing skills, remove Claude-specific text |
| `AGENTS.md` | Add 3 missing skills |
| `CLAUDE.md` | Add 3 missing skills |
| `.github/workflows/ci.yml` | Add `content-integrity` job |
| `.ai-engineering/manifest.yml` | Add `AGENTS.md` to `external_framework_managed` |
| `.ai-engineering/context/product/product-contract.md` | Update counters 29→32, fix Active Spec section |
| `src/ai_engineering/updater/service.py` | Handle new template map entries |

### Mirror Copies

| Canonical | Mirror |
|-----------|--------|
| `.claude/commands/utils/git-helpers.md` | `src/ai_engineering/templates/project/.claude/commands/utils/git-helpers.md` |
| `.claude/commands/utils/platform-detection.md` | `src/ai_engineering/templates/project/.claude/commands/utils/platform-detection.md` |
| `.claude/commands/validation/install-readiness.md` | `src/ai_engineering/templates/project/.claude/commands/validation/install-readiness.md` |

## File Structure

```text
src/ai_engineering/
├── validator/
│   ├── __init__.py
│   └── service.py          # IntegrityReport, 6 _check_* functions
├── cli_commands/
│   └── validate.py          # CLI handler
├── installer/
│   └── templates.py         # Extended map + tree copy
├── state/
│   └── defaults.py          # Fixed ownership map
└── templates/project/
    ├── instructions/         # NEW: 3 path-scoped Copilot templates
    └── codex.md              # EXPANDED: full parity
```

## Session Map

### Phase 0: Scaffold [S]

- Create spec directory and documents.
- Update `_active.md`.

### Phase 1: Cross-Cutting Fixes [M]

- Fix `_PROJECT_TEMPLATE_MAP` — add `AGENTS.md`, `.github/instructions/**`.
- Fix `defaults.py` — add `.claude/commands/**`.
- Fix `manifest.yml` — add `AGENTS.md` to `external_framework_managed`.
- Fix `product-contract.md` — update counters, Active Spec section.

### Phase 2: Validator Core [L]

- Create `validator/` package with data model.
- Implement 6 category validators.
- Create main `validate_content_integrity()` entry point.

### Phase 3: Validator CLI + CI [M]

- Create `cli_commands/validate.py`.
- Register in `cli_factory.py`.
- Add CI job to `ci.yml`.

### Phase 4: Copilot Parity [M]

- Create `.github/instructions/**` templates.
- Remove Claude-specific text from `copilot-instructions.md`.
- Register 3 missing skills in Copilot instruction files.

### Phase 5: Claude Parity [M]

- Extend `copy_project_templates()` in `templates.py` for `.claude/commands/**` tree-copy.
- Create 3 new Claude command wrappers + mirrors.
- Register 3 missing skills in Claude instruction files.

### Phase 6: Codex Parity [M]

- Expand `codex.md` template to full parity.
- Create `codex.md` at repo root.
- Add `AGENTS.md` to template map.
- Register 3 missing skills in Codex instruction files.

### Phase 7: Instruction Consistency [S]

- Verify all 6 instruction files list identical 32 skills and 8 agents.
- Add `### Utility Skills` and `### Validation Skills` subsections.

### Phase 8: Tests [L]

- Unit tests for all 6 validator categories.
- Tests with intentionally broken states.
- Target ≥ 90% coverage for `validator/`.

### Phase 9: Validator Self-Check + Close [S]

- Run `ai-eng validate` — must exit 0.
- Run full test suite.
- Run quality gates.
- Create `done.md`.
- Create PR.

## Patterns

- Follow `DoctorReport`/`CheckResult` dataclass pattern from `doctor/service.py`.
- Each validator category is a private `_check_*` function appending to a report.
- CLI command follows existing `typer` handler patterns from `cli_commands/core.py`.
- Template map uses string keys (template-relative) → string values (project-relative).
- Mirror sync uses SHA-256 byte comparison.
- All instruction file edits must be applied to all 6 files simultaneously.
