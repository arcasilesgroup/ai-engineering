---
total: 6
completed: 6
---

# Plan: sub-005 Reference Updates, Mirrors + Tests

## Plan

exports: ["all references updated", "all mirrors synced", "all tests passing"]
imports: ["LESSONS.md new path (sub-001)", "instincts v2 schema (sub-002)", "ai-instinct rewritten SKILL.md (sub-003)", "proposals.md (sub-004)"]

- [x] T-5.1: Update CLAUDE.md, GEMINI.md, AGENTS.md references
  - **Files**: `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
  - **Done**: All `contexts/team/lessons.md` -> `LESSONS.md`. Source of Truth table updated in all 3 files. Self-Improvement Loop, Proactive Memory, Task Management sections all updated.

- [x] T-5.2: Update template files
  - **Files**: `src/ai_engineering/templates/project/CLAUDE.md`, `src/ai_engineering/templates/project/GEMINI.md`, `src/ai_engineering/templates/project/AGENTS.md`, template ai-onboard and ai-learn SKILL.md copies
  - **Done**: Templates match active project files. Template LESSONS.md at correct path. All 4 IDE template ai-onboard copies synced via sync_command_mirrors.py. Template manifest.yml ownership cleaned (removed learnings/** reference).

- [x] T-5.3: Sync 4 IDE skill mirrors
  - **Files**: `.codex/skills/`, `.gemini/skills/`, `.github/skills/`, `src/ai_engineering/templates/project/.*/skills/`
  - **Done**: `python scripts/sync_command_mirrors.py` synced 42 files (updated ai-onboard, ai-learn, ai-instinct, ai-commit, ai-pr across all mirrors). 7 orphan consolidate.py scripts removed. `--check` returns 0, all 895 mirror files in sync.

- [x] T-5.4: Update README.md directory documentation
  - **Files**: `.ai-engineering/README.md`, `README.md`, `src/ai_engineering/templates/.ai-engineering/README.md`
  - **Done**: Directory tree shows LESSONS.md at root. No learnings/ directory. learnings/ removed from directory guide table. Reviews/notes/instincts section updated. Template README.md mirrors active project README.md.

- [x] T-5.5: Update installer governance.py for migration
  - **Files**: `src/ai_engineering/installer/phases/governance.py`
  - **Done**: Migration logic already in place from sub-001: _MIGRATIONS dict maps LESSONS.md -> contexts/team/lessons.md. State phase cleaned: removed _INSTINCT_CONTEXT (context.md eliminated in v2). Service _STATE_FILES cleaned. Ownership defaults cleaned.

- [x] T-5.6: Update tests
  - **Files**: `tests/unit/test_framework_context_loads.py`, `tests/unit/test_cli_ui.py`, `tests/unit/test_state.py`, `tests/unit/test_installer.py`, `tests/unit/installer/test_phases.py`, `tests/e2e/test_install_clean.py`, `tests/integration/test_updater.py`, `tests/integration/test_framework_hook_emitters.py`
  - **Done**: All path references updated. Team seed count adjusted (2->1). State files count adjusted (8->7). instincts/context.md assertions removed. Instinct extraction assertions updated to match v2 behavior (Bash -> Grep recovery). `pytest tests/` passes with 2656 passed, 0 failures.

### Confidence
- **Level**: high
- **Assumptions**: sync_command_mirrors.py handles all mirror targets correctly. No hidden references outside the grep results.
- **Unknowns**: None remaining.

## Self-Report

**Phase**: sub-005 Reference Updates, Mirrors + Tests
**Status**: COMPLETE
**Duration**: Single pass, no retries needed

### Changes Made

**Instruction files** (6 files): CLAUDE.md, GEMINI.md, AGENTS.md (root + template copies)
- Replaced 5 occurrences per file of `contexts/team/lessons.md` -> `LESSONS.md`
- Sections updated: Self-Improvement Loop (section 3), Proactive Memory (section 9), Task Management (step 6), Source of Truth table

**Template files** (4 files): template README.md, template manifest.yml
- Removed `learnings/` from directory tree, directory guide table, and reviews/notes/instincts section
- Added `LESSONS.md` to directory tree as seeded file
- Removed `learnings/**` from template manifest.yml ownership.system

**IDE mirrors** (42 files synced): ai-onboard, ai-learn, ai-instinct, ai-commit, ai-pr across .codex/, .gemini/, .github/, and all template copies. 7 orphan consolidate.py scripts removed.

**Installer/state** (4 source files):
- `state.py`: Removed _INSTINCT_CONTEXT constant and plan/execute/verify references
- `service.py`: Removed instinct-context from _STATE_FILES dict and _generate_state_files
- `defaults.py`: Removed instincts/context.md ownership entry
- `governance.py`: Already had migration logic (verified, no changes needed)

**Tests** (8 test files): Updated path references, count assertions, and instinct v2 behavior assertions.

### Validation
- `ruff check` + `ruff format --check`: All 12 changed Python files pass
- `sync_command_mirrors.py --check`: 895 mirror files in sync, 0 drift
- `pytest tests/`: 2656 passed, 0 failed, 1 warning (unrelated RuntimeWarning)
